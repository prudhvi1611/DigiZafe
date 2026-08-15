import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.config import get_settings
from app.domain.scan_states import is_terminal_scan
from app.schemas.scan import (
    FindingPublic,
    ScanCreate,
    ScanListItem,
    ScanPublic,
)
from app.services.discovery_service import DiscoveryService

router = APIRouter(tags=["scans"])


def _svc(db: AsyncSession = Depends(get_db)) -> DiscoveryService:
    return DiscoveryService(db)


@router.post("/scans", response_model=ScanPublic, status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: ScanCreate,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    """
    Start a discovery scan for a **verified** identifier (G1).
    Work runs in Celery worker — not in the request path.
    """
    scan = await svc.create_scan(
        current_user.id,
        body.identifier_id,
        connector_ids=body.connector_ids,
        layer_scope=body.layer_scope,
    )
    return ScanPublic.model_validate(scan)


@router.get("/scans", response_model=list[ScanListItem])
async def list_scans(
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: DiscoveryService = Depends(_svc),
):
    rows = await svc.list_scans(current_user.id, limit=limit, offset=offset)
    return [ScanListItem.model_validate(r) for r in rows]


@router.get("/scans/{scan_id}", response_model=ScanPublic)
async def get_scan(
    scan_id: UUID,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    scan = await svc.get_scan(current_user.id, scan_id)
    return ScanPublic.model_validate(scan)


@router.post("/scans/{scan_id}/cancel", response_model=ScanPublic)
async def cancel_scan(
    scan_id: UUID,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    scan = await svc.cancel_scan(current_user.id, scan_id)
    return ScanPublic.model_validate(scan)


@router.get("/scans/{scan_id}/events")
async def scan_events_sse(
    scan_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events stream of scan progress.
    Polls DB (Postgres is source of truth). Compatible with EventSource.
    """
    settings = get_settings()
    svc = DiscoveryService(db)
    # ownership check
    await svc.get_scan(current_user.id, scan_id)

    async def event_generator() -> AsyncIterator[str]:
        started = datetime.now(UTC)
        last_payload = None
        last_heartbeat = datetime.now(UTC)
        event_id = 0

        while True:
            now = datetime.now(UTC)
            if (now - started).total_seconds() > settings.sse_max_duration_seconds:
                event_id += 1
                yield f"id: {event_id}\nevent: timeout\ndata: {json.dumps({'message': 'SSE max duration'})}\n\n"
                break

            # Fresh session read — reuse service with same session (refresh)
            try:
                scan = await svc.get_scan(current_user.id, scan_id)
            except Exception as e:
                event_id += 1
                yield f"id: {event_id}\nevent: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

            payload = {
                "scan_id": str(scan.id),
                "status": scan.status,
                "progress_pct": scan.progress_pct,
                "message": scan.message,
                "observation_count": scan.observation_count,
                "finding_count": scan.finding_count,
                "error": scan.error,
                "connector_runs": [
                    {
                        "connector_id": r.connector_id,
                        "status": r.status,
                        "skip_reason": r.skip_reason,
                        "observation_count": r.observation_count,
                        "finding_count": r.finding_count,
                        "cache_hit": r.cache_hit,
                    }
                    for r in (scan.connector_runs or [])
                ],
                "meta": scan.meta,
                "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
            }
            serialized = json.dumps(payload, default=str)

            if serialized != last_payload:
                last_payload = serialized
                event_id += 1
                yield f"id: {event_id}\nevent: scan\ndata: {serialized}\n\n"

                if is_terminal_scan(scan.status):
                    event_id += 1
                    yield f"id: {event_id}\nevent: done\ndata: {serialized}\n\n"
                    break

            # heartbeat
            if (now - last_heartbeat).total_seconds() >= settings.sse_heartbeat_seconds:
                last_heartbeat = now
                yield f": ping {now.isoformat()}\n\n"

            await asyncio.sleep(settings.sse_poll_interval_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/findings", response_model=list[FindingPublic])
async def list_findings(
    current_user: CurrentUser,
    identifier_id: UUID | None = None,
    source: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: DiscoveryService = Depends(_svc),
):
    rows = await svc.list_findings(
        current_user.id,
        identifier_id=identifier_id,
        source=source,
        limit=limit,
        offset=offset,
    )
    return [FindingPublic.model_validate(r) for r in rows]


@router.get("/findings/{finding_id}", response_model=FindingPublic)
async def get_finding(
    finding_id: UUID,
    current_user: CurrentUser,
    svc: DiscoveryService = Depends(_svc),
):
    row = await svc.get_finding(current_user.id, finding_id)
    return FindingPublic.model_validate(row)
