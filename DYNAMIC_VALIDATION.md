# Cross-engine dynamic trajectory validation

`powermcp.dynamic_validation` provides a simulator-independent comparison core
for transient and time-domain study outputs. It deliberately does not launch
simulators or guess channel mappings: engine adapters must provide equivalent
physical channel identifiers, identical units, matching case/study/disturbance
identifiers, and event timestamps in seconds.

## Minimal example

```python
from powermcp.dynamic_validation import (
    ChannelSeries, DynamicSnapshot, compare_dynamic_snapshots,
)

psse = DynamicSnapshot(
    engine="psse", case_id="ieee9", study_type="fault_response",
    disturbance_id="bus5_three_phase_fault_0.1s", event_time_s=1.0,
    channels={"bus:5:voltage": ChannelSeries(
        unit="pu", time_s=(1.0, 1.01, 1.02), values=(1.0, 0.82, 0.91),
    )},
)
andes = DynamicSnapshot(
    engine="andes", case_id="ieee9", study_type="fault_response",
    disturbance_id="bus5_three_phase_fault_0.1s", event_time_s=1.0,
    channels={"bus:5:voltage": ChannelSeries(
        unit="pu", time_s=(1.0, 1.005, 1.01, 1.015, 1.02),
        values=(1.0, 0.91, 0.82, 0.865, 0.91),
    )},
)
report = compare_dynamic_snapshots(psse, andes)
print(report.passed)
print(report.channels_compared[0].root_mean_square_error)
```

## Comparison contract

- Each channel owns its sample clock; timestamps must be finite and strictly
  increasing, with at least two finite samples.
- `event_time_s` is subtracted from each channel clock before alignment. Use
  the physical event origin (for example, fault application), not a convenient
  first sample, so event timing remains meaningful.
- Channel IDs and units are exact-match contracts. No implicit pu/kV, Hz/rad/s,
  MW/Mvar, or sign-convention conversion is performed.
- The comparison grid is the union of both sample grids over their common
  interval. Linear interpolation is used only inside each trace's observed
  interval. Extrapolation is forbidden.
- Reports include time-weighted MAE, RMSE, maximum absolute error, integrated
  absolute error, signed peaks, overlap bounds, and the allowed maximum error.
- A report passes only when at least one channel was compared and there are no
  missing channels, unit mismatches, insufficient-overlap channels, or channels
  outside the configured absolute-plus-relative maximum-error tolerance.
- Default tolerance is `1e-6 + 1e-5 * max_abs_signal`. Supply per-channel
  `(absolute_tolerance, relative_tolerance)` pairs when a study has justified,
  documented channel-specific tolerances. Unknown tolerance keys are errors.
- `max_points_per_channel` bounds alignment work and defaults to 100,000 points.

This core does not claim dynamic stability equivalence from waveform similarity
alone. It does not yet calculate damping ratios, critical clearing time, rotor
angle stability, or settling-time compliance. Those require explicit study
semantics and validated engine-specific adapters and should be layered on top
rather than inferred from arbitrary channel names.
