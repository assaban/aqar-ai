# apps/api/app/services/agent_service.py
"""
Aqar.ai - Agent Service Layer
=============================
Handles all operational business rules for Agents and Channel management.
"""

import re
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Agent, ChannelRegistration, ChannelStatus, Property, VideoSource

logger = structlog.get_logger()

# Match expressions for automatic agency parsing
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
MOROCCO_PHONE_REGEX = re.compile(r"(?:\+212|0)[67]\d{8}")


class AgentService:
    @staticmethod
    async def list_all_agents(
        db: AsyncSession,
        city: str | None = None,
        country: str | None = None,
        verified: bool | None = None,
    ) -> list[dict]:
        """Applies filters and computes real-time aggregation metrics for the Agent ledger."""
        query = select(Agent).order_by(Agent.created_at.desc())
        if city:
            query = query.where(Agent.city.ilike(f"%{city}%"))
        if country:
            query = query.where(Agent.country.ilike(f"%{country}%"))
        if verified is not None:
            query = query.where(Agent.is_verified == verified)

        result = await db.execute(query)
        agents = result.scalars().all()

        items = []
        for a in agents:
            ch_count = (
                await db.execute(
                    select(func.count(ChannelRegistration.id)).where(
                        ChannelRegistration.agent_id == a.id
                    )
                )
            ).scalar_one()

            prop_count = (
                await db.execute(
                    select(func.count(Property.id))
                    .join(VideoSource, Property.video_source_id == VideoSource.id)
                    .join(
                        ChannelRegistration,
                        VideoSource.channel_id == ChannelRegistration.channel_id,
                    )
                    .where(ChannelRegistration.agent_id == a.id)
                )
            ).scalar_one()

            items.append(
                {
                    "id": str(a.id),
                    "name": a.name,
                    "email": a.email,
                    "phone": a.phone,
                    "company": a.company,
                    "city": a.city,
                    "country": a.country or "Morocco",
                    "is_verified": a.is_verified,
                    "channels_count": ch_count,
                    "properties_count": prop_count,
                    "created_at": a.created_at.isoformat() if a.created_at else "",
                }
            )
        return items

    @staticmethod
    async def register_new_channel(db: AsyncSession, dto) -> ChannelRegistration:
        """Runs the validation matrix and registers a monitored channel with automatic agent profile generation."""
        existing = await db.execute(
            select(ChannelRegistration).where(ChannelRegistration.channel_url == dto.channel_url)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="This channel is already registered")

        channel_name = dto.channel_name
        channel_id = None
        description_text = dto.description or ""

        try:
            from aqar_pipeline.utils.youtube import fetch_channel_videos

            videos = fetch_channel_videos(dto.channel_url, max_videos=1)
            if videos:
                channel_name = channel_name or videos[0].channel_name
                channel_id = videos[0].channel_id
                if videos[0].description:
                    description_text += f" {videos[0].description}"
        except Exception as e:
            logger.warning("youtube_metadata_resolution_failed", error=str(e))

        assigned_agent_id = dto.agent_id

        if not assigned_agent_id:
            found_emails = EMAIL_REGEX.findall(description_text)
            found_phones = MOROCCO_PHONE_REGEX.findall(description_text)

            agent_email = (
                found_emails[0]
                if found_emails
                else f"contact+{channel_id or uuid.uuid4().hex[:6]}@aqar.ai"
            )
            agent_phone = found_phones[0] if found_phones else None

            agent_check = await db.execute(select(Agent).where(Agent.email == agent_email))
            existing_agent = agent_check.scalar_one_or_none()

            if existing_agent:
                assigned_agent_id = existing_agent.id
            else:
                new_agent = Agent(
                    name=channel_name or "New AI Partner",
                    email=agent_email,
                    phone=agent_phone,
                    company=channel_name,
                    city="Tangier",
                )
                db.add(new_agent)
                await db.flush()
                assigned_agent_id = new_agent.id

        channel = ChannelRegistration(
            agent_id=assigned_agent_id,
            channel_url=dto.channel_url,
            channel_name=channel_name,
            channel_id=channel_id,
            description=dto.description,
            region=dto.region,
            status=ChannelStatus.PENDING,
            discovered_via="agent_registration" if dto.agent_id else "manual",
        )
        db.add(channel)
        await db.flush()
        return channel

    @staticmethod
    async def modify_channel_status(
        db: AsyncSession,
        channel_id: uuid.UUID,
        status: str,
        reason: str | None = None,
        max_v: int | None = None,
    ) -> ChannelRegistration:
        """Handles administrative status adjustments for channel ingestion loops."""
        ch = (
            await db.execute(
                select(ChannelRegistration).where(ChannelRegistration.id == channel_id)
            )
        ).scalar_one_or_none()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")

        if status == "approved":
            ch.status = ChannelStatus.APPROVED
            ch.approved_at = datetime.now(UTC)
            if max_v:
                ch.max_videos = max_v
        elif status == "rejected":
            ch.status = ChannelStatus.REJECTED
            ch.rejection_reason = reason
        else:
            raise HTTPException(
                status_code=400, detail="Invalid target status modification requested"
            )

        await db.flush()
        return ch
