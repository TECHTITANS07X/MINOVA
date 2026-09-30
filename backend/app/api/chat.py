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
from app.core.security import CurrentUser
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
    return QueryRouteType.OUT_OF_SCOPE


@router.post("/sessions", response_model=ChatSessionOut)
async def create_session(
    body: ChatSessionCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(
        user_id=uuid.UUID(user.sub) if user.sub else uuid.uuid4(),
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
