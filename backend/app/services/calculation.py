"""
MINOVA Deterministic Calculation Engine — the single source of truth for all
mining production numbers.  Every computation uses ``Decimal`` with explicit
rounding (ROUND_HALF_EVEN).  Every invocation produces a ``CalcRunRecord``
whose ``input_hash`` guarantees reproducibility.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from enum import Enum
from typing import Sequence
from uuid import uuid4

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRECISION = Decimal("0.0001")
ROUNDING = ROUND_HALF_EVEN
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

class MassUnit(str, Enum):
    TONNES = "t"
    KILOTONNES = "kt"
    MEGATONNES = "Mt"


class VolumeUnit(str, Enum):
    CUBIC_METRES = "m3"
    THOUSAND_CUBIC_METRES = "km3"


_MASS_TO_TONNES: dict[MassUnit, Decimal] = {
    MassUnit.TONNES: ONE,
    MassUnit.KILOTONNES: Decimal("1000"),
    MassUnit.MEGATONNES: Decimal("1000000"),
}

_VOLUME_TO_M3: dict[VolumeUnit, Decimal] = {
    VolumeUnit.CUBIC_METRES: ONE,
    VolumeUnit.THOUSAND_CUBIC_METRES: Decimal("1000"),
}


def convert_mass(value: Decimal, from_unit: MassUnit, to_unit: MassUnit) -> Decimal:
    if from_unit == to_unit:
        return value
    in_tonnes = value * _MASS_TO_TONNES[from_unit]
    return (in_tonnes / _MASS_TO_TONNES[to_unit]).quantize(PRECISION, rounding=ROUNDING)


def convert_volume(value: Decimal, from_unit: VolumeUnit, to_unit: VolumeUnit) -> Decimal:
    if from_unit == to_unit:
        return value
    in_m3 = value * _VOLUME_TO_M3[from_unit]
    return (in_m3 / _VOLUME_TO_M3[to_unit]).quantize(PRECISION, rounding=ROUNDING)


def unit_conversion(value: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Generic dispatcher that delegates to mass or volume conversion."""
    try:
        return convert_mass(value, MassUnit(from_unit), MassUnit(to_unit))
    except ValueError:
        pass
    try:
        return convert_volume(value, VolumeUnit(from_unit), VolumeUnit(to_unit))
    except ValueError:
        pass
    raise ValueError(f"Cannot convert between {from_unit!r} and {to_unit!r}")


# ---------------------------------------------------------------------------
# Formula registry
# ---------------------------------------------------------------------------

class FormulaSpec(BaseModel):
    formula_id: str
    version: int = 1
    description: str = ""


_FORMULA_SHIFT_TO_DAILY = FormulaSpec(
    formula_id="shift_to_daily_agg",
    version=1,
    description="Sum shift-level values to a daily total",
)

_FORMULA_PERIOD_ROLLUP = FormulaSpec(
    formula_id="period_rollup",
    version=1,
    description="Aggregate child-period totals into a parent period",
)

_FORMULA_STRIPPING_RATIO = FormulaSpec(
    formula_id="stripping_ratio",
    version=1,
    description="OB volume / coal tonnage",
)

_FORMULA_TARGET_VS_ACTUAL = FormulaSpec(
    formula_id="target_vs_actual",
    version=1,
    description="Compare target and actual values",
)

_FORMULA_CUMULATIVE = FormulaSpec(
    formula_id="cumulative_to_date",
    version=1,
    description="Sum values within a date range up to a given date",
)

_FORMULA_RUN_RATE = FormulaSpec(
    formula_id="required_run_rate",
    version=1,
    description="Remaining target / remaining days",
)

_FORMULA_TARGET_CASCADE = FormulaSpec(
    formula_id="target_cascade",
    version=1,
    description="Distribute a parent target to children by weights",
)


# ---------------------------------------------------------------------------
# Pydantic data models
# ---------------------------------------------------------------------------

class ShiftValue(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    shift_number: int
    shift_date: date
    mine_id: str
    bench_id: str | None = None
    production_tonnes: Decimal = ZERO
    ob_volume_m3: Decimal = ZERO
    operating_hours: Decimal = ZERO
    downtime_hours: Decimal = ZERO
    workers_present: int = 0
    remarks: str = ""
    is_resubmission: bool = False
    previous_entry_id: str | None = None


class DailyTotal(BaseModel):
    calc_date: date
    mine_id: str
    bench_id: str | None = None
    total_production_tonnes: Decimal = ZERO
    total_ob_volume_m3: Decimal = ZERO
    total_operating_hours: Decimal = ZERO
    total_downtime_hours: Decimal = ZERO
    shift_count: int = 0
    input_entry_ids: list[str] = Field(default_factory=list)


class PeriodTotal(BaseModel):
    period_label: str
    start_date: date
    end_date: date
    mine_id: str
    total_production_tonnes: Decimal = ZERO
    total_ob_volume_m3: Decimal = ZERO
    child_count: int = 0
    input_ids: list[str] = Field(default_factory=list)


class TargetComparison(BaseModel):
    target: Decimal
    actual: Decimal
    absolute_diff: Decimal
    percentage_diff: Decimal
    achievement_pct: Decimal


class CalcRunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    formula_id: str
    formula_version: int
    input_ids: list[str]
    output_value: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_hash: str


# ---------------------------------------------------------------------------
# Hashing helper — deterministic, reproducible
# ---------------------------------------------------------------------------

def _compute_input_hash(formula_id: str, formula_version: int, input_ids: Sequence[str], values: Sequence[Decimal]) -> str:
    payload = json.dumps(
        {
            "formula": formula_id,
            "version": formula_version,
            "input_ids": sorted(input_ids),
            "values": sorted(str(v) for v in values),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _make_run_record(
    formula: FormulaSpec,
    input_ids: Sequence[str],
    values: Sequence[Decimal],
    output_value: Decimal,
) -> CalcRunRecord:
    return CalcRunRecord(
        formula_id=formula.formula_id,
        formula_version=formula.version,
        input_ids=list(input_ids),
        output_value=str(output_value),
        input_hash=_compute_input_hash(formula.formula_id, formula.version, input_ids, values),
    )


# ---------------------------------------------------------------------------
# Core computation functions
# ---------------------------------------------------------------------------

def aggregate_shifts_to_daily(shift_values: list[ShiftValue]) -> tuple[DailyTotal, CalcRunRecord]:
    """Sum shift-level entries into a single daily total.

    Handles resubmissions: if ``is_resubmission`` is True the entry
    *replaces* (not adds to) any earlier entry for the same shift number
    and bench.
    """
    if not shift_values:
        raise ValueError("Cannot aggregate an empty list of shifts")

    effective: dict[tuple[int, str | None], ShiftValue] = {}
    for sv in shift_values:
        key = (sv.shift_number, sv.bench_id)
        if key in effective and not sv.is_resubmission:
            existing = effective[key]
            if sv.entry_id != existing.entry_id:
                raise ValueError(
                    f"Duplicate shift {sv.shift_number} bench {sv.bench_id} "
                    f"without resubmission flag"
                )
        effective[key] = sv

    vals = list(effective.values())
    total_prod = sum((v.production_tonnes for v in vals), ZERO)
    total_ob = sum((v.ob_volume_m3 for v in vals), ZERO)
    total_op_hrs = sum((v.operating_hours for v in vals), ZERO)
    total_dt_hrs = sum((v.downtime_hours for v in vals), ZERO)
    entry_ids = [v.entry_id for v in vals]

    daily = DailyTotal(
        calc_date=vals[0].shift_date,
        mine_id=vals[0].mine_id,
        bench_id=vals[0].bench_id,
        total_production_tonnes=total_prod.quantize(PRECISION, rounding=ROUNDING),
        total_ob_volume_m3=total_ob.quantize(PRECISION, rounding=ROUNDING),
        total_operating_hours=total_op_hrs.quantize(PRECISION, rounding=ROUNDING),
        total_downtime_hours=total_dt_hrs.quantize(PRECISION, rounding=ROUNDING),
        shift_count=len(vals),
        input_entry_ids=entry_ids,
    )

    run = _make_run_record(
        _FORMULA_SHIFT_TO_DAILY,
        entry_ids,
        [v.production_tonnes for v in vals],
        daily.total_production_tonnes,
    )
    return daily, run


def aggregate_period(
    children: list[PeriodTotal],
    period_label: str,
    start_date: date,
    end_date: date,
    mine_id: str,
) -> tuple[PeriodTotal, CalcRunRecord]:
    """Aggregate child-period totals into a parent-period total."""
    total_prod = sum((c.total_production_tonnes for c in children), ZERO)
    total_ob = sum((c.total_ob_volume_m3 for c in children), ZERO)
    ids = [f"{c.period_label}" for c in children]

    parent = PeriodTotal(
        period_label=period_label,
        start_date=start_date,
        end_date=end_date,
        mine_id=mine_id,
        total_production_tonnes=total_prod.quantize(PRECISION, rounding=ROUNDING),
        total_ob_volume_m3=total_ob.quantize(PRECISION, rounding=ROUNDING),
        child_count=len(children),
        input_ids=ids,
    )

    run = _make_run_record(
        _FORMULA_PERIOD_ROLLUP,
        ids,
        [c.total_production_tonnes for c in children],
        parent.total_production_tonnes,
    )
    return parent, run


def aggregate_daily_to_weekly(
    dailies: list[DailyTotal], week_label: str, start: date, end: date, mine_id: str,
) -> tuple[PeriodTotal, CalcRunRecord]:
    children = [
        PeriodTotal(
            period_label=f"daily_{d.calc_date.isoformat()}",
            start_date=d.calc_date,
            end_date=d.calc_date,
            mine_id=d.mine_id,
            total_production_tonnes=d.total_production_tonnes,
            total_ob_volume_m3=d.total_ob_volume_m3,
            child_count=d.shift_count,
            input_ids=d.input_entry_ids,
        )
        for d in dailies
    ]
    return aggregate_period(children, week_label, start, end, mine_id)


def aggregate_daily_to_monthly(
    dailies: list[DailyTotal], month_label: str, start: date, end: date, mine_id: str,
) -> tuple[PeriodTotal, CalcRunRecord]:
    children = [
        PeriodTotal(
            period_label=f"daily_{d.calc_date.isoformat()}",
            start_date=d.calc_date,
            end_date=d.calc_date,
            mine_id=d.mine_id,
            total_production_tonnes=d.total_production_tonnes,
            total_ob_volume_m3=d.total_ob_volume_m3,
            child_count=d.shift_count,
            input_ids=d.input_entry_ids,
        )
        for d in dailies
    ]
    return aggregate_period(children, month_label, start, end, mine_id)


def aggregate_to_quarterly(
    months: list[PeriodTotal], label: str, start: date, end: date, mine_id: str,
) -> tuple[PeriodTotal, CalcRunRecord]:
    return aggregate_period(months, label, start, end, mine_id)


def aggregate_to_half_yearly(
    quarters: list[PeriodTotal], label: str, start: date, end: date, mine_id: str,
) -> tuple[PeriodTotal, CalcRunRecord]:
    return aggregate_period(quarters, label, start, end, mine_id)


def aggregate_to_yearly(
    halves: list[PeriodTotal], label: str, start: date, end: date, mine_id: str,
) -> tuple[PeriodTotal, CalcRunRecord]:
    return aggregate_period(halves, label, start, end, mine_id)


# ---------------------------------------------------------------------------
# Stripping ratio
# ---------------------------------------------------------------------------

def compute_stripping_ratio(
    ob_volume_m3: Decimal, coal_tonnage: Decimal,
) -> tuple[Decimal, CalcRunRecord]:
    if coal_tonnage == ZERO:
        raise ValueError("Coal tonnage is zero; cannot compute stripping ratio")
    ratio = (ob_volume_m3 / coal_tonnage).quantize(PRECISION, rounding=ROUNDING)
    run = _make_run_record(
        _FORMULA_STRIPPING_RATIO,
        ["ob_volume", "coal_tonnage"],
        [ob_volume_m3, coal_tonnage],
        ratio,
    )
    return ratio, run


# ---------------------------------------------------------------------------
# Target vs actual
# ---------------------------------------------------------------------------

def compute_target_vs_actual(
    target: Decimal, actual: Decimal,
) -> tuple[TargetComparison, CalcRunRecord]:
    absolute_diff = (actual - target).quantize(PRECISION, rounding=ROUNDING)
    if target == ZERO:
        pct_diff = ZERO
        achievement = ZERO if actual == ZERO else Decimal("Infinity")
    else:
        pct_diff = ((actual - target) / target * HUNDRED).quantize(PRECISION, rounding=ROUNDING)
        achievement = (actual / target * HUNDRED).quantize(PRECISION, rounding=ROUNDING)

    comp = TargetComparison(
        target=target,
        actual=actual,
        absolute_diff=absolute_diff,
        percentage_diff=pct_diff,
        achievement_pct=achievement,
    )
    run = _make_run_record(
        _FORMULA_TARGET_VS_ACTUAL,
        ["target", "actual"],
        [target, actual],
        achievement,
    )
    return comp, run


# ---------------------------------------------------------------------------
# Cumulative to date
# ---------------------------------------------------------------------------

class DatedValue(BaseModel):
    value_id: str
    value_date: date
    amount: Decimal


def compute_cumulative_to_date(
    values: list[DatedValue],
    period_start: date,
    period_end: date,
    as_of: date,
) -> tuple[Decimal, CalcRunRecord]:
    cutoff = min(as_of, period_end)
    filtered = [v for v in values if period_start <= v.value_date <= cutoff]
    total = sum((v.amount for v in filtered), ZERO).quantize(PRECISION, rounding=ROUNDING)
    run = _make_run_record(
        _FORMULA_CUMULATIVE,
        [v.value_id for v in filtered],
        [v.amount for v in filtered],
        total,
    )
    return total, run


# ---------------------------------------------------------------------------
# Required run rate
# ---------------------------------------------------------------------------

def compute_required_run_rate(
    remaining_target: Decimal, remaining_days: int,
) -> tuple[Decimal, CalcRunRecord]:
    if remaining_days <= 0:
        raise ValueError("No remaining days to compute run rate")
    rate = (remaining_target / Decimal(remaining_days)).quantize(PRECISION, rounding=ROUNDING)
    run = _make_run_record(
        _FORMULA_RUN_RATE,
        ["remaining_target", "remaining_days"],
        [remaining_target, Decimal(remaining_days)],
        rate,
    )
    return rate, run


# ---------------------------------------------------------------------------
# Target cascade allocation
# ---------------------------------------------------------------------------

def allocate_target_cascade(
    annual_target: Decimal,
    weights: dict[str, Decimal],
) -> tuple[dict[str, Decimal], CalcRunRecord]:
    """Distribute *annual_target* among children proportionally to *weights*.

    The weights are normalised internally so they need not sum to 1.
    Any rounding residual is added to the largest-weight child to ensure
    the children sum to exactly ``annual_target``.
    """
    if not weights:
        raise ValueError("Weights dict is empty")

    total_weight = sum(weights.values(), ZERO)
    if total_weight == ZERO:
        raise ValueError("All weights are zero")

    allocated: dict[str, Decimal] = {}
    running_sum = ZERO
    sorted_keys = sorted(weights.keys(), key=lambda k: weights[k], reverse=True)

    for key in sorted_keys[1:]:
        share = (annual_target * weights[key] / total_weight).quantize(PRECISION, rounding=ROUNDING)
        allocated[key] = share
        running_sum += share

    allocated[sorted_keys[0]] = (annual_target - running_sum).quantize(PRECISION, rounding=ROUNDING)

    run = _make_run_record(
        _FORMULA_TARGET_CASCADE,
        sorted_keys,
        list(weights.values()),
        annual_target,
    )
    return allocated, run
