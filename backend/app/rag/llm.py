"""
Qwen3 LLM service via Ollama for grounded generation.
AI never computes or alters official numbers (P1 golden rule).
"""
from __future__ import annotations

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are MINOVA AI Assistant, helping mining professionals understand their data.

CRITICAL RULES:
1. NEVER compute, calculate, or alter any official numbers. All numbers come from the calculation engine.
2. When citing numbers, ALWAYS reference the source (shift entry, report, calculation run).
3. If asked to change or override a number, refuse and explain that numbers can only be modified through the official data entry and approval workflow.
4. Be precise with units (tonnes, m³, ratios).
5. Answer in the language of the question (Hindi or English).
"""


async def generate_response(
    query: str,
    context_chunks: list[dict],
    conversation_history: list[dict] | None = None,
) -> dict:
    context_text = "\n\n".join(
        f"[Source: {c.get('filename', 'unknown')}, Page {c.get('page', '?')}]\n{c['text']}"
        for c in context_chunks
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    user_message = f"""Context from documents:
---
{context_text}
---

User question: {query}

Provide a grounded answer using ONLY the information from the context above. Cite sources."""

    messages.append({"role": "user", "content": user_message})

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": settings.llm_model,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": settings.llm_temperature,
                    "num_predict": settings.llm_max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    return {
        "content": data["message"]["content"],
        "model": data.get("model", settings.llm_model),
        "eval_count": data.get("eval_count", 0),
    }


async def generate_report_description(
    report_values: list[dict],
    mine_name: str,
    period: str,
) -> str:
    prompt = f"""Generate a brief factual summary for this {period} mining report for {mine_name}.

Report values:
{chr(10).join(f"- {v['metric']}: {v['value']} {v['unit']}" for v in report_values)}

Write 2-3 sentences describing the production performance. Do NOT change any numbers.
Reference the values exactly as provided."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.llm_model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 256},
            },
        )
        response.raise_for_status()
        return response.json()["response"]
