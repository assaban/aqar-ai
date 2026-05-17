# Feature: Agent Portal, Admin Discovery, and Property Improvements

> **Sprint:** Backlog: Quality and UX improvements
> **Branch:** `feature/AQAR-agent-portal`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-13
> **Status:** In Progress

---

## Scope

### 1. Property Detail 404 Fix
- SSR pages fetch from Docker-internal API URL (server-side) vs browser URL (client-side)
- Video embed already exists but page fails to load

### 2. Agent/Channel Admin System
- Agents can register and add their YouTube channels
- Admin approval workflow for new channels
- Admin page to manage agents and channels
- Channel status: pending, approved, rejected, disabled

### 3. Property Summary on Search Cards
- Short summary extracted from transcript and/or video description
- Displayed on search result cards

### 4. Admin Channel Discovery
- Admin can search YouTube for channels by keyword and region
- Discovered channels can be added to the monitoring list
- Uses yt-dlp to search YouTube

### 5. Database Models
- New: Agent, ChannelRegistration models
- Channel approval status enum

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
