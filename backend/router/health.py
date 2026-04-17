from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from ..database import session_object, Admin, HealthInsight, Astronaut
from ..oauth2 import get_current_admin
from ..health_service import (
    get_astronaut_report,
    get_all_astronauts_summary,
    get_recent_critical_alerts,
)

logger = logging.getLogger("maitri.health_router")
router = APIRouter(prefix="/api/v1/health", tags=["Health Reports"])


@router.get("/alerts")
async def critical_alerts(
<<<<<<< HEAD
    db: session_object,
    limit: int = 20,
=======
    limit: int = 20,
    db: session_object = None,
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
    admin: Admin = Depends(get_current_admin),
):
    """
    Most recent CRITICAL and HIGH severity alerts across all astronauts.
    This is the first thing an admin should check.
    """
    alerts = await get_recent_critical_alerts(db, limit=min(limit, 100))
    return {
        "total": len(alerts),
        "alerts": alerts,
    }


@router.get("/summary")
async def all_astronauts_summary(
<<<<<<< HEAD
    db: session_object,
=======
    db: session_object = None,
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
    admin: Admin = Depends(get_current_admin),
):
    """
    Dashboard view — all astronauts ranked by risk level (critical first).
    Shows overall risk, severity breakdown, and latest insight per astronaut.
    """
    return await get_all_astronauts_summary(db)


@router.get("/astronaut/{astronaut_id}")
async def astronaut_report(
    astronaut_id: int,
<<<<<<< HEAD
    db: session_object,
    limit: int = 50,
=======
    limit: int = 50,
    db: session_object = None,
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
    admin: Admin = Depends(get_current_admin),
):
    """
    Full prioritized health report for a specific astronaut.
    Insights sorted: critical → high → medium → low, then by recency.
    """
    # Verify astronaut exists
    astronaut = await db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")

    report = await get_astronaut_report(db, astronaut_id, limit=min(limit, 200))
    return report


@router.delete("/insights/{insight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_insight(
    insight_id: int,
<<<<<<< HEAD
    db: session_object,
=======
    db: session_object = None,
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
    admin: Admin = Depends(get_current_admin),
):
    """
    Dismiss/delete a resolved health insight.
    Use when an issue has been addressed and admin has followed up.
    """
    insight = await db.get(HealthInsight, insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    await db.delete(insight)
    await db.commit()
    logger.info(f"Admin {admin.id} dismissed health insight {insight_id}")


@router.get("/astronauts")
async def list_astronauts(
<<<<<<< HEAD
    db: session_object,
=======
    db: session_object = None,
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
    admin: Admin = Depends(get_current_admin),
):
    """List all registered astronauts with their IDs — useful for building the report UI."""
    result = await db.exec(select(Astronaut).order_by(Astronaut.created_at))
    astronauts = result.all()
    return {
        "total": len(astronauts),
        "astronauts": [
            {
                "id":         a.id,
                "email":      a.email,
                "created_at": a.created_at.isoformat(),
            }
            for a in astronauts
        ],
    }
