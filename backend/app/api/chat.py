from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    ChatMessageIn,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    Page,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUser, resolve_app_user
from app.domain.enums import QueryRouteType
from app.domain.models import ChatMessage, ChatSession

router = APIRouter()


def _classify_query(content: str) -> QueryRouteType:
    lower = content.lower()
    numeric_keywords = [
        "how much", "how many", "total", "sum", "count", "target", "actual",
        "production", "tonnes", "dispatch", "output", "mtpa",
    ]
    contextual_keywords = [
        "why", "explain", "describe", "what happened", "reason", "cause",
        "report", "document", "summary",
    ]
    has_numeric = any(kw in lower for kw in numeric_keywords)
    has_contextual = any(kw in lower for kw in contextual_keywords)

    if has_numeric and has_contextual:
        return QueryRouteType.HYBRID
    if has_numeric:
        return QueryRouteType.NUMERIC
    if has_contextual:
        return QueryRouteType.CONTEXTUAL
    if any(kw in lower for kw in ["plan", "forecast", "recovery", "schedule", "suggest"]):
        return QueryRouteType.PLANNING
    if any(kw in lower for kw in ["anomal", "outlier", "unusual", "flag"]):
        # Anomaly questions need both the anomaly table and narrative reasoning.
        return QueryRouteType.HYBRID
    return QueryRouteType.OUT_OF_SCOPE


@router.post("/sessions", response_model=ChatSessionOut)
async def create_session(
    body: ChatSessionCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    app_user = await resolve_app_user(db, user)
    session = ChatSession(
        user_id=app_user.id,
        title=body.title or "New conversation",
    )
    db.add(session)
    await db.flush()
    return session


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    user: CurrentUser,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(ChatSession).order_by(ChatSession.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_messages(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session_res = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    if not session_res.scalar_one_or_none():
        raise HTTPException(404, "Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageOut)
async def send_message(
    session_id: uuid.UUID,
    body: ChatMessageIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session_res = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    if not session_res.scalar_one_or_none():
        raise HTTPException(404, "Session not found")

    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    route = _classify_query(body.content)

    import httpx
    citations: dict = {}
    answer_content = ""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.llm_model,
                    "prompt": body.content,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": settings.llm_temperature},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                answer_content = data.get("response", "I could not generate a response.")
            else:
                answer_content = "LLM service is unavailable. Please try again later."
    except Exception:
        answer_content = "LLM service is unavailable. Please try again later."

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer_content,
        route_type=route,
        citations=citations if citations else None,
    )
    db.add(assistant_msg)
    await db.flush()

    return assistant_msg


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: uuid.UUID,
    body: ChatMessageIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session_res = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    if not session_res.scalar_one_or_none():
        raise HTTPException(404, "Session not found")

    user_msg = ChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    await db.flush()

    import httpx

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.llm_model,
                        "prompt": body.content,
                        "stream": True,
                        "think": False,
                        "options": {"temperature": settings.llm_temperature},
                    },
                ) as resp:
                    full_response = ""
                    async for line in resp.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            full_response += token
                            yield f"data: {json.dumps({'token': token})}\n\n"
                            if chunk.get("done"):
                                break
                    yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/message", response_model=ChatMessageOut)
async def send_message_sessionless(
    body: ChatMessageIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Convenience endpoint: auto-creates a session if needed, sends a message,
    and returns the assistant response. Used by the portal's simple chat UI."""
    app_user = await resolve_app_user(db, user)
    session = ChatSession(
        user_id=app_user.id,
        title=body.content[:60],
    )
    db.add(session)
    await db.flush()

    user_msg = ChatMessage(session_id=session.id, role="user", content=body.content)
    db.add(user_msg)
    await db.flush()

    route = _classify_query(body.content)

    rag_context = ""
    citations_list: list[dict] = []
    if route in (QueryRouteType.CONTEXTUAL, QueryRouteType.HYBRID):
        from sqlalchemy import text as sql_text
        kw_sql = sql_text("""
            SELECT dc.id, dc.document_id, dc.page_number, dc.text, d.filename
            FROM doc_chunk dc
            JOIN document d ON d.id = dc.document_id
            WHERE dc.tsv @@ websearch_to_tsquery('english', :query)
            ORDER BY ts_rank(dc.tsv, websearch_to_tsquery('english', :query)) DESC
            LIMIT 5
        """)
        try:
            kw_rows = (await db.execute(kw_sql, {"query": body.content})).fetchall()
            for i, row in enumerate(kw_rows):
                rag_context += f"\n[Source {i+1}: {row[4]}, page {row[2]}]\n{row[3][:400]}\n"
                citations_list.append({
                    "type": "document",
                    "id": str(row[1]),
                    "label": f"{row[4]} p.{row[2]}",
                    "page": row[2],
                })
        except Exception:
            pass

    if route == QueryRouteType.NUMERIC:
        from app.domain.models import ShiftEntry, EntryValue
        from app.domain.enums import EntryStatus
        from sqlalchemy import func
        try:
            prod_q = (
                select(
                    func.date(ShiftEntry.shift_date).label("d"),
                    func.sum(EntryValue.value).label("total"),
                )
                .join(ShiftEntry, ShiftEntry.id == EntryValue.entry_id)
                .where(
                    ShiftEntry.status.in_([EntryStatus.APPROVED, EntryStatus.SUBMITTED]),
                    EntryValue.metric == "production_tonnes",
                )
                .group_by(func.date(ShiftEntry.shift_date))
                .order_by(func.date(ShiftEntry.shift_date).desc())
                .limit(7)
            )
            rows = (await db.execute(prod_q)).fetchall()
            if rows:
                rag_context += "\n[Production data from database]\n"
                for row in rows:
                    rag_context += f"  {row[0]}: {float(row[1]):,.0f} tonnes\n"
                citations_list.append({"type": "database", "id": "entry_values", "label": "Shift entry data"})
        except Exception:
            pass

    if route in (QueryRouteType.NUMERIC, QueryRouteType.HYBRID) or "anomal" in body.content.lower():
        from app.domain.models import AnomalyFlag, Mine
        from app.domain.enums import AnomalyStatus
        from sqlalchemy import func
        try:
            anomaly_q = (
                select(
                    AnomalyFlag.flag_date,
                    AnomalyFlag.metric,
                    AnomalyFlag.actual_value,
                    AnomalyFlag.expected_value,
                    AnomalyFlag.anomaly_score,
                    AnomalyFlag.explanation,
                    Mine.name,
                )
                .join(Mine, Mine.id == AnomalyFlag.mine_id)
                .where(AnomalyFlag.status.in_([AnomalyStatus.FLAGGED, AnomalyStatus.ACKNOWLEDGED]))
                .order_by(AnomalyFlag.flag_date.desc())
                .limit(10)
            )
            a_rows = (await db.execute(anomaly_q)).fetchall()
            if a_rows:
                rag_context += "\n[Active anomalies from database (status flagged or acknowledged)]\n"
                for r in a_rows:
                    deviation = float(r[2]) - float(r[3])
                    rag_context += (
                        f"  {r[6]} | {r[1]} on {r[0].date().isoformat()} | "
                        f"actual {float(r[2]):,.2f} vs expected {float(r[3]):,.2f} "
                        f"(deviation {deviation:+,.2f}) | score {float(r[4]):.2f} | {r[5][:200]}\n"
                    )
                citations_list.append({"type": "database", "id": "anomaly_flag", "label": "Anomaly flags"})
            else:
                rag_context += "\n[Database check: no anomalies with status flagged or acknowledged exist.]\n"
        except Exception:
            pass

    system_prompt = (
        "You are MINOVA AI Assistant for CIL/CMPDI mining operations. "
        "Answer questions about production, targets, causes, documents, and mine operations. "
        "Always cite your sources. Be concise and factual. Support English and Hindi queries.\n"
        "CRITICAL: Only state facts found in the provided context. Never invent anomalies, "
        "equipment, incidents, or sources. If the context does not contain the answer, say "
        "exactly that instead of guessing."
    )
    if rag_context:
        system_prompt += f"\nRelevant context:\n{rag_context}\n\nUse the above context to answer. Cite sources by number."

    import httpx
    answer_content = ""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.llm_model,
                    "system": system_prompt,
                    "prompt": body.content,
                    "stream": False,
                    "think": False,
                    "options": {"temperature": settings.llm_temperature},
                },
            )
            if resp.status_code == 200:
                answer_content = resp.json().get("response", "I could not generate a response.")
            else:
                answer_content = "LLM service is unavailable. Please try again later."
    except Exception:
        answer_content = "LLM service is unavailable. Please try again later."

    citations_dict = {"sources": citations_list} if citations_list else None

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_content,
        route_type=route,
        citations=citations_dict,
    )
    db.add(assistant_msg)
    await db.flush()
    return assistant_msg


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session_res = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    msgs_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msgs_res.scalars().all()

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 780, f"MINOVA AI Chat — {session.title}")
    c.setFont("Helvetica", 9)
    y = 755

    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, f"[{role_label}] ({msg.created_at.strftime('%H:%M:%S')}):")
        y -= 12
        c.setFont("Helvetica", 9)
        for line in msg.content.split("\n"):
            for i in range(0, len(line), 90):
                c.drawString(60, y, line[i : i + 90])
                y -= 11
                if y < 50:
                    c.showPage()
                    y = 780
                    c.setFont("Helvetica", 9)
        y -= 6

    c.save()
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="chat_{session_id}.pdf"'},
    )
