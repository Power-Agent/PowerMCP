# Cross-engine transient validation

PowerMCP provides a simulator-independent comparison core, strict PSS/E and
ANDES trajectory adapters, MCP snapshot-export tools, and deterministic JSON
and Markdown evidence reports.

The workflow has three explicit steps. The simulators are still launched by
their respective MCP servers or by the calling workflow; the comparison tool
does not silently launch either engine.

## 1. Export full-resolution engine snapshots

On the PSS/E MCP server, call `export_dynamic_validation_snapshot` after the
dynamic simulation has written its `.out`/`.outx` file:

```json
{
  "outfile": "/approved/path/fault.out",
  "channel_map": {
    "bus:5:voltage": {"source": 1, "unit": "pu"},
    "machine:1:angle": {"source": 2, "unit": "deg"}
  },
  "case_id": "kundur",
  "study_type": "fault_response",
  "disturbance_id": "bus5_3ph_fault_at_0.1s",
  "event_time_s": 0.1,
  "engine_version": "PSS/E 36.2",
  "simulation_settings": {"t_end_s": 10.0, "integration_step_s": 0.01}
}
```

The source channel numbers and units are explicit. The adapter rejects
downsampled PSS/E responses: increase `max_points` and `max_cells` to fit
the complete run rather than validating a display-oriented decimation.

On the ANDES MCP server, call `export_dynamic_validation_snapshot` after
`run_time_domain_simulation`:

```json
{
  "channel_map": {
    "bus:5:voltage": {"source": "y", "index": 0, "unit": "pu"},
    "machine:1:speed": {"source": "x", "index": 2, "unit": "pu"}
  },
  "case_id": "kundur",
  "study_type": "fault_response",
  "disturbance_id": "bus5_3ph_fault_at_0.1s",
  "event_time_s": 0.1,
  "engine_version": "ANDES <installed version>",
  "simulation_settings": {"t_end_s": 10.0, "integration_step_s": 0.01},
  "max_points": 100000,
  "max_cells": 1000000
}
```

ANDES selectors use `x` for differential states and `y` for algebraic
variables. The `index` is the index in the corresponding time-series matrix.
The mapping to canonical physical channel IDs and units must be established
from the model and study; the adapter deliberately does not guess that an
internal state is a voltage, speed, or angle. Ambiguous matrix orientation,
missing time history, invalid selectors, and histories exceeding the point/cell
budgets are errors. ANDES histories are never downsampled for validation.

Both tools return a portable `snapshot` object. Keep the study identifiers,
event origin, channel IDs and units consistent across the two exports.
Engine versions and run settings are recorded when supplied by the caller.

## 2. Compare the snapshots

Call `compare_dynamic_trajectories` on the ANDES MCP server with the two
snapshot objects returned above:

```json
{
  "left_snapshot": { "...": "PSS/E snapshot returned by export tool" },
  "right_snapshot": { "...": "ANDES snapshot returned by export tool" },
  "absolute_tolerance": 0.000001,
  "relative_tolerance": 0.00001,
  "minimum_overlap_s": 0.5,
  "max_points_per_channel": 100000,
  "channel_tolerances": {
    "bus:5:voltage": [0.0001, 0.0005]
  }
}
```

The comparison tool returns a pass/fail result, a provenance-bearing JSON
artifact, and a readable Markdown report. A report passes only when at least
one channel is compared and no channel is missing, has a unit mismatch,
insufficient overlap, or exceeds its tolerance.

## Comparison contract

- Each channel has its own strictly increasing sample clock and at least two
  finite samples.
- Event timestamps are converted to event-relative time before alignment.
  Supply the physical event origin (for example, fault application), not an
  arbitrary first sample.
- Channel IDs and units must match exactly. No implicit pu/kV, Hz/rad/s,
  MW/Mvar, angle-reference, or sign-convention conversion is performed.
- The comparison grid is the union of both sample grids over their common
  interval. Linear interpolation is used only within observed ranges;
  extrapolation is forbidden.
- Metrics include time-weighted MAE, RMSE, maximum absolute error, integrated
  absolute error, signed peaks, overlap bounds, and the allowed maximum error.
- Default tolerance is `atol + rtol * max_abs_signal`; per-channel
  `[atol, rtol]` pairs are supported and unknown keys are rejected.
- Alignment work is bounded by `max_points_per_channel`.
- Non-finite input and arithmetic overflow are rejected.

## Scope and engineering limits

This is an MCP-level export-and-compare workflow for completed runs. It does
not yet submit both simulations as one atomic study, synchronize their event
definitions, translate model parameters between engines, or guarantee that
the two models are physically equivalent. Those responsibilities belong in a
workflow/orchestration layer (for example PowerWF) and require explicit study
configuration and model validation.

The comparison does not infer dynamic-stability equivalence from waveform
similarity alone. Damping ratio, critical clearing time, rotor-angle stability,
and settling-time compliance require dedicated study semantics and validated
engine-specific calculations.

The report includes case/study/disturbance IDs, event origins, engine names,
optional engine versions, simulation settings, comparison settings, channel
metrics, and all mismatch/failure lists. Supply accurate engine versions and
simulation settings when exporting snapshots; the adapter cannot discover
every solver configuration from an arbitrary output file.
