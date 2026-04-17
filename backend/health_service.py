from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from typing import Optional

from groq import Groq
from sqlmodel import select, desc, func
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import settings
from .database import HealthInsight, Astronaut, Messages

logger = logging.getLogger("maitri.health")

# ── Severity ordering for sorting ─────────────────────────────────────────────
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}


@lru_cache(maxsize=1)
def _groq_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


# ── Analysis prompt ───────────────────────────────────────────────────────────

_ANALYSIS_SYSTEM = """You are a clinical psychologist AI assistant analyzing messages from astronauts on long-duration space missions.

Your task is to detect psychological and physical health signals from the astronaut's message and recent conversation context.

You MUST respond with ONLY a valid JSON object — no prose, no markdown, no explanation.

JSON schema:
{
  "severity": "<critical|high|medium|low|none>",
  "insight_type": "<concise category, e.g. 'anxiety', 'depression_signs', 'isolation', 'sleep_deprivation', 'acute_stress', 'suicidal_ideation', 'physical_pain', 'cognitive_decline', 'none'>",
  "summary": "<1-2 sentence plain English summary of what was detected, or 'No significant health signals detected'>",
  "indicators": ["<specific phrase or signal from the message that triggered this>"],
  "recommended_action": "<what the admin/mission control should do, or 'No action required'>",
  "confidence": <0.0 to 1.0>
}

Severity definitions:
- critical: immediate risk to life or mission safety (suicidal ideation, acute psychosis, medical emergency, complete breakdown)
- high: significant psychological distress needing prompt attention (severe anxiety, depression indicators, prolonged sleep loss, dangerous isolation)
- medium: notable concern worth monitoring (persistent low mood, elevated stress, social withdrawal, fatigue patterns)
- low: mild or transient signal (momentary frustration, minor worry, expressed tiredness)
- none: normal communication, no health signals

Be conservative — only flag genuine signals. Do NOT pathologize normal expressions of preference or minor emotion.
If severity is 'none', set insight_type to 'none' and indicators to [].
"""


# ── Core analysis function ────────────────────────────────────────────────────

async def analyze_message(
    db: AsyncSession,
    astronaut_id: int,
    message_id: int,
    message_content: str,
    recent_history: list[dict],
) -> Optional[HealthInsight]:
    """
    Analyze a single astronaut message for health signals.
    Saves a HealthInsight record if severity is not 'none'.
    Returns the saved insight or None.

    Called as a fire-and-forget background task from /chat/send.
    """
    try:
        # Build context from recent history (last 6 messages for context)
        history_text = ""
        if recent_history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in recent_history[-6:]
            )

        user_prompt = f"""Recent conversation context:
{history_text if history_text else "(no prior context)"}

Current astronaut message to analyze:
\"\"\"{message_content}\"\"\"

Analyze this message for health signals and respond with JSON only."""

        client = _groq_client()
        t0 = time.time()

        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": _ANALYSIS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        latency_ms = int((time.time() - t0) * 1000)
        raw = resp.choices[0].message.content

        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Health analysis returned invalid JSON for msg {message_id}: {raw}")
            return None

        severity = analysis.get("severity", "none").lower()
        insight_type = analysis.get("insight_type", "none").lower()

        # Don't store 'none' records — keeps the table clean
        if severity == "none" or insight_type == "none":
            logger.debug(f"No health signals in message {message_id} (latency:{latency_ms}ms)")
            return None

        insight = HealthInsight(
            astronaut_id=astronaut_id,
            message_id=message_id,
            insight_type=insight_type,
            severity=severity,
            details={
                "summary":              analysis.get("summary", ""),
                "indicators":           analysis.get("indicators", []),
                "recommended_action":   analysis.get("recommended_action", ""),
                "confidence":           analysis.get("confidence", 0.0),
                "analysis_latency_ms":  latency_ms,
                "raw_message_snippet":  message_content[:200],
            },
        )
        db.add(insight)
        await db.commit()
        await db.refresh(insight)

        logger.info(
            f"Health insight saved — astronaut:{astronaut_id} msg:{message_id} "
            f"severity:{severity} type:{insight_type} confidence:{analysis.get('confidence', '?')}"
        )

        # Extra loud log for critical issues so they don't get buried
        if severity == "critical":
            logger.critical(
                f"⚠ CRITICAL HEALTH ALERT — astronaut_id:{astronaut_id} "
                f"type:{insight_type} summary:{analysis.get('summary', '')}"
            )

        return insight

    except Exception as exc:
        logger.error(
            f"Health analysis failed for message {message_id}: {exc}",
            exc_info=True,
        )
        return None


# ── Report queries (used by admin router) ────────────────────────────────────

async def get_astronaut_report(
    db: AsyncSession,
    astronaut_id: int,
    limit: int = 50,
) -> dict:
    """
    Full prioritized health report for one astronaut.
    Insights sorted by severity then recency.
    """
    astronaut = await db.get(Astronaut, astronaut_id)
    if not astronaut:
        return {}

    result = await db.exec(
        select(HealthInsight)
        .where(HealthInsight.astronaut_id == astronaut_id)
        .order_by(HealthInsight.created_at.desc())
        .limit(limit)
    )
    insights = list(result.all())

    # Sort by severity priority
    insights.sort(key=lambda x: SEVERITY_ORDER.get(x.severity, 99))

    # Count by severity
    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for ins in insights:
        if ins.severity in severity_counts:
            severity_counts[ins.severity] += 1

    # Overall risk level = highest severity present
    overall = "none"
    for level in ("critical", "high", "medium", "low"):
        if severity_counts[level] > 0:
            overall = level
            break

    return {
        "astronaut_id":    astronaut_id,
        "astronaut_email": astronaut.email,
        "overall_risk":    overall,
        "severity_counts": severity_counts,
        "total_insights":  len(insights),
        "insights": [_format_insight(i) for i in insights],
    }


async def get_all_astronauts_summary(db: AsyncSession) -> dict:
    """
    Dashboard summary for admins — all astronauts ranked by risk level.
    Shows only the most recent + most severe insight per astronaut.
    """
    # Get all astronauts who have at least one insight
    result = await db.exec(
        select(HealthInsight.astronaut_id)
        .distinct()
    )
    astronaut_ids = [row for row in result.all()]

    summaries = []
    for aid in astronaut_ids:
        # Most recent critical/high first, then by date
        result = await db.exec(
            select(HealthInsight)
            .where(HealthInsight.astronaut_id == aid)
            .order_by(HealthInsight.created_at.desc())
            .limit(20)
        )
        insights = list(result.all())
        if not insights:
            continue

        insights.sort(key=lambda x: SEVERITY_ORDER.get(x.severity, 99))
        top = insights[0]

        astronaut = await db.get(Astronaut, aid)
        severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for ins in insights:
            if ins.severity in severity_counts:
                severity_counts[ins.severity] += 1

        summaries.append({
            "astronaut_id":    aid,
            "astronaut_email": astronaut.email if astronaut else "unknown",
            "overall_risk":    top.severity,
            "severity_counts": severity_counts,
            "latest_insight":  _format_insight(top),
            "total_insights":  len(insights),
        })

    # Sort summaries by overall risk
    summaries.sort(key=lambda x: SEVERITY_ORDER.get(x["overall_risk"], 99))

    critical_count = sum(1 for s in summaries if s["overall_risk"] == "critical")
    high_count     = sum(1 for s in summaries if s["overall_risk"] == "high")

    return {
        "total_astronauts_monitored": len(summaries),
        "critical_count": critical_count,
        "high_count":     high_count,
        "astronauts":     summaries,
    }


async def get_recent_critical_alerts(db: AsyncSession, limit: int = 20) -> list:
    """Return the most recent critical + high severity insights across all astronauts."""
    result = await db.exec(
        select(HealthInsight)
        .where(HealthInsight.severity.in_(["critical", "high"]))
        .order_by(HealthInsight.created_at.desc())
        .limit(limit)
    )
    insights = list(result.all())

    out = []
    for ins in insights:
        astronaut = await db.get(Astronaut, ins.astronaut_id)
        entry = _format_insight(ins)
        entry["astronaut_email"] = astronaut.email if astronaut else "unknown"
        out.append(entry)

    return out


def _format_insight(ins: HealthInsight) -> dict:
    return {
        "id":           ins.id,
        "insight_type": ins.insight_type,
        "severity":     ins.severity,
        "summary":      ins.details.get("summary", "") if ins.details else "",
        "indicators":   ins.details.get("indicators", []) if ins.details else [],
        "recommended_action": ins.details.get("recommended_action", "") if ins.details else "",
        "confidence":   ins.details.get("confidence", 0.0) if ins.details else 0.0,
        "message_id":   ins.message_id,
        "created_at":   ins.created_at.isoformat(),
    }