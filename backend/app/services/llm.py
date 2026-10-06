from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import AsyncGenerator

import httpx
import structlog

from app.domain.enums import QueryRouteType

logger = structlog.get_logger()

OLLAMA_BASE = "http://localhost:11434"
MODEL = "qwen3:8b"

# qwen3 is a reasoning model: without this it burns tokens (and often the whole
# request timeout) on hidden chain-of-thought before answering.
NO_THINK = {"think": False}

SYSTEM_GROUNDING = (
    "You are MINOVA AI, a mining operations assistant. "
    "You describe and summarize data. You NEVER compute, estimate, or invent numbers. "
    "Every number you cite must come from the provided data context. "
    "If you don't have data to answer, say so."
)


@dataclass
class QueryRoute:
    route_type: QueryRouteType
    confidence: float
    reasoning: str


@dataclass
class GroundedResponse:
    text: str
    grounded: bool
    ungrounded_numbers: list[str] = field(default_factory=list)


async def generate(prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2048) -> str:
    sys_prompt = system or SYSTEM_GROUNDING
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "system": sys_prompt,
                "stream": False,
                **NO_THINK,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]


async def generate_stream(prompt: str, system: str = "") -> AsyncGenerator[str, None]:
    sys_prompt = system or SYSTEM_GROUNDING
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE}/api/generate",
            json=            {"model": MODEL, "prompt": prompt, "system": sys_prompt, "stream": True, **NO_THINK},
        ) as resp:
            async for line in resp.aiter_lines():
                if line:
                    chunk = json.loads(line)
                    if token := chunk.get("response", ""):
                        yield token
                    if chunk.get("done"):
                        return


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d[\d,]*\.?\d*\b", text))


async def generate_grounded_description(data: dict, context: str = "") -> GroundedResponse:
    data_str = json.dumps(data, indent=2, default=str)
    prompt = (
        f"Based ONLY on the following data, write a concise summary.\n\n"
        f"DATA:\n{data_str}\n\n"
        f"{'CONTEXT: ' + context if context else ''}\n"
        f"Write 2-3 sentences. Only reference numbers present in the data."
    )
    text = await generate(prompt, temperature=0.2)
    data_numbers = _extract_numbers(data_str)
    response_numbers = _extract_numbers(text)
    ungrounded = [n for n in response_numbers if n not in data_numbers and n not in {"1", "2", "3"}]
    return GroundedResponse(text=text, grounded=len(ungrounded) == 0, ungrounded_numbers=ungrounded)


async def route_query(query: str) -> QueryRoute:
    prompt = (
        f'Classify this mining query into exactly one category.\n'
        f'Query: "{query}"\n\n'
        f'Categories:\n'
        f'- NUMERIC: needs a specific number (production, tonnage, ratio, count)\n'
        f'- DESCRIPTIVE: needs explanation, process, or qualitative answer\n'
        f'- HYBRID: needs both numbers and explanation\n\n'
        f'Reply with JSON: {{"category": "...", "confidence": 0.0-1.0, "reason": "..."}}'
    )
    text = await generate(prompt, system="You classify queries. Reply only with valid JSON.", temperature=0.1)
    try:
        clean = text.strip()
        if "```" in clean:
            clean = clean.split("```")[1].strip().removeprefix("json").strip()
        parsed = json.loads(clean)
        cat_map = {"NUMERIC": QueryRouteType.numeric, "DESCRIPTIVE": QueryRouteType.descriptive, "HYBRID": QueryRouteType.hybrid}
        return QueryRoute(
            route_type=cat_map.get(parsed.get("category", "").upper(), QueryRouteType.hybrid),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reason", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return QueryRoute(route_type=QueryRouteType.hybrid, confidence=0.3, reasoning="Failed to parse LLM classification")
