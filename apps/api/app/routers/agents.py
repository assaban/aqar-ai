# apps/api/app/routers/agents.py
"""
Aqar.ai - Agents & Channels Controller
========================================
Thin presentation interface wrapper for routing agent and channel requests.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.services.agent_service import AgentService
from models.base import Agent, ChannelRegistration

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


# ═══════════════════════════════════════
# Thin Route Endpoints
# ═══════════════════════════════════════


@router.get("/agents", response_model=list[AgentListItem])
async def list_agents(
    db: Annotated[AsyncSession, Depends(get_db)],
    city: str | None = None,
    country: str | None = None,
    verified: bool | None = None,
):
    return await AgentService.list_all_agents(db, city, country, verified)


@router.post("/agents", response_model=AgentListItem)
async def create_agent(
    request: AgentCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    agent = await AgentService.create_agent(db, request)
    return AgentListItem(
        id=str(agent.id),
        name=agent.name,
        email=agent.email,
        phone=agent.phone,
        company=agent.company,
        city=agent.city,
        country=agent.country,
        is_verified=agent.is_verified,
        channels_count=0,
        properties_count=0,
        created_at=agent.created_at.isoformat() if agent.created_at else "",
    )


@router.post("/channels", response_model=ChannelResponse, status_code=201)
async def register_channel(
    request: ChannelRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    channel = await AgentService.register_new_channel(db, request)
    return await _build_channel_response(db, channel)


@router.post("/channels/{channel_id}/approve", response_model=ChannelResponse)
async def approve_channel(
    channel_id: uuid.UUID,
    request: ChannelApprovalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ch = await AgentService.modify_channel_status(
        db, channel_id, request.status, request.rejection_reason, request.max_videos
    )
    return await _build_channel_response(db, ch)


# ── Clean Adapter Mapping Logic ──
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
        status=ch.status.value if hasattr(ch.status, "value") else str(ch.status),
        max_videos=ch.max_videos,
        discovered_via=ch.discovered_via,
        rejection_reason=ch.rejection_reason,
        agent_id=str(ch.agent_id) if ch.agent_id else None,
        agent_name=agent_name,
        tags=ch.tags,
        created_at=ch.created_at.isoformat() if ch.created_at else "",
        approved_at=ch.approved_at.isoformat() if ch.approved_at else None,
    )
