"""One resource-name taxonomy shared by all GenX result visualizations.

GenX result labels are not always canonical technology names: names can contain
technology tokens such as combined_cycle, combustion_turbine, _DR, hydroelectric,
distributed_generation or fuel terminology. Keep the mapping here so capacity
plots and time-of-day generation plots cannot silently report different totals.
"""

from __future__ import annotations

import re

# Keys are stable snake_case identifiers used by data-processing functions.
# Labels are shared with palette.py and user-facing chart legends.
RESOURCE_LABELS: dict[str, str] = {
    "coal": "Coal",
    "natural_gas": "Natural Gas",
    "solar": "Solar",
    "wind": "Wind",
    "battery": "Battery",
    "hydro": "Hydro",
    "nuclear": "Nuclear",
    "biomass": "Biomass",
    "other": "Other",
    "dr": "DR",
}


def classify_resource(resource: object) -> str:
    """Map a GenX resource name to a stable shared technology key.

    Order matters: subtotal rows are ignored, demand-response resources are
    distinguished before fuel names, and specific technologies precede broad
    fallback matches.
    """
    name = str(resource or "").strip().lower()
    normalized = re.sub(r"[\s\-]+", "_", name)

    if normalized in {"", "total", "annualsum", "zone"}:
        return "ignore"

    if normalized.endswith("_dr") or "_dr_" in normalized or normalized == "dr":
        return "dr"

    if "batt" in normalized or "storage" in normalized:
        return "battery"

    if "hydroelectric" in normalized or "hydropower" in normalized or "hydro" in normalized:
        return "hydro"

    if "nuclear" in normalized:
        return "nuclear"

    if "coal" in normalized:
        return "coal"

    if "natural_gas" in normalized or "naturalgas" in normalized or "gas" in normalized:
        return "natural_gas"

    if "petroleum" in normalized or re.search(r"(^|_)oil($|_)", normalized):
        return "natural_gas"

    if "biomass" in normalized or "biogas" in normalized:
        return "biomass"

    if "wind" in normalized:
        return "wind"

    if (
        "solar" in normalized
        or "photovoltaic" in normalized
        or "utilitypv" in normalized
        or re.search(r"(^|_)pv($|_)", normalized)
    ):
        return "solar"

    if (
        "combined_cycle" in normalized
        or "combustion_turbine" in normalized
        or normalized.endswith("_cc_new")
        or normalized.endswith("_ct_new")
    ):
        return "natural_gas"

    return "other"
