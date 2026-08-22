#!/usr/bin/env python3
"""Deterministic QIK-VRT carrier-cost and transport-envelope calculator.

The calculator deliberately separates carrier size, Shannon information,
Landauer lower bounds, measured energy, operational cost, replacement cost,
and market/IP value.  It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation, getcontext
from typing import Iterable

getcontext().prec = 60

BOLTZMANN_J_PER_K = Decimal("1.380649e-23")  # exact in the SI
LN2 = Decimal("0.693147180559945309417232121458176568075500134360255254120")
JOULES_PER_KWH = Decimal("3600000")
BYTES_PER_GIB = Decimal(1024) ** 3
SECONDS_PER_MINUTE = Decimal(60)


class InputError(ValueError):
    """Raised when a requested calculation would violate the fail-closed contract."""


def _decimal(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InputError(f"{name} must be a finite decimal") from exc
    if not result.is_finite():
        raise InputError(f"{name} must be finite")
    return result


def _nonnegative(value: object, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise InputError(f"{name} must be non-negative")
    return result


def _positive(value: object, name: str) -> Decimal:
    result = _decimal(value, name)
    if result <= 0:
        raise InputError(f"{name} must be positive")
    return result


def carrier_bits(byte_count: int) -> int:
    if isinstance(byte_count, bool) or not isinstance(byte_count, int):
        raise InputError("byte_count must be an integer")
    if byte_count < 0:
        raise InputError("byte_count must be non-negative")
    return byte_count * 8


def landauer_minimum_joules(
    bit_count: int,
    temperature_kelvin: object,
    irreversible_operations_per_bit: object = 1,
) -> Decimal:
    """Return k_B*T*ln(2) times the requested irreversible operation count.

    This is a thermodynamic lower bound for logically irreversible operations,
    not a measurement of practical evidence creation, storage, or transmission.
    """
    if isinstance(bit_count, bool) or not isinstance(bit_count, int):
        raise InputError("bit_count must be an integer")
    if bit_count < 0:
        raise InputError("bit_count must be non-negative")
    temperature = _positive(temperature_kelvin, "temperature_kelvin")
    operations = _nonnegative(
        irreversible_operations_per_bit, "irreversible_operations_per_bit"
    )
    return Decimal(bit_count) * BOLTZMANN_J_PER_K * temperature * LN2 * operations


def ideal_transfer_seconds(
    byte_count: int,
    width_bits: int,
    clock_hz: object,
    utilization: object = 1,
) -> Decimal:
    """Idealized lower-envelope transfer time, not a CPU or bus benchmark."""
    bits = carrier_bits(byte_count)
    if isinstance(width_bits, bool) or not isinstance(width_bits, int):
        raise InputError("width_bits must be an integer")
    if width_bits <= 0:
        raise InputError("width_bits must be positive")
    clock = _positive(clock_hz, "clock_hz")
    eta = _positive(utilization, "utilization")
    if eta > 1:
        raise InputError("utilization must be <= 1")
    return Decimal(bits) / (Decimal(width_bits) * clock * eta)


def bandwidth_transfer_seconds(byte_count: int, bytes_per_second: object) -> Decimal:
    carrier_bits(byte_count)
    throughput = _positive(bytes_per_second, "bytes_per_second")
    return Decimal(byte_count) / throughput


def storage_list_price_usd(
    byte_count: int,
    price_usd_per_gib_month: object,
    months: object,
    replicas: int = 1,
) -> Decimal:
    carrier_bits(byte_count)
    price = _nonnegative(price_usd_per_gib_month, "price_usd_per_gib_month")
    duration = _nonnegative(months, "months")
    if isinstance(replicas, bool) or not isinstance(replicas, int):
        raise InputError("replicas must be an integer")
    if replicas < 0:
        raise InputError("replicas must be non-negative")
    gib = Decimal(byte_count) / BYTES_PER_GIB
    return gib * price * duration * Decimal(replicas)


def runner_list_price_usd(
    duration_seconds: object, price_usd_per_minute: object
) -> Decimal:
    seconds = _nonnegative(duration_seconds, "duration_seconds")
    rate = _nonnegative(price_usd_per_minute, "price_usd_per_minute")
    return (seconds / SECONDS_PER_MINUTE) * rate


def replacement_cost(
    labour_hours: object,
    labour_rate_per_hour: object,
    direct_costs: object = 0,
) -> Decimal:
    hours = _nonnegative(labour_hours, "labour_hours")
    rate = _nonnegative(labour_rate_per_hour, "labour_rate_per_hour")
    direct = _nonnegative(direct_costs, "direct_costs")
    return hours * rate + direct


def _fmt(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "E")


def build_receipt(
    *,
    source_label: str,
    byte_count: int,
    temperature_kelvin: object,
    irreversible_operations_per_bit: object,
    electricity_eur_per_kwh: object,
    widths: Iterable[int],
    clock_hz: object | None,
    utilization: object,
    bandwidths_gb_s: Iterable[object],
    storage_price_usd_per_gib_month: object,
    storage_months: object,
    storage_replicas: int,
    runner_seconds: object,
    runner_price_usd_per_minute: object,
) -> dict[str, object]:
    if not source_label or not source_label.strip():
        raise InputError("source_label must be non-empty")

    bits = carrier_bits(byte_count)
    temperature = _positive(temperature_kelvin, "temperature_kelvin")
    irreversible = _nonnegative(
        irreversible_operations_per_bit, "irreversible_operations_per_bit"
    )
    energy_j = landauer_minimum_joules(bits, temperature, irreversible)
    energy_kwh = energy_j / JOULES_PER_KWH
    electricity_rate = _nonnegative(
        electricity_eur_per_kwh, "electricity_eur_per_kwh"
    )

    transfer_envelopes: list[dict[str, str | int]] = []
    if clock_hz is not None:
        clock = _positive(clock_hz, "clock_hz")
        eta = _positive(utilization, "utilization")
        if eta > 1:
            raise InputError("utilization must be <= 1")
        for width in widths:
            seconds = ideal_transfer_seconds(byte_count, width, clock, eta)
            transfer_envelopes.append(
                {
                    "width_bits": width,
                    "clock_hz": _fmt(clock),
                    "utilization": _fmt(eta),
                    "ideal_lower_envelope_seconds": _fmt(seconds),
                }
            )

    bandwidth_envelopes: list[dict[str, str]] = []
    for gb_s_value in bandwidths_gb_s:
        gb_s = _positive(gb_s_value, "bandwidth_gb_s")
        bytes_per_second = gb_s * Decimal(1_000_000_000)
        bandwidth_envelopes.append(
            {
                "decimal_gb_per_second": _fmt(gb_s),
                "ideal_carrier_time_seconds": _fmt(
                    bandwidth_transfer_seconds(byte_count, bytes_per_second)
                ),
            }
        )

    storage_cost = storage_list_price_usd(
        byte_count,
        storage_price_usd_per_gib_month,
        storage_months,
        storage_replicas,
    )
    runner_cost = runner_list_price_usd(
        runner_seconds, runner_price_usd_per_minute
    )

    return {
        "schema": "qikvrt_evidence_bandwidth_cost_receipt_v1",
        "source_label": source_label.strip(),
        "carrier": {
            "bytes": byte_count,
            "bits": bits,
            "gib": _fmt(Decimal(byte_count) / BYTES_PER_GIB),
            "semantic_information_measured": False,
        },
        "thermodynamic_lower_bound": {
            "temperature_kelvin": _fmt(temperature),
            "boltzmann_j_per_kelvin_exact": str(BOLTZMANN_J_PER_K),
            "ln_2_decimal": str(LN2),
            "irreversible_operations_per_carrier_bit": _fmt(irreversible),
            "joules": _fmt(energy_j),
            "kilowatt_hours": _fmt(energy_kwh),
            "electricity_rate_eur_per_kwh_scenario": _fmt(electricity_rate),
            "electricity_cost_eur_scenario": _fmt(energy_kwh * electricity_rate),
            "interpretation": (
                "LOWER_BOUND_FOR_SPECIFIED_LOGICALLY_IRREVERSIBLE_OPERATIONS_"
                "NOT_MEASURED_EVIDENCE_CREATION_ENERGY"
            ),
            "actual_energy_measured": False,
        },
        "transport_envelopes": transfer_envelopes,
        "bandwidth_envelopes": bandwidth_envelopes,
        "operational_scenarios": {
            "storage": {
                "price_usd_per_gib_month": _fmt(
                    _nonnegative(
                        storage_price_usd_per_gib_month,
                        "storage_price_usd_per_gib_month",
                    )
                ),
                "months": _fmt(_nonnegative(storage_months, "storage_months")),
                "replicas": storage_replicas,
                "list_price_usd": _fmt(storage_cost),
            },
            "runner": {
                "duration_seconds": _fmt(
                    _nonnegative(runner_seconds, "runner_seconds")
                ),
                "price_usd_per_minute": _fmt(
                    _nonnegative(
                        runner_price_usd_per_minute,
                        "runner_price_usd_per_minute",
                    )
                ),
                "fractional_list_price_usd": _fmt(runner_cost),
                "actual_invoice_measured": False,
            },
        },
        "boundaries": {
            "carrier_bytes_not_shannon_information": True,
            "landauer_lower_bound_not_actual_energy": True,
            "carrier_cost_not_reproduction_cost": True,
            "reproduction_cost_not_market_value": True,
            "ideal_width_scaling_not_measured_speedup": True,
            "repository_evidence_not_physical_law": True,
            "market_value_determined": False,
            "market_value_disposition": (
                "HOLD_UNTIL_COST_LEDGER_RIGHTS_PROVENANCE_INDEPENDENT_BENCHMARK_"
                "AND_DEMAND_EVIDENCE"
            ),
        },
    }


def _parse_widths(raw: str) -> list[int]:
    values: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError as exc:
            raise InputError("widths must be comma-separated positive integers") from exc
        if value <= 0:
            raise InputError("widths must be positive")
        values.append(value)
    if not values:
        raise InputError("at least one width is required")
    return values


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bytes", dest="byte_count", required=True, type=int)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--temperature-k", default="300")
    parser.add_argument("--irreversible-ops-per-bit", default="1")
    parser.add_argument("--electricity-eur-per-kwh", default="0.1837")
    parser.add_argument("--clock-hz")
    parser.add_argument("--widths", default="8,16,32,64,128,256")
    parser.add_argument("--utilization", default="1")
    parser.add_argument(
        "--bandwidth-gb-s",
        action="append",
        default=[],
        help="repeatable decimal GB/s carrier-envelope scenario",
    )
    parser.add_argument("--storage-price-usd-per-gib-month", default="0.023")
    parser.add_argument("--storage-months", default="12")
    parser.add_argument("--storage-replicas", type=int, default=1)
    parser.add_argument("--runner-seconds", default="0")
    parser.add_argument("--runner-price-usd-per-minute", default="0.006")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        receipt = build_receipt(
            source_label=args.source_label,
            byte_count=args.byte_count,
            temperature_kelvin=args.temperature_k,
            irreversible_operations_per_bit=args.irreversible_ops_per_bit,
            electricity_eur_per_kwh=args.electricity_eur_per_kwh,
            widths=_parse_widths(args.widths),
            clock_hz=args.clock_hz,
            utilization=args.utilization,
            bandwidths_gb_s=args.bandwidth_gb_s,
            storage_price_usd_per_gib_month=args.storage_price_usd_per_gib_month,
            storage_months=args.storage_months,
            storage_replicas=args.storage_replicas,
            runner_seconds=args.runner_seconds,
            runner_price_usd_per_minute=args.runner_price_usd_per_minute,
        )
    except InputError as exc:
        raise SystemExit(f"HOLD: {exc}") from exc

    rendered = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
