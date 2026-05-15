"""
Aqar.ai - Agents & Channels Routes
====================================
Endpoints for agent registration, channel management, and YouTube discovery.

Workflow:
  1. Agent registers (or admin creates agent)
  2. Agent adds their YouTube channel
  3. Admin reviews and approves/rejects channel
  4. Approved channels are included in the discovery task
  5. Admin can also discover channels by searching YouTube
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from models.base import Agent, ChannelRegistration, ChannelStatus

logger = structlog.get_logger()
router = APIRouter()


# ═══════════════════════════════════════
# Schemas
# ═══════════════════════════════════════


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    city: str = "Tangier"
    country: str = "Morocco"
    notes: str | None = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    company: str | None
    city: str
    country: str
    is_verified: bool
    notes: str | None = None
    channels_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}  # Enables model_validate


class ChannelRegisterRequest(BaseModel):
    channel_url: str = Field(..., description="YouTube channel URL")
    channel_name: str | None = None
    description: str | None = None
    region: str = "tangier-tetouan"
    agent_id: uuid.UUID | None = None


class ChannelResponse(BaseModel):
    id: uuid.UUID
    channel_url: str
    channel_name: str | None
    channel_id: str | None
    description: str | None
    region: str
    status: str
    max_videos: int
    discovered_via: str | None
    rejection_reason: str | None
    agent_name: str | None = None
    created_at: datetime
    approved_at: datetime | None

    model_config = {"from_attributes": True}


class ChannelApprovalRequest(BaseModel):
    status: str = Field(..., description="approved or rejected")
    rejection_reason: str | None = None
    max_videos: int | None = None


class YouTubeSearchRequest(BaseModel):
    keywords: str = Field(..., description="Search keywords (e.g. 'real estate tangier')")
    max_results: int = Field(10, ge=1, le=50)


class YouTubeSearchResult(BaseModel):
    channel_id: str
    channel_name: str
    channel_url: str
    subscriber_count: str | None = None
    video_count: str | None = None
    description: str = ""
    already_registered: bool = False


# ═══════════════════════════════════════
# Agent Endpoints
# ═══════════════════════════════════════


@router.post("/agents", response_model=AgentResponse)
async def register_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: AgentCreateRequest,
):
    """Register a new real estate agent."""
    # Check duplicate email
    if request.email:
        existing = await db.execute(select(Agent).where(Agent.email == request.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Agent with this email already exists")

    agent = Agent(**request.model_dump())
    db.add(agent)
    await db.flush()

    logger.info("Agent registered", agent_id=str(agent.id), name=agent.name)
    # Use model_validate to avoid manual field mapping
    return AgentResponse.model_validate(agent)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Fetch details for a single agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Calculate channel count for response
    ch_count = await db.execute(
        select(func.count(ChannelRegistration.id)).where(ChannelRegistration.agent_id == agent.id)
    )

    # Convert to response with count
    resp = AgentResponse.model_validate(agent)
    resp.channels_count = ch_count.scalar_one()
    return resp


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    request: AgentCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing agent's details."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update only the fields provided in the request
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)
    return await get_agent(agent_id, db)


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents(
    db: Annotated[AsyncSession, Depends(get_db)],
    city: str | None = None,
    verified: bool | None = None,
):
    """List all registered agents."""
    query = select(Agent).order_by(Agent.created_at.desc())
    if city:
        query = query.where(Agent.city.ilike(f"%{city}%"))
    if verified is not None:
        query = query.where(Agent.is_verified == verified)

    result = await db.execute(query)
    agents_list = result.scalars().all()  # <── Get model instances (not Rows)

    items = []
    for agent in agents_list:
        # Fetch channel count
        ch_count_res = await db.execute(
            select(func.count(ChannelRegistration.id)).where(
                ChannelRegistration.agent_id == agent.id
            )
        )
        ch_count = ch_count_res.scalar_one()

        # FIXED: Use model_validate to ensure 'country' and others are mapped
        response_obj = AgentResponse.model_validate(agent)
        response_obj.channels_count = ch_count
        items.append(response_obj)

    return items


@router.post("/agents/{agent_id}/verify")
async def verify_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: uuid.UUID,
):
    """Admin: verify an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_verified = True
    await db.flush()
    return {"status": "verified", "agent_id": str(agent_id)}


@router.get("/config/geo-defaults")
async def get_geo_config():
    """Returns dynamic lists of supported countries and cities."""
    return {
        "countries": ["Morocco", "Spain", "France", "UAE"],
        "cities_by_country": {
            "Morocco": ["Tangier", "Tetouan", "Casablanca", "Marrakesh"],
            "Spain": ["Madrid", "Barcelona", "Malaga"],
        },
    }


# ═══════════════════════════════════════
# Channel Registration Endpoints
# ═══════════════════════════════════════


@router.post("/channels", response_model=ChannelResponse)
async def register_channel(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: ChannelRegisterRequest,
):
    """
    Register a YouTube channel for monitoring.
    Status starts as 'pending' and requires admin approval.
    """
    # Check duplicate
    existing = await db.execute(
        select(ChannelRegistration).where(ChannelRegistration.channel_url == request.channel_url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This channel is already registered")

    # Try to fetch channel metadata
    channel_name = request.channel_name
    channel_id = None
    try:
        from aqar_pipeline.utils.youtube import fetch_channel_videos

        # Fetch just 1 video to get channel metadata
        videos = fetch_channel_videos(request.channel_url, max_videos=1)
        if videos:
            channel_name = channel_name or videos[0].channel_name
            channel_id = videos[0].channel_id
    except Exception as e:
        logger.warning(f"Could not fetch channel metadata: {e}")

    channel = ChannelRegistration(
        agent_id=request.agent_id,
        channel_url=request.channel_url,
        channel_name=channel_name,
        channel_id=channel_id,
        description=request.description,
        region=request.region,
        status=ChannelStatus.PENDING,
        discovered_via="agent_registration" if request.agent_id else "manual",
    )
    db.add(channel)
    await db.flush()

    logger.info(
        "Channel registered",
        channel_id=str(channel.id),
        url=request.channel_url,
    )

    return _channel_to_response(channel, None)


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    region: str | None = None,
):
    """List all registered channels with optional status/region filter."""
    query = select(ChannelRegistration).order_by(ChannelRegistration.created_at.desc())
    if status:
        query = query.where(ChannelRegistration.status == status)
    if region:
        query = query.where(ChannelRegistration.region == region)

    result = await db.execute(query)
    channels = result.scalars().all()

    items = []
    for ch in channels:
        agent_name = None
        if ch.agent_id:
            agent_result = await db.execute(select(Agent.name).where(Agent.id == ch.agent_id))
            agent_name = agent_result.scalar_one_or_none()
        items.append(_channel_to_response(ch, agent_name))

    return items


@router.post("/channels/{channel_id}/approve", response_model=ChannelResponse)
async def approve_channel(
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_id: uuid.UUID,
    request: ChannelApprovalRequest,
):
    """
    Admin: approve or reject a channel registration.

    Approved channels will be included in the next discovery scan.
    """
    result = await db.execute(
        select(ChannelRegistration).where(ChannelRegistration.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if request.status == "approved":
        channel.status = ChannelStatus.APPROVED
        channel.approved_at = datetime.now(UTC)
        if request.max_videos:
            channel.max_videos = request.max_videos
    elif request.status == "rejected":
        channel.status = ChannelStatus.REJECTED
        channel.rejection_reason = request.rejection_reason
    else:
        raise HTTPException(
            status_code=400,
            detail="Status must be 'approved' or 'rejected'",
        )

    await db.flush()

    logger.info(
        f"Channel {request.status}",
        channel_id=str(channel_id),
        channel_name=channel.channel_name,
    )

    return _channel_to_response(channel, None)


@router.post("/channels/{channel_id}/disable")
async def disable_channel(
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_id: uuid.UUID,
):
    """Admin: disable an approved channel (stops future discovery scans)."""
    result = await db.execute(
        select(ChannelRegistration).where(ChannelRegistration.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.status = ChannelStatus.DISABLED
    await db.flush()
    return {"status": "disabled", "channel_id": str(channel_id)}


# ═══════════════════════════════════════
# YouTube Discovery (Admin)
# ═══════════════════════════════════════


@router.post("/channels/discover", response_model=list[YouTubeSearchResult])
async def discover_youtube_channels(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: YouTubeSearchRequest,
):
    """
    Admin: search YouTube for channels matching keywords.

    Uses yt-dlp to search YouTube and returns channel candidates
    that can then be registered for monitoring.
    """
    import yt_dlp

    search_query = f"ytsearch{request.max_results}:{request.keywords}"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "no_color": True,
    }

    results = []
    seen_channels = set()

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get("entries", []) if info else []

            for entry in entries:
                if not entry:
                    continue

                ch_id = entry.get("channel_id", "")
                ch_name = entry.get("channel", entry.get("uploader", ""))
                ch_url = entry.get("channel_url", "")

                if not ch_id or ch_id in seen_channels:
                    continue
                seen_channels.add(ch_id)

                if not ch_url and ch_id:
                    ch_url = f"https://www.youtube.com/channel/{ch_id}"

                # Check if already registered
                existing = await db.execute(
                    select(ChannelRegistration).where(ChannelRegistration.channel_id == ch_id)
                )
                already_registered = existing.scalar_one_or_none() is not None

                results.append(
                    YouTubeSearchResult(
                        channel_id=ch_id,
                        channel_name=ch_name,
                        channel_url=ch_url,
                        description=entry.get("description", "")[:200]
                        if entry.get("description")
                        else "",
                        already_registered=already_registered,
                    )
                )

    except Exception as e:
        logger.error(f"YouTube channel search error: {e}")
        # Add 'from e' to fix Ruff B904
        raise HTTPException(status_code=500, detail=f"YouTube search failed: {str(e)}") from e

    logger.info(f"YouTube discovery: found {len(results)} channels for '{request.keywords}'")
    return results


def _channel_to_response(channel: ChannelRegistration, agent_name: str | None) -> ChannelResponse:
    return ChannelResponse(
        id=channel.id,
        channel_url=channel.channel_url,
        channel_name=channel.channel_name,
        channel_id=channel.channel_id,
        description=channel.description,
        region=channel.region,
        status=channel.status.value,
        max_videos=channel.max_videos,
        discovered_via=channel.discovered_via,
        rejection_reason=channel.rejection_reason,
        agent_name=agent_name,
        created_at=channel.created_at,
        approved_at=channel.approved_at,
    )
