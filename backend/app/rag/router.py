"""
RAG query router — classifies user queries and routes to appropriate handler.
Types: NUMERIC (calculation engine), CONTEXTUAL (document RAG), HYBRID, PLANNING, OUT_OF_SCOPE.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RouteType(str, Enum):
    NUMERIC = "numeric"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"
    PLANNING = "planning"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class RouteDecision:
    route_type: RouteType
    confidence: float
    reasoning: str


NUMERIC_PATTERNS = [
    r"\b(total|sum|count|average|mean|production|tonnage|output)\b.*\b(tonnes?|t|mt|kt)\b",
    r"\b(how much|how many|what is the|calculate|compute)\b",
    r"\b(stripping ratio|ob.*coal|target.*vs.*actual)\b",
    r"\b(\d+\s*\+\s*\d+|\d+\s*[\*\/]\s*\d+)\b",
    r"\b(cumulative|year.to.date|ytd|mtd|qtd)\b",
]

PLANNING_PATTERNS = [
    r"\b(recovery plan|catch up|make up|shortfall|gap|behind target)\b",
    r"\b(weather.*impact|rain.*delay|monsoon)\b",
    r"\b(forecast|predict|projection|next week|next month)\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\b(stock price|cricket|movie|recipe|joke)\b",
    r"\b(write.*code|generate.*program|hack|bypass)\b",
]


def route_query(query: str) -> RouteDecision:
    q = query.lower().strip()

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, q):
            return RouteDecision(RouteType.OUT_OF_SCOPE, 0.95, "Query outside mining domain")

    numeric_score = sum(1 for p in NUMERIC_PATTERNS if re.search(p, q))
    planning_score = sum(1 for p in PLANNING_PATTERNS if re.search(p, q))

    if planning_score >= 2:
        return RouteDecision(RouteType.PLANNING, 0.8 + planning_score * 0.05, "Planning/recovery query detected")

    if numeric_score >= 2:
        return RouteDecision(RouteType.NUMERIC, 0.8 + numeric_score * 0.05, "Numerical/calculation query")

    if numeric_score == 1:
        return RouteDecision(RouteType.HYBRID, 0.7, "Mixed numeric and contextual query")

    return RouteDecision(RouteType.CONTEXTUAL, 0.75, "Document/context retrieval query")
