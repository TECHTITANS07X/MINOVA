"""
Open-Meteo weather service — no API key needed.
Fetches historical observations and 7-day forecasts for mine locations.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

BASE_URL = settings.OPEN_METEO_BASE_URL


async def fetch_weather_observations(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BASE_URL}/archive", params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "Asia/Kolkata",
        })
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    results = []
    for i, d in enumerate(dates):
        results.append({
            "observation_date": d,
            "temperature_max": daily.get("temperature_2m_max", [None])[i],
            "temperature_min": daily.get("temperature_2m_min", [None])[i],
            "precipitation_mm": daily.get("precipitation_sum", [0])[i] or 0,
            "wind_speed_kmh": daily.get("wind_speed_10m_max", [None])[i],
            "source": "open_meteo",
        })
    return results


async def fetch_weather_forecast(
    latitude: float,
    longitude: float,
) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BASE_URL}/forecast", params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,precipitation_sum,weather_code",
            "timezone": "Asia/Kolkata",
            "forecast_days": 7,
        })
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    results = []
    for i, d in enumerate(dates):
        results.append({
            "forecast_date": d,
            "temperature_max": daily.get("temperature_2m_max", [None])[i],
            "precipitation_mm": daily.get("precipitation_sum", [0])[i] or 0,
            "weather_code": daily.get("weather_code", [None])[i],
        })
    return results


def assess_weather_impact(precipitation_mm: float) -> dict:
    if precipitation_mm > 50:
        return {"impact": "high", "expected_loss_pct": 40, "note": "Heavy rain — expect significant delays"}
    elif precipitation_mm > 20:
        return {"impact": "moderate", "expected_loss_pct": 20, "note": "Moderate rain — partial operations possible"}
    elif precipitation_mm > 5:
        return {"impact": "low", "expected_loss_pct": 5, "note": "Light rain — minimal impact expected"}
    return {"impact": "none", "expected_loss_pct": 0, "note": "Clear weather — full operations"}
