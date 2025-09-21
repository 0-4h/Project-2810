"""
Tiered (Block) Tariff module (tiered_rate.py)
Only handles tiered pricing. Safe to import from app.py.

Public API:
  - calculate_tiered_bill(consumption_kwh, tier_list, fixed_fee=0.0) -> dict
  - parse_tiers(text) -> List[Tuple[Optional[float], float]]
  - format_breakdown(result, currency_symbol="$") -> str

Tiers format:
  [(100, 0.20), (200, 0.30), (None, 0.40)]
Where None means an unlimited final block.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import json

__all__ = [
    "calculate_tiered_bill",
    "parse_tiers",
    "format_breakdown",
]

# -----------------------------
# Data structures
# -----------------------------
@dataclass
class TierBreakdown:
    tier_index: int
    kwh: float
    rate: float
    cost: float

    def as_dict(self) -> Dict[str, Any]:
        return {"tier": self.tier_index, "kwh": self.kwh, "rate": self.rate, "cost": self.cost}


# -----------------------------
# Validation helpers
# -----------------------------

def _validate_common(consumption_kwh: float, fixed_fee: float) -> None:
    if consumption_kwh < 0:
        raise ValueError("consumption_kwh must be >= 0")
    if fixed_fee < 0:
        raise ValueError("fixed_fee must be >= 0")


def _validate_tier_list(tier_list: List[Tuple[Optional[float], float]]) -> None:
    if not tier_list:
        raise ValueError("tiers must be a non-empty list")
    for i, (block_kwh, rate) in enumerate(tier_list, start=1):
        if rate < 0:
            raise ValueError(f"rate for tier {i} must be >= 0")
        if block_kwh is not None and block_kwh <= 0:
            raise ValueError(f"block_kwh for tier {i} must be > 0 or None for unlimited")
    # Removed: allow all finite tiers; overflow handled after computation
# -----------------------------
# Core computation
# -----------------------------

def calculate_tiered_bill(
    consumption_kwh: float,
    tier_list: List[Tuple[Optional[float], float]],
    fixed_fee: float = 0.0,
) -> Dict[str, Any]:
    """Compute a progressive tiered electricity bill.

    Args:
        consumption_kwh: Total consumption in kWh for the billing period.
        tier_list: List of (block_kwh, rate). Use None for the last tier to denote unlimited remainder.
        fixed_fee: Fixed supply charge for the billing period.

    Returns:
        dict with keys: breakdown (list of dict), energy_cost, fixed_fee, total
    """
    _validate_common(consumption_kwh, fixed_fee)
    _validate_tier_list(tier_list)

    remaining = float(consumption_kwh)
    breakdown: List[TierBreakdown] = []

    for idx, (block_kwh, rate) in enumerate(tier_list, start=1):
        if remaining <= 0:
            break
        block = remaining if block_kwh is None else min(remaining, float(block_kwh))
        cost = block * rate
        breakdown.append(TierBreakdown(tier_index=idx, kwh=block, rate=rate, cost=cost))
        remaining -= block

    if remaining > 1e-9:
        raise ValueError(
            f"Consumption exceeds defined tiers by {remaining:.3f} kWh. Add a final tier with block_kwh=None."
        )

    energy_cost = sum(t.cost for t in breakdown)
    total = energy_cost + fixed_fee

    return {
        "breakdown": [t.as_dict() for t in breakdown],
        "energy_cost": energy_cost,
        "fixed_fee": fixed_fee,
        "total": total,
    }


# -----------------------------
# Parsing and presentation helpers
# -----------------------------

def parse_tiers(text: str) -> List[Tuple[Optional[float], float]]:
    """Parse tiers from JSON or shorthand string."""
    if not text:
        raise ValueError("tiers text is empty")
    t = text.strip()
    if t.startswith("["):
        data = json.loads(t)
        out: List[Tuple[Optional[float], float]] = []
        for pair in data:
            size, rate = pair
            out.append((None if size is None else float(size), float(rate)))
        return out
    # shorthand
    out: List[Tuple[Optional[float], float]] = []
    for part in t.split(','):
        size_s, rate_s = part.strip().split('@')
        size = None if size_s.strip() in {"*", "None", "null"} else float(size_s)
        out.append((size, float(rate_s)))
    return out


def format_currency(value: float, symbol: str = "$") -> str:
    return f"{symbol}{value:,.2f}"


def format_breakdown(result: Dict[str, Any], currency_symbol: str = "$") -> str:
    lines = ["Breakdown:"]
    for item in result.get("breakdown", []):
        tier = item.get("tier", "-")
        kwh = float(item.get("kwh", 0.0))
        rate = float(item.get("rate", 0.0))
        cost = float(item.get("cost", kwh * rate))
        lines.append(
            f"  Tier {tier}: {kwh:.3f} kWh × {format_currency(rate, currency_symbol)} = {format_currency(cost, currency_symbol)}"
        )
    lines.append("")
    lines.append(f"Energy cost = {format_currency(float(result.get('energy_cost', 0.0)), currency_symbol)}")
    lines.append(f"Fixed fee   = {format_currency(float(result.get('fixed_fee', 0.0)), currency_symbol)}")
    lines.append(f"Total bill  = {format_currency(float(result.get('total', 0.0)), currency_symbol)}")
    return "/n".join(lines)


# -----------------------------
# Demonstration
# -----------------------------
if __name__ == "__main__":
    tiers = [(100, 0.20), (200, 0.30), (None, 0.40)]
    r = calculate_tiered_bill(consumption_kwh=350, tier_list=tiers, fixed_fee=10)
    print(format_breakdown(r))
