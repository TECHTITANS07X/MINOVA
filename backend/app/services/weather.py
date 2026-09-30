from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from datetime import date, datetime

import httpx
import structlog

logger = structlog.get_logger()

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"


@dataclass
class WeatherRecord:
    dt: date
    temp_max: float
    temp_min: float
    precip_mm: float
    wind_kph: float
    humidity: float | None = None


@dataclass
class WeatherImpact:
    impact_pct: Decimal
    adjusted_target: Decimal
    reason: str
    risk_level: str


async def fetch_observations(lat: float, lon: float, start_date: str, end_date: str) -> list[WeatherRecord]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean",
        "timezone": "Asia/Kolkata",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{OPEN_METEO_BASE}/forecast", params=params)
        resp.raise_for_status()
        data = resp.json()
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    records = []
    for i, d in enumerate(dates):
        records.append(WeatherRecord(
            dt=date.fromisoformat(d),
            temp_max=daily["temperature_2m_max"][i] or 0,
            temp_min=daily["temperature_2m_min"][i] or 0,
            precip_mm=daily["precipitation_sum"][i] or 0,
            wind_kph=daily["wind_speed_10m_max"][i] or 0,
            humidity=(daily.get("relative_humidity_2m_mean") or [None] * len(dates))[i],
        ))
    return records


async def fetch_forecast(lat: float, lon: float, days: int = 7) -> list[WeatherRecord]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "forecast_days": days,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "Asia/Kolkata",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{OPEN_METEO_BASE}/forecast", params=params)
        resp.raise_for_status()
        data = resp.json()
    daily = data.get("daily", {})
    return [
        WeatherRecord(
            dt=date.fromisoformat(d),
            temp_max=daily["temperature_2m_max"][i] or 0,
            temp_min=daily["temperature_2m_min"][i] or 0,
            precip_mm=daily["precipitation_sum"][i] or 0,
            wind_kph=daily["wind_speed_10m_max"][i] or 0,
        )
        for i, d in enumerate(daily.get("time", []))
    ]


def compute_weather_impact(observations: list[WeatherRecord], target_daily: Decimal) -> WeatherImpact:
    if not observations:
        return WeatherImpact(Decimal("0"), target_daily, "No weather data", "low")

    total_precip = sum(o.precip_mm for o in observations)
    max_wind = max(o.wind_kph for o in observations)
    max_temp = max(o.temp_max for o in observations)
    avg_precip = total_precip / len(observations)

    impact = Decimal("0")
    reasons = []

    if avg_precip > 50:
        impact += Decimal("30")
        reasons.append(f"Heavy rain ({avg_precip:.0f}mm avg) — 30% reduction")
    elif avg_precip > 20:
        impact += Decimal("15")
        reasons.append(f"Moderate rain ({avg_precip:.0f}mm avg) — 15% reduction")
    elif avg_precip > 5:
        impact += Decimal("5")
        reasons.append(f"Light rain ({avg_precip:.0f}mm avg) — 5% reduction")

    if max_wind > 60:
        impact += Decimal("20")
        reasons.append(f"Storm winds ({max_wind:.0f} kph) — 20% reduction")
    elif max_wind > 40:
        impact += Decimal("10")
        reasons.append(f"Strong winds ({max_wind:.0f} kph) — 10% reduction")

    if max_temp > 45:
        impact += Decimal("10")
        reasons.append(f"Extreme heat ({max_temp:.0f}°C) — 10% reduction")

    impact = min(impact, Decimal("60"))
    adjusted = target_daily * (Decimal("100") - impact) / Decimal("100")

    risk = "low"
    if impact >= 30:
        risk = "high"
    elif impact >= 15:
        risk = "medium"

    return WeatherImpact(
        impact_pct=impact,
        adjusted_target=adjusted,
        reason="; ".join(reasons) if reasons else "Clear conditions — no impact",
        risk_level=risk,
    )
