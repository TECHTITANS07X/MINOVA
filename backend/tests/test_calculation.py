"""Tests for the MINOVA deterministic calculation engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.calculation import (
    CalcRunRecord,
    DatedValue,
    DailyTotal,
    MassUnit,
    PeriodTotal,
    ShiftValue,
    VolumeUnit,
    aggregate_daily_to_monthly,
    aggregate_daily_to_weekly,
    aggregate_period,
    aggregate_shifts_to_daily,
    aggregate_to_quarterly,
    allocate_target_cascade,
    compute_cumulative_to_date,
    compute_required_run_rate,
    compute_stripping_ratio,
    compute_target_vs_actual,
    convert_mass,
    convert_volume,
    unit_conversion,
    ZERO,
    PRECISION,
    ROUNDING,
    _compute_input_hash,
)


# ── Helpers ───────────────────────────────────────────────────────────────

D = Decimal
MINE = "mine-demo-1"
BENCH = "bench-top"
DAY = date(2026, 9, 15)


def _shift(num: int, prod: str, ob: str = "0", **kw) -> ShiftValue:
    return ShiftValue(
        shift_number=num,
        shift_date=DAY,
        mine_id=MINE,
        bench_id=BENCH,
        production_tonnes=D(prod),
        ob_volume_m3=D(ob),
        **kw,
    )


# ── 1.  MANDATORY: 3100 + 2900 + 2000 = 8000 exactly ────────────────────

class TestShiftToDailyAggregation:
    def test_three_shifts_sum_exactly_8000(self):
        shifts = [_shift(1, "3100"), _shift(2, "2900"), _shift(3, "2000")]
        daily, run = aggregate_shifts_to_daily(shifts)

        assert daily.total_production_tonnes == D("8000.0000")
        assert daily.shift_count == 3
        assert len(daily.input_entry_ids) == 3
        assert isinstance(run, CalcRunRecord)

    def test_single_shift(self):
        daily, _ = aggregate_shifts_to_daily([_shift(1, "5000")])
        assert daily.total_production_tonnes == D("5000.0000")
        assert daily.shift_count == 1

    def test_ob_summed(self):
        shifts = [_shift(1, "1000", "2000"), _shift(2, "1500", "3000")]
        daily, _ = aggregate_shifts_to_daily(shifts)
        assert daily.total_ob_volume_m3 == D("5000.0000")

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            aggregate_shifts_to_daily([])


# ── 2.  Partial-shift days ────────────────────────────────────────────────

class TestPartialShiftDay:
    def test_two_of_three_shifts(self):
        """Only two shifts reported — daily should sum just those."""
        shifts = [_shift(1, "3100"), _shift(3, "2000")]
        daily, _ = aggregate_shifts_to_daily(shifts)
        assert daily.total_production_tonnes == D("5100.0000")
        assert daily.shift_count == 2


# ── 3.  Resubmission replaces earlier entry ──────────────────────────────

class TestResubmission:
    def test_resubmission_replaces(self):
        original = _shift(2, "2900")
        corrected = _shift(
            2, "2850",
            is_resubmission=True,
            previous_entry_id=original.entry_id,
        )
        shifts = [_shift(1, "3100"), original, corrected, _shift(3, "2000")]
        daily, _ = aggregate_shifts_to_daily(shifts)

        # 3100 + 2850 (replaced) + 2000 = 7950
        assert daily.total_production_tonnes == D("7950.0000")
        assert daily.shift_count == 3

    def test_duplicate_without_flag_raises(self):
        s1 = _shift(2, "2900")
        s2 = _shift(2, "2800")  # same shift, different entry, no flag
        with pytest.raises(ValueError, match="Duplicate shift"):
            aggregate_shifts_to_daily([s1, s2])


# ── 4.  Rounding rules ───────────────────────────────────────────────────

class TestRounding:
    def test_bankers_rounding_half_even(self):
        """Decimal('0.00005') should round to '0.0000' (ROUND_HALF_EVEN)."""
        val = D("0.00005")
        assert val.quantize(PRECISION, rounding=ROUNDING) == D("0.0000")

        val2 = D("0.00015")
        assert val2.quantize(PRECISION, rounding=ROUNDING) == D("0.0002")

    def test_shift_sum_precision(self):
        shifts = [_shift(1, "1000.1234"), _shift(2, "2000.5678")]
        daily, _ = aggregate_shifts_to_daily(shifts)
        assert daily.total_production_tonnes == D("3000.6912")


# ── 5.  Unit conversion ──────────────────────────────────────────────────

class TestUnitConversion:
    def test_tonnes_to_kilotonnes(self):
        assert convert_mass(D("8000"), MassUnit.TONNES, MassUnit.KILOTONNES) == D("8.0000")

    def test_kilotonnes_to_megatonnes(self):
        assert convert_mass(D("2500"), MassUnit.KILOTONNES, MassUnit.MEGATONNES) == D("2.5000")

    def test_megatonnes_to_tonnes(self):
        assert convert_mass(D("1.5"), MassUnit.MEGATONNES, MassUnit.TONNES) == D("1500000.0000")

    def test_same_unit_noop(self):
        assert convert_mass(D("42"), MassUnit.TONNES, MassUnit.TONNES) == D("42")

    def test_volume_m3_to_km3(self):
        assert convert_volume(D("5000"), VolumeUnit.CUBIC_METRES, VolumeUnit.THOUSAND_CUBIC_METRES) == D("5.0000")

    def test_generic_dispatcher(self):
        assert unit_conversion(D("8000"), "t", "kt") == D("8.0000")
        assert unit_conversion(D("5000"), "m3", "km3") == D("5.0000")

    def test_invalid_conversion(self):
        with pytest.raises(ValueError, match="Cannot convert"):
            unit_conversion(D("1"), "t", "m3")


# ── 6.  Stripping ratio ──────────────────────────────────────────────────

class TestStrippingRatio:
    def test_basic_ratio(self):
        ratio, run = compute_stripping_ratio(D("32000"), D("8000"))
        assert ratio == D("4.0000")

    def test_zero_coal_raises(self):
        with pytest.raises(ValueError, match="zero"):
            compute_stripping_ratio(D("10000"), ZERO)

    def test_fractional_ratio(self):
        ratio, _ = compute_stripping_ratio(D("10000"), D("3000"))
        assert ratio == D("3.3333")


# ── 7.  Target vs actual ─────────────────────────────────────────────────

class TestTargetVsActual:
    def test_on_target(self):
        comp, _ = compute_target_vs_actual(D("8000"), D("8000"))
        assert comp.achievement_pct == D("100.0000")
        assert comp.absolute_diff == ZERO

    def test_under_target(self):
        comp, _ = compute_target_vs_actual(D("10000"), D("8000"))
        assert comp.achievement_pct == D("80.0000")
        assert comp.absolute_diff == D("-2000.0000")
        assert comp.percentage_diff == D("-20.0000")

    def test_over_target(self):
        comp, _ = compute_target_vs_actual(D("8000"), D("9000"))
        assert comp.achievement_pct == D("112.5000")


# ── 8.  Cumulative to date ───────────────────────────────────────────────

class TestCumulativeToDate:
    def test_partial_month(self):
        values = [
            DatedValue(value_id="d1", value_date=date(2026, 9, 1), amount=D("1000")),
            DatedValue(value_id="d2", value_date=date(2026, 9, 5), amount=D("2000")),
            DatedValue(value_id="d3", value_date=date(2026, 9, 10), amount=D("1500")),
            DatedValue(value_id="d4", value_date=date(2026, 9, 20), amount=D("3000")),
        ]
        total, _ = compute_cumulative_to_date(
            values,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
            as_of=date(2026, 9, 10),
        )
        assert total == D("4500.0000")

    def test_full_period(self):
        values = [
            DatedValue(value_id="d1", value_date=date(2026, 9, 1), amount=D("1000")),
            DatedValue(value_id="d2", value_date=date(2026, 9, 30), amount=D("2000")),
        ]
        total, _ = compute_cumulative_to_date(
            values, date(2026, 9, 1), date(2026, 9, 30), date(2026, 10, 5),
        )
        assert total == D("3000.0000")


# ── 9.  Required run rate ────────────────────────────────────────────────

class TestRunRate:
    def test_basic(self):
        rate, _ = compute_required_run_rate(D("10000"), 10)
        assert rate == D("1000.0000")

    def test_zero_days_raises(self):
        with pytest.raises(ValueError, match="No remaining days"):
            compute_required_run_rate(D("5000"), 0)


# ── 10. Target cascade allocation ────────────────────────────────────────

class TestTargetCascade:
    def test_equal_weights(self):
        weights = {"Q1": D("1"), "Q2": D("1"), "Q3": D("1"), "Q4": D("1")}
        alloc, _ = allocate_target_cascade(D("12000"), weights)
        assert sum(alloc.values()) == D("12000.0000")
        for v in alloc.values():
            assert v == D("3000.0000")

    def test_unequal_weights_sum_preserved(self):
        weights = {"Q1": D("3"), "Q2": D("3"), "Q3": D("2"), "Q4": D("2")}
        alloc, _ = allocate_target_cascade(D("15000"), weights)
        # Must sum exactly to annual target
        assert sum(alloc.values()) == D("15000.0000")
        assert alloc["Q1"] >= alloc["Q3"]

    def test_rounding_residual_assigned_to_largest(self):
        # 10000 / 3 doesn't divide evenly
        weights = {"A": D("1"), "B": D("1"), "C": D("1")}
        alloc, _ = allocate_target_cascade(D("10000"), weights)
        assert sum(alloc.values()) == D("10000.0000")

    def test_empty_weights_raises(self):
        with pytest.raises(ValueError, match="empty"):
            allocate_target_cascade(D("10000"), {})


# ── 11. Reproducibility / deterministic hashing ─────────────────────────

class TestReproducibility:
    def test_same_inputs_same_hash(self):
        shifts = [_shift(1, "3100"), _shift(2, "2900"), _shift(3, "2000")]
        _, run1 = aggregate_shifts_to_daily(shifts)
        _, run2 = aggregate_shifts_to_daily(shifts)
        assert run1.input_hash == run2.input_hash

    def test_different_order_same_hash(self):
        """Input order doesn't change the hash (sorted internally)."""
        h1 = _compute_input_hash("f", 1, ["a", "b", "c"], [D("1"), D("2"), D("3")])
        h2 = _compute_input_hash("f", 1, ["c", "a", "b"], [D("3"), D("1"), D("2")])
        assert h1 == h2

    def test_different_values_different_hash(self):
        h1 = _compute_input_hash("f", 1, ["a"], [D("100")])
        h2 = _compute_input_hash("f", 1, ["a"], [D("200")])
        assert h1 != h2


# ── 12. Period cascading rollups ─────────────────────────────────────────

class TestPeriodCascade:
    def _daily(self, d: date, prod: str) -> DailyTotal:
        return DailyTotal(
            calc_date=d,
            mine_id=MINE,
            total_production_tonnes=D(prod),
            input_entry_ids=[f"e-{d.isoformat()}"],
        )

    def test_daily_to_weekly(self):
        dailies = [self._daily(date(2026, 9, i), str(1000 + i * 100)) for i in range(1, 8)]
        weekly, run = aggregate_daily_to_weekly(
            dailies, "W-2026-36", date(2026, 9, 1), date(2026, 9, 7), MINE,
        )
        expected = sum(D(str(1000 + i * 100)) for i in range(1, 8))
        assert weekly.total_production_tonnes == expected.quantize(PRECISION, rounding=ROUNDING)
        assert weekly.child_count == 7

    def test_daily_to_monthly(self):
        dailies = [self._daily(date(2026, 9, d), "500") for d in range(1, 31)]
        monthly, _ = aggregate_daily_to_monthly(
            dailies, "2026-09", date(2026, 9, 1), date(2026, 9, 30), MINE,
        )
        assert monthly.total_production_tonnes == D("15000.0000")

    def test_monthly_to_quarterly(self):
        months = [
            PeriodTotal(period_label=f"2026-0{m}", start_date=date(2026, m, 1),
                        end_date=date(2026, m, 28), mine_id=MINE,
                        total_production_tonnes=D("50000"))
            for m in [7, 8, 9]
        ]
        quarterly, _ = aggregate_to_quarterly(
            months, "Q3-2026", date(2026, 7, 1), date(2026, 9, 30), MINE,
        )
        assert quarterly.total_production_tonnes == D("150000.0000")
