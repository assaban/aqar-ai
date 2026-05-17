"""
Aqar.ai - Agents & Channels Controller
========================================
Full CRUD for agents, channels, and their relationships.
Includes YouTube discovery with channel quality scoring.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from re import compile
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from models.base import (
    Agent,
    ChannelRegistration,
    Property,
    VideoSource,
)
from packages.db.models.base import ChannelStatus

logger = structlog.get_logger()
router = APIRouter()


# ═══════════════════════════════════════
# Request/Response Schemas
# ═══════════════════════════════════════


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    city: str = "Tangier"
    country: str = "Morocco"
    notes: str | None = None


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    city: str | None = None
    country: str | None = None
    notes: str | None = None
    is_verified: bool | None = None


class ChannelSummary(BaseModel):
    id: str
    channel_url: str
    channel_name: str | None
    status: str
    max_videos: int
    created_at: str

    model_config = {"from_attributes": True}


class PropertySummary(BaseModel):
    id: str
    title: str | None
    property_type: str
    price: float | None
    neighborhood: str | None
    is_published: bool
    created_at: str


class AgentDetailResponse(BaseModel):
    id: str
    name: str
    email: str | None
    phone: str | None
    company: str | None
    city: str
    country: str
    is_verified: bool
    notes: str | None
    created_at: str
    channels: list[ChannelSummary]
    properties: list[PropertySummary]
    total_properties: int
    total_published: int


class AgentListItem(BaseModel):
    id: str
    name: str
    email: str | None
    phone: str | None
    company: str | None
    city: str
    country: str
    is_verified: bool
    channels_count: int
    properties_count: int
    created_at: str


class ChannelRegisterRequest(BaseModel):
    channel_url: str
    channel_name: str | None = None
    description: str | None = None
    region: str = "tangier-tetouan"
    agent_id: str | None = None
    max_videos: int = 20


class ChannelResponse(BaseModel):
    id: str
    channel_url: str
    channel_name: str | None
    channel_id: str | None
    description: str | None
    region: str
    status: str
    max_videos: int
    discovered_via: str | None
    rejection_reason: str | None
    agent_id: str | None
    agent_name: str | None
    tags: dict | None
    created_at: str
    approved_at: str | None


class ChannelApprovalRequest(BaseModel):
    status: str = Field(..., description="approved or rejected")
    rejection_reason: str | None = None
    max_videos: int | None = None


class LinkChannelRequest(BaseModel):
    agent_id: str


class YouTubeSearchRequest(BaseModel):
    keywords: str
    max_results: int = Field(15, ge=1, le=50)


class DiscoveredChannel(BaseModel):
    channel_id: str
    channel_name: str
    channel_url: str
    description: str
    video_count: int | None
    recent_upload: str | None  # Most recent video title
    recent_upload_date: str | None
    already_registered: bool
    existing_channel_id: str | None  # If registered, the DB channel ID


# ═══════════════════════════════════════
# Agent Endpoints
# ═══════════════════════════════════════


@router.get("/agents", response_model=list[AgentListItem])
async def list_agents(
    db: Annotated[AsyncSession, Depends(get_db)],
    city: str | None = None,
    country: str | None = None,
    verified: bool | None = None,
):
    """List all agents with summary counts."""
    query = select(Agent).order_by(Agent.created_at.desc())
    if city:
        query = query.where(Agent.city.ilike(f"%{city}%"))
    if country:
        query = query.where(Agent.city.ilike(f"%{country}%"))
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

        # Count properties from this agent's channels
        prop_count = (
            await db.execute(
                select(func.count(Property.id))
                .join(VideoSource, Property.video_source_id == VideoSource.id)
                .join(ChannelRegistration, VideoSource.channel_id == ChannelRegistration.channel_id)
                .where(ChannelRegistration.agent_id == a.id)
            )
        ).scalar_one()

        items.append(
            AgentListItem(
                id=str(a.id),
                name=a.name,
                email=a.email,
                phone=a.phone,
                company=a.company,
                city=a.city,
                country=a.country or "Morocco",
                is_verified=a.is_verified,
                channels_count=ch_count,
                properties_count=prop_count,
                created_at=a.created_at.isoformat() if a.created_at else "",
            )
        )
    return items


@router.post("/agents", response_model=AgentDetailResponse)
async def create_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: AgentCreateRequest,
):
    """Create a new agent."""
    if request.email:
        existing = await db.execute(select(Agent).where(Agent.email == request.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Agent with this email already exists")

    agent = Agent(
        name=request.name,
        email=request.email,
        phone=request.phone,
        company=request.company,
        city=request.city,
        notes=request.notes,
    )
    db.add(agent)
    await db.flush()

    return await _build_agent_detail(db, agent)


@router.get("/agents/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: uuid.UUID,
):
    """Get full agent details with channels and properties."""
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await _build_agent_detail(db, agent)


@router.patch("/agents/{agent_id}", response_model=AgentDetailResponse)
async def update_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: uuid.UUID,
    request: AgentUpdateRequest,
):
    """Update agent details."""
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field, value in request.model_dump(exclude_none=True).items():
        setattr(agent, field, value)
    await db.flush()

    return await _build_agent_detail(db, agent)


@router.post("/agents/{agent_id}/verify")
async def verify_agent(db: Annotated[AsyncSession, Depends(get_db)], agent_id: uuid.UUID):
    """Toggle agent verification."""
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_verified = True
    await db.flush()
    return {"status": "verified", "agent_id": str(agent_id)}


# ═══════════════════════════════════════
# Channel Endpoints
# ═══════════════════════════════════════

# Add these regex compilation helpers at the top of agents.py
EMAIL_REGEX = compile(r"[\w\.-]+@[\w\.-]+\.\w+")
MOROCCO_PHONE_REGEX = compile(r"(?:\+212|0)[67]\d{8}")


@router.post("/channels", response_model=ChannelResponse)
async def register_channel(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: ChannelRegisterRequest,
):
    """Register a YouTube channel and automatically provision its Agent profile."""
    existing = await db.execute(
        select(ChannelRegistration).where(ChannelRegistration.channel_url == request.channel_url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This channel is already registered")

    channel_name = request.channel_name
    channel_id = None
    description_text = request.description or ""

    try:
        from aqar_pipeline.utils.youtube import fetch_channel_videos

        videos = fetch_channel_videos(request.channel_url, max_videos=1)
        if videos:
            channel_name = channel_name or videos[0].channel_name
            channel_id = videos[0].channel_id
            if videos[0].description:
                description_text += f" {videos[0].description}"
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")

    # --- AUTO-AGENT PROVISIONING WORKFLOW ---
    assigned_agent_id = request.agent_id

    if not assigned_agent_id:
        # Extract metadata footprints
        found_emails = EMAIL_REGEX.findall(description_text)
        found_phones = MOROCCO_PHONE_REGEX.findall(description_text)

        agent_email = (
            found_emails[0]
            if found_emails
            else f"contact+{channel_id or uuid.uuid4().hex[:6]}@aqar.ai"
        )
        agent_phone = found_phones[0] if found_phones else None

        # Guard against duplicate emails across automatic scans
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
                is_verified=False,
                notes="Automatically provisioned from YouTube channel extraction profile.",
            )
            db.add(new_agent)
            await db.flush()
            assigned_agent_id = new_agent.id

    channel = ChannelRegistration(
        agent_id=assigned_agent_id,
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

    return await _build_channel_response(db, channel)


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    region: str | None = None,
    agent_id: str | None = None,
):
    """List channels with optional filters."""
    query = select(ChannelRegistration).order_by(ChannelRegistration.created_at.desc())
    if status:
        query = query.where(ChannelRegistration.status == status)
    if region:
        query = query.where(ChannelRegistration.region == region)
    if agent_id:
        query = query.where(ChannelRegistration.agent_id == agent_id)

    result = await db.execute(query)
    channels = result.scalars().all()
    return [await _build_channel_response(db, ch) for ch in channels]


@router.post("/channels/{channel_id}/approve", response_model=ChannelResponse)
async def approve_channel(
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_id: uuid.UUID,
    request: ChannelApprovalRequest,
):
    """Approve or reject a channel."""
    ch = (
        await db.execute(select(ChannelRegistration).where(ChannelRegistration.id == channel_id))
    ).scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    if request.status == "approved":
        ch.status = "approved"
        ch.approved_at = datetime.now(UTC)
        if request.max_videos:
            ch.max_videos = request.max_videos
    elif request.status == "rejected":
        ch.status = "rejected"
        ch.rejection_reason = request.rejection_reason
    else:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    await db.flush()
    return await _build_channel_response(db, ch)


@router.post("/channels/{channel_id}/link", response_model=ChannelResponse)
async def link_channel_to_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_id: uuid.UUID,
    request: LinkChannelRequest,
):
    """Link an existing channel to an agent."""
    ch = (
        await db.execute(select(ChannelRegistration).where(ChannelRegistration.id == channel_id))
    ).scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    agent = (
        await db.execute(select(Agent).where(Agent.id == request.agent_id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    ch.agent_id = agent.id
    await db.flush()

    logger.info(f"Channel {channel_id} linked to agent {agent.name}")
    return await _build_channel_response(db, ch)


@router.post("/channels/{channel_id}/disable")
async def disable_channel(db: Annotated[AsyncSession, Depends(get_db)], channel_id: uuid.UUID):
    ch = (
        await db.execute(select(ChannelRegistration).where(ChannelRegistration.id == channel_id))
    ).scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    ch.status = "disabled"
    await db.flush()
    return {"status": "disabled"}


@router.post("/channels/{channel_id}/scan")
async def trigger_channel_scan(
    db: Annotated[AsyncSession, Depends(get_db)],
    channel_id: uuid.UUID,
):
    """
    Trigger immediate video discovery for a specific channel.

    This is the key function: it scans the channel for videos,
    and for each new video, submits it to the full pipeline:
    ingest -> audio -> transcribe -> extract -> geocode -> DONE
    """
    ch = (
        await db.execute(select(ChannelRegistration).where(ChannelRegistration.id == channel_id))
    ).scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")

    from aqar_pipeline.stages.ingestion import ingest_video
    from aqar_pipeline.utils.youtube import fetch_channel_videos

    try:
        videos = fetch_channel_videos(ch.channel_url, max_videos=ch.max_videos)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Channel scan failed: {e}") from e

    # Check which videos are already in the system
    submitted = 0
    skipped = 0
    for video in videos:
        existing = await db.execute(
            select(VideoSource).where(VideoSource.external_id == video.external_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Submit to pipeline: this triggers the FULL chain
        # ingest_video -> extract_audio -> transcribe_audio -> extract_properties -> geocode_properties -> COMPLETED
        ingest_video.delay(video.url)
        submitted += 1

    logger.info(f"Channel scan: {submitted} new, {skipped} existing from {ch.channel_name}")
    return {
        "status": "scan_completed",
        "channel": ch.channel_name,
        "videos_found": len(videos),
        "submitted": submitted,
        "skipped_existing": skipped,
    }


# ═══════════════════════════════════════
# YouTube Discovery
# ═══════════════════════════════════════


@router.post("/channels/discover", response_model=list[DiscoveredChannel])
async def discover_youtube_channels(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: YouTubeSearchRequest,
):
    """
    Search YouTube for real estate channels.

    Returns channels with quality indicators:
    recent uploads, video count, and whether already registered.
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
    seen_channels: dict[str, dict] = {}

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get("entries", []) if info else []

            for entry in entries:
                if not entry:
                    continue
                ch_id = entry.get("channel_id", "")
                if not ch_id or ch_id in seen_channels:
                    # Aggregate: track most recent video per channel
                    if ch_id in seen_channels:
                        existing = seen_channels[ch_id]
                        existing["video_count"] = (existing.get("video_count") or 0) + 1
                    continue

                ch_name = entry.get("channel", entry.get("uploader", "Unknown"))
                ch_url = entry.get("channel_url", f"https://www.youtube.com/channel/{ch_id}")

                seen_channels[ch_id] = {
                    "channel_id": ch_id,
                    "channel_name": ch_name,
                    "channel_url": ch_url,
                    "description": (entry.get("description", "") or "")[:300],
                    "video_count": 1,
                    "recent_upload": entry.get("title", ""),
                    "recent_upload_date": entry.get("upload_date", ""),
                }

        # Check registration status for each channel
        for ch_id, ch_data in seen_channels.items():
            existing = (
                await db.execute(
                    select(ChannelRegistration).where(ChannelRegistration.channel_id == ch_id)
                )
            ).scalar_one_or_none()

            results.append(
                DiscoveredChannel(
                    channel_id=ch_data["channel_id"],
                    channel_name=ch_data["channel_name"],
                    channel_url=ch_data["channel_url"],
                    description=ch_data["description"],
                    video_count=ch_data["video_count"],
                    recent_upload=ch_data["recent_upload"],
                    recent_upload_date=ch_data["recent_upload_date"],
                    already_registered=existing is not None,
                    existing_channel_id=str(existing.id) if existing else None,
                )
            )

        # Sort: unregistered first, then by video count
        results.sort(key=lambda x: (x.already_registered, -(x.video_count or 0)))

    except Exception as e:
        logger.error(f"YouTube discovery error: {e}")
        raise HTTPException(status_code=500, detail=f"YouTube search failed: {e}") from e

    return results


# ═══════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════


async def _build_agent_detail(db: AsyncSession, agent: Agent) -> AgentDetailResponse:
    """Build a full agent detail response with channels and properties."""
    # Get channels
    ch_result = await db.execute(
        select(ChannelRegistration)
        .where(ChannelRegistration.agent_id == agent.id)
        .order_by(ChannelRegistration.created_at.desc())
    )
    channels = [
        ChannelSummary(
            id=str(ch.id),
            channel_url=ch.channel_url,
            channel_name=ch.channel_name,
            status=ch.status,
            max_videos=ch.max_videos,
            created_at=ch.created_at.isoformat() if ch.created_at else "",
        )
        for ch in ch_result.scalars().all()
    ]

    # Get properties linked to this agent's channels
    prop_result = await db.execute(
        select(Property)
        .join(VideoSource, Property.video_source_id == VideoSource.id)
        .join(ChannelRegistration, VideoSource.channel_id == ChannelRegistration.channel_id)
        .where(ChannelRegistration.agent_id == agent.id)
        .order_by(Property.created_at.desc())
        .limit(20)
    )
    props = prop_result.scalars().all()

    properties = []
    for p in props:
        # Get neighborhood from location if available
        neighborhood = None
        if p.location:
            neighborhood = p.location.neighborhood
        properties.append(
            PropertySummary(
                id=str(p.id),
                title=p.title_generated,
                property_type=p.property_type.value if p.property_type else "other",
                price=p.price,
                neighborhood=neighborhood,
                is_published=p.is_published,
                created_at=p.created_at.isoformat() if p.created_at else "",
            )
        )

    total_published = sum(1 for p in properties if p.is_published)

    return AgentDetailResponse(
        id=str(agent.id),
        name=agent.name,
        email=agent.email,
        phone=agent.phone,
        company=agent.company,
        city=agent.city,
        country=agent.country or "Morocco",
        is_verified=agent.is_verified,
        notes=agent.notes,
        created_at=agent.created_at.isoformat() if agent.created_at else "",
        channels=channels,
        properties=properties,
        total_properties=len(properties),
        total_published=total_published,
    )


async def _build_channel_response(db: AsyncSession, ch: ChannelRegistration) -> ChannelResponse:
    agent_name = None
    if ch.agent_id:
        agent = (
            await db.execute(select(Agent.name).where(Agent.id == ch.agent_id))
        ).scalar_one_or_none()
        agent_name = agent

    return ChannelResponse(
        id=str(ch.id),
        channel_url=ch.channel_url,
        channel_name=ch.channel_name,
        channel_id=ch.channel_id,
        description=ch.description,
        region=ch.region,
        status=ch.status,
        max_videos=ch.max_videos,
        discovered_via=ch.discovered_via,
        rejection_reason=ch.rejection_reason,
        agent_id=str(ch.agent_id) if ch.agent_id else None,
        agent_name=agent_name,
        tags=ch.tags,
        created_at=ch.created_at.isoformat() if ch.created_at else "",
        approved_at=ch.approved_at.isoformat() if ch.approved_at else None,
    )
