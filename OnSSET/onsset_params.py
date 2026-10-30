"""Scenario parameter schema for the OnSSET engine.

Defaults come from the OnSSET scenario notebook (``2. OnSSET_Scenarios.ipynb``) and the
fixed values in ``detailed_tech_parameters.ipynb``. Each field carries a unit and a group
in its JSON schema so MCP clients can present and validate scenarios without the notebook.
"""

from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def P(default, unit, group, description, **constraints):
    """Field with the unit and group exposed in the JSON schema."""
    return Field(default, description=description, json_schema_extra={"unit": unit, "group": group},
                 **constraints)


def R(unit, group, description, **constraints):
    """Required field (no cross-country default)."""
    return P(..., unit, group, description, **constraints)


class ScenarioParams(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # --- Modelling period and electrification targets
    start_year: int = R("year", "horizon", "Base year of the analysis; must equal the calibration year of the input CSV.",
                        ge=2000, le=2100)
    end_year: int = R("year", "horizon", "Final year of the analysis.", ge=2000, le=2100)
    end_electrification_rate_target: float = P(
        1.0, "share", "horizon", "Share of the population electrified in end_year (1 = universal access).", gt=0, le=1)
    intermediate_targets: Dict[int, float] = P(
        {}, "{year: share}", "horizon",
        "Optional intermediate time steps as {year: electrification share}, years strictly between start_year and "
        "end_year. Each year adds a model time step.")

    # --- Demographics
    end_year_pop: float = R("people", "demographics", "Projected national population in end_year.", gt=0)
    urban_ratio_end_year: float = R("share", "demographics", "Urban share of the population in end_year.", ge=0, le=1)
    num_people_per_hh_urban: float = P(5, "people/household", "demographics", "Household size in urban settlements.",
                                       gt=0, le=20)
    num_people_per_hh_rural: float = P(5, "people/household", "demographics", "Household size in rural settlements.",
                                       gt=0, le=20)

    # --- Residential demand
    tier_1: float = P(20, "kWh/household/year", "demand", "Annual household consumption at MTF tier 1.", gt=0)
    tier_2: float = P(73, "kWh/household/year", "demand", "Annual household consumption at MTF tier 2.", gt=0)
    tier_3: float = P(365, "kWh/household/year", "demand", "Annual household consumption at MTF tier 3.", gt=0)
    tier_4: float = P(1241, "kWh/household/year", "demand", "Annual household consumption at MTF tier 4.", gt=0)
    tier_5: float = P(3000, "kWh/household/year", "demand", "Annual household consumption at MTF tier 5.", gt=0)
    urban_target_tier: int = P(
        4, "tier", "demand",
        "Target tier (1-5) for urban settlements, or 6 for the settlement-specific poverty/GDP based tier "
        "(needs the ResidentialDemandTierCustom column in the input).", ge=1, le=6)
    rural_target_tier_large: int = P(3, "tier", "demand", "Target tier (1-6) for large rural settlements.", ge=1, le=6)
    rural_target_tier_small: int = P(1, "tier", "demand", "Target tier (1-6) for small rural settlements.", ge=1, le=6)
    rural_cutoff_size: float = P(100, "households", "demand",
                                 "Rural settlements with fewer households are 'small rural'.", ge=0)

    # --- Central grid: generation and limits
    grid_generation_cost: float = P(0.10, "USD/kWh", "grid", "Grid electricity generation cost in end_year.", ge=0)
    grid_power_plants_capital_cost: float = P(2500, "USD/kW", "grid", "Capital cost of new grid generation capacity.",
                                              ge=0)
    grid_losses: float = P(0.15, "share", "grid", "Transmission and distribution losses.", ge=0, lt=1)
    grid_emission_factor: float = P(745, "gCO2/kWh", "grid", "Average emission factor of grid generation.", ge=0)
    annual_new_grid_connections_limit: float = P(999999999, "households/year", "grid",
                                                 "Maximum new grid connections per year.", gt=0)
    annual_grid_cap_gen_limit: float = P(9999999, "MW/year", "grid", "Maximum grid generation capacity added per year.",
                                         gt=0)
    grid_reliability_option: Literal["None", "CNSE"] = P(
        "None", "-", "grid", "'CNSE' adds the cost of non-served energy to grid-connected settlements.")
    cnse: float = P(0.0, "USD/kWh", "grid", "Cost of non-served energy, used when grid_reliability_option='CNSE'.", ge=0)
    grid_reliability: float = P(1.0, "share", "grid", "Share of annual load the grid can meet.", gt=0, le=1)

    # --- Central grid: network
    hv_line_capacity: float = P(161, "kV", "grid_network", "HV line voltage.", gt=0)
    hv_line_cost: float = P(106000, "USD/km", "grid_network", "HV line cost.", ge=0)
    hv_mv_transformer_type: float = P(16000, "kVA", "grid_network", "HV/MV substation transformer rating.", gt=0)
    hv_mv_transformer_cost: float = P(980000, "USD/unit", "grid_network", "HV/MV substation transformer cost.", ge=0)
    grid_mv_line_capacity: float = P(33, "kV", "grid_network", "MV line voltage.", gt=0)
    grid_mv_line_cost: float = P(20000, "USD/km", "grid_network", "MV line cost.", ge=0)
    grid_mv_line_max_length: float = P(100, "km", "grid_network", "Maximum length of a single MV grid extension.", gt=0)
    grid_MV_line_amperage_limit: float = P(275, "A", "grid_network", "MV line ampacity.", gt=0)
    grid_lv_line_capacity: float = P(0.4, "kV", "grid_network", "LV line voltage.", gt=0)
    grid_lv_line_max_length: float = P(1, "km", "grid_network", "Maximum LV line length.", gt=0)
    grid_lv_line_cost: float = P(15000, "USD/km", "grid_network", "LV line cost.", ge=0)
    grid_service_Transf_type: float = P(75, "kVA", "grid_network", "MV/LV service transformer rating.", gt=0)
    grid_service_Transf_cost: float = P(9000, "USD/unit", "grid_network", "MV/LV service transformer cost.", ge=0)
    grid_max_nodes_per_serv_trans: int = P(95, "nodes", "grid_network",
                                           "Maximum households served by one service transformer.", gt=0)

    # --- Off-grid general
    min_mg_size: float = P(100, "households", "off_grid",
                           "Minimum settlement size for mini-grids to be considered.", ge=0)
    mg_min_grid_dist: float = P(0, "km", "off_grid",
                                "Minimum distance from existing MV lines for mini-grids to be considered.", ge=0)
    mg_interconnection: Literal[0, 1] = P(1, "-", "off_grid",
                                          "1 = mini-grids may be connected to the grid in a later time step.")
    diesel_price: float = P(1.43, "USD/l", "off_grid", "Diesel price in end_year.", ge=0)

    # --- Hybrid mini-grids
    pv_cost: float = P(1400, "USD/kW", "mini_grid", "Mini-grid PV capital cost incl. BoS (PV inverter, charge "
                                                    "controller).", ge=0)
    wind_cost: float = P(2500, "USD/kW", "mini_grid", "Mini-grid wind turbine capital cost.", ge=0)
    battery_cost: float = P(550, "USD/kWh", "mini_grid", "Mini-grid battery capital cost per kWh of storage.", ge=0)
    inverter_cost: float = P(598, "USD/kW", "mini_grid", "Mini-grid battery inverter cost.", ge=0)
    diesel_gen_cost: float = P(500, "USD/kW", "mini_grid", "Mini-grid diesel generator capital cost.", ge=0)
    pv_life: int = P(25, "years", "mini_grid", "Mini-grid PV lifetime.", ge=1)
    inverter_life: int = P(8, "years", "mini_grid", "Mini-grid battery inverter lifetime.", ge=1)
    diesel_life: int = P(10, "years", "mini_grid", "Mini-grid diesel generator lifetime.", ge=1)
    lpsp_max: float = P(0.02, "share", "mini_grid", "Maximum loss of power supply probability (unmet share of annual "
                                                    "kWh).", ge=0, lt=1)
    max_diesel: float = P(0.0, "share", "mini_grid", "Maximum share of PV hybrid mini-grid generation from diesel "
                                                     "(0 = fully renewable).", ge=0, le=1)
    mg_hydro_capital_cost: float = P(15000, "USD/kW", "mini_grid", "Mini-grid hydro capital cost.", ge=0)

    # --- Mini-grid distribution network
    mg_mv_line_capacity: float = P(33, "kV", "mini_grid_network", "Mini-grid MV line voltage.", gt=0)
    mg_mv_line_cost: float = P(25000, "USD/km", "mini_grid_network", "Mini-grid MV line cost.", ge=0)
    mg_MV_line_amperage_limit: float = P(275, "A", "mini_grid_network", "Mini-grid MV line ampacity.", gt=0)
    mg_lv_line_capacity: float = P(0.4, "kV", "mini_grid_network", "Mini-grid LV line voltage.", gt=0)
    mg_lv_line_max_length: float = P(1, "km", "mini_grid_network", "Mini-grid maximum LV line length.", gt=0)
    mg_lv_line_cost: float = P(15000, "USD/km", "mini_grid_network", "Mini-grid LV line cost.", ge=0)
    mg_service_Transf_type: float = P(75, "kVA", "mini_grid_network", "Mini-grid service transformer rating.", gt=0)
    mg_service_Transf_cost: float = P(9000, "USD/unit", "mini_grid_network", "Mini-grid service transformer cost.",
                                      ge=0)
    mg_max_nodes_per_serv_trans: int = P(95, "nodes", "mini_grid_network",
                                         "Maximum households served by one mini-grid service transformer.", gt=0)

    # --- Stand-alone PV
    sa_pv_capital_cost_1: float = P(11600, "USD/kW", "stand_alone", "Solar home system cost, systems up to 20 W.", gt=0)
    sa_pv_capital_cost_2: float = P(7500, "USD/kW", "stand_alone", "Solar home system cost, 20-50 W.", gt=0)
    sa_pv_capital_cost_3: float = P(7500, "USD/kW", "stand_alone", "Solar home system cost, 50-100 W.", gt=0)
    sa_pv_capital_cost_4: float = P(8000, "USD/kW", "stand_alone", "Solar home system cost, 100 W-1 kW.", gt=0)
    sa_pv_capital_cost_5: float = P(8000, "USD/kW", "stand_alone", "Solar home system cost, above 1 kW.", gt=0)
    shs_lifetime: int = P(5, "years", "stand_alone", "Solar home system lifetime.", ge=1)

    # --- Finance
    grid_discount_rate: float = P(0.12, "share", "finance", "Discount rate for grid investments.", ge=0, lt=1)
    mini_grid_discount_rate: float = P(0.12, "share", "finance", "Discount rate for mini-grid investments.", ge=0, lt=1)
    standalone_discount_rate: float = P(0.12, "share", "finance", "Discount rate for stand-alone systems.", ge=0, lt=1)

    # --- Rollout
    auto_intensification: float = P(0, "km", "rollout",
                                    "Buffer around planned MV lines where settlements are forced onto the grid "
                                    "(0 = pure least cost).", ge=0)
    max_grid_intensification_cost: float = P(1500, "USD/household", "rollout",
                                             "Maximum cost per household for forced grid intensification.", ge=0)
    prio_choice: Literal[1, 2, 3, 4, 5] = P(
        1, "-", "rollout",
        "Settlement priority when a target is below 100%: 1 closest to roads, 2 shortest travel time, 3 largest "
        "first, 4 lowest investment per connection, 5 smallest first.")

    @model_validator(mode="after")
    def _check_consistency(self):
        if self.end_year <= self.start_year:
            raise ValueError("end_year must be after start_year")
        previous = 0.0
        for year in sorted(self.intermediate_targets):
            rate = self.intermediate_targets[year]
            if not self.start_year < year < self.end_year:
                raise ValueError(f"intermediate_targets year {year} must lie strictly between start_year and end_year")
            if not 0 < rate <= 1:
                raise ValueError(f"intermediate_targets rate for {year} must be in (0, 1]")
            if rate < previous:
                raise ValueError("intermediate_targets rates must not decrease over time")
            previous = rate
        if self.end_electrification_rate_target < previous:
            raise ValueError("end_electrification_rate_target must not be below the intermediate targets")
        tiers = [self.tier_1, self.tier_2, self.tier_3, self.tier_4, self.tier_5]
        if tiers != sorted(tiers) or len(set(tiers)) < 5:
            raise ValueError("tier_1 ... tier_5 must be strictly increasing")
        return self


class CalibrationParams(BaseModel):
    """Inputs of ``1. OnSSET_Calibration.ipynb``; defaults are the notebook's cells 14-15."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # --- Base-year statistics
    start_year: int = R("year", "statistics", "Base year of the analysis; becomes the scenario start_year.",
                        ge=2000, le=2100)
    pop_start_year: float = R("people", "statistics", "National population in start_year.", gt=0)
    urban_ratio_start_year: float = R("share", "statistics", "Urban share of the population in start_year.",
                                      gt=0, lt=1)
    grid_elec_ratio_start_year: float = R("share", "statistics", "National grid electrification rate in start_year.",
                                          ge=0, le=1)
    grid_urban_elec_ratio: float = R("share", "statistics", "Urban grid electrification rate in start_year.",
                                     ge=0, le=1)
    grid_rural_elec_ratio: float = R("share", "statistics", "Rural grid electrification rate in start_year.",
                                     ge=0, le=1)

    # --- Grid calibration thresholds (calibrate_grid_elec_current)
    min_night_lights: float = P(0, "-", "grid_calibration",
                                "Night-light intensity above which a settlement may be considered electrified.",
                                ge=0)
    min_pop: float = P(50, "people", "grid_calibration",
                       "Settlement population above which a settlement may be considered electrified.", ge=0)
    max_mv_line_distance: float = P(2, "km", "grid_calibration",
                                    "Distance to current MV lines below which a settlement may be electrified "
                                    "(used when no transformer data exist).", gt=0)
    max_transformer_dist: float = P(1, "km", "grid_calibration",
                                    "Distance to a distribution transformer below which a settlement may be "
                                    "electrified.", gt=0)
    max_hv_dist: float = P(5, "km", "grid_calibration",
                           "Distance to HV lines used when neither transformers nor MV lines exist.", gt=0)

    # --- Existing mini-grids (notebook cell 15)
    mg_dist: float = P(0.5, "km", "mini_grid_calibration",
                       "Settlements closer than this to an existing mini-grid (MGDist) count as mini-grid "
                       "electrified. 0 disables mini-grid calibration.", ge=0)
    mg_ntl: float = P(0, "-", "mini_grid_calibration",
                      "Minimum night-light intensity for mini-grid electrified settlements.", ge=0)
    mg_pop: float = P(0, "people", "mini_grid_calibration",
                      "Minimum population for mini-grid electrified settlements.", ge=0)


REQUIRED_PARAMS = tuple(name for name, f in ScenarioParams.model_fields.items() if f.is_required())
DEFAULT_PARAMS = {name: f.default for name, f in ScenarioParams.model_fields.items() if not f.is_required()}


def describe_parameters(model=ScenarioParams):
    """Parameters grouped for display: {group: [{name, unit, default, required, description, constraints}]}."""
    schema = model.model_json_schema()["properties"]
    groups = {}
    for name, f in model.model_fields.items():
        s = schema[name]
        constraints = {k: s[k] for k in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "enum")
                       if k in s}
        groups.setdefault(s["group"], []).append({
            "name": name, "unit": s["unit"], "required": f.is_required(),
            "default": None if f.is_required() else f.default,
            "description": f.description, "constraints": constraints})
    return groups
