# EvEMTBench research basis

The PowerFactory equipment-library work is informed by:

> Georg Kordowich, Jonathan Loebel, Julian Oelhaf, Andreas Maier, Siming
> Bayer, Christian Bergler, and Johann Jaeger. “A simulation based dataset of
> faults and events for machine learning in power systems.” arXiv:2608.19777,
> 2026.

- Paper: <https://arxiv.org/abs/2608.19777>
- Dataset: <https://data.fau.de/share/0e8d60feb7e65616c60aab78b93db77053275da53fd894bf5b75fc5e9ee7dfbf/>
- Component-data catalog: [evemtbench_component_catalog.md](evemtbench_component_catalog.md)

## Relevance to the library tool

The paper creates detailed element models from pre-generated libraries and
documents ranges for cables, overhead lines and conductors, transformers,
synchronous machines, excitation systems, inverter-based resources, grounding
systems, capacitors, and arc models.

The first executable database covers the five fixed-voltage two-winding
transformer classes in Tables 10-12. It uses a supplied seed for reproducible
uniform sampling and defaults to preview mode. The creator builds a new
`TypTr2` and connected `ElmTr2` without copying or requiring an existing
transformer type. Creation requires the exact phrase returned by the preview.

### Table 11 mapping

| Published quantity | Unit | PowerFactory `TypTr2` attribute |
|---|---:|---|
| Rated apparent power, S n | MVA | `strn` |
| High-side rated voltage | kV | `utrn_h` |
| Low-side rated voltage | kV | `utrn_l` |
| Short-circuit voltage, u k | % | `uktr` |
| Winding/copper losses, P k | kW | `pcutr` |
| No-load losses, P l | kW | `pfe` |
| No-load current, I l | % | `curmg` |

The paper uses both 50 Hz and 60 Hz systems and assumes the same transformer
parameter ranges for both. The creator therefore requires the caller to choose
50 or 60 Hz explicitly, writes it to `frnom`, and sets three-phase technology
with `nt2ph = 3`. It does not infer frequency from `ElmNet.frnom` because an
existing project can contain transformer types at a different frequency.

The implemented voltage classes are 20/0.4, 110/20, 110/11, 380/110, and
345/25 kV. Each rating is selected from the discrete Table 11 rows, then each
reported interval is sampled uniformly. Fixed values remain fixed.

The versioned database is
[`../data/evemtbench_transformers.json`](../data/evemtbench_transformers.json).
It also stores Tables 10 and 12 and records the PowerFactory mappings that are
still pending. In particular, Table 11 gives vector-group families but does not
select a clock number for every generated transformer, so the caller must
provide that engineering choice explicitly.

The paper's `Block` class is catalog-only because its voltage ratio depends on
generator rating and project voltage. Table 10 zero-sequence and Table 12
saturation ranges are returned for inspection but are not written until their
PowerFactory attributes have been validated. The paper's ranges are a research
basis, not a claim that every sampled type is suitable for a specific study.

### Tables 3 and 7 overhead-line mapping

The second executable database is
[`../data/evemtbench_overhead_lines.json`](../data/evemtbench_overhead_lines.json).
It preserves the 5th, 50th and 95th percentile electrical parameters reported
for generated 20, 110 and 345 kV overhead lines. These are exposed as the
discrete `p05`, `p50` and `p95` profiles; they are not treated as endpoints of
a continuous sampling range. Table 3 supplies the accepted line-length range.

| Published quantity | Source unit | PowerFactory `TypLne` attribute |
|---|---:|---|
| Nominal voltage | kV | `uline` |
| Positive-sequence resistance, R1 | ohm/km | `rline` |
| Positive-sequence reactance, X1 | ohm/km | `xline` |
| Positive-sequence capacitance, C1 | nF/km | `cline` after conversion to uF/km |
| Zero-sequence resistance, R0 | ohm/km | `rline0` |
| Zero-sequence reactance, X0 | ohm/km | `xline0` |
| Zero-sequence capacitance, C0 | nF/km | `cline0` after conversion to uF/km |

The paper's percentile table does not associate each electrical profile with a
specific conductor current rating, so the caller must provide `rated_current_ka`
as an explicit engineering choice; it is stored as `sline`. The caller also
selects 50 or 60 Hz for `frnom`. The creator builds a three-phase sequence-
equivalent `TypLne` and connected `ElmLne` without an existing template.

This is intentionally not a geometric ULM recreation. The Table 7-9
tower/conductor geometry remains catalog-only.

### Tables 3 and 6 underground-cable mapping

The third executable equipment database is
[`../data/evemtbench_underground_cables.json`](../data/evemtbench_underground_cables.json).
It exposes the published 5th, 50th and 95th percentile 20 kV cable sequence
parameters as discrete profiles and uses Table 3's cable-length range.

| Published quantity | Source unit | PowerFactory `TypLne` attribute |
|---|---:|---|
| Nominal voltage | kV | `uline` |
| Positive-sequence resistance, R1 | ohm/km | `rline` |
| Positive-sequence reactance, X1 | ohm/km | `xline` |
| Positive-sequence capacitance, C1 | nF/km | `cline` after conversion to uF/km |
| Zero-sequence resistance, R0 | ohm/km | `rline0` |
| Zero-sequence reactance, X0 | ohm/km | `xline0` |
| Zero-sequence capacitance, C0 | nF/km | `cline0` after conversion to uF/km |

Table 6 does not publish cable ampacity, so the caller supplies
`rated_current_ka` as an engineering input for `sline` and selects 50 or 60 Hz
for `frnom`. The creator uses a sequence-equivalent `TypLne` and `ElmLne`.
Construction and installation values remain catalog metadata; the tool does
not claim to recreate the paper's geometric ULM model.

### Table 4 external-grid mapping

The fourth executable database is
[`../data/evemtbench_external_grids.json`](../data/evemtbench_external_grids.json).
It preserves the paper's complete 110 kV and combined 380/345 kV intervals and
uses a supplied seed for reproducible uniform sampling.

| Published quantity | Unit | PowerFactory `ElmXnet` attribute |
|---|---:|---|
| Short-circuit power, S''k | MVA | `snss` |
| Positive-sequence R/X | - | `rntxn` |
| X0/X1 | - | `x0tx1` |
| Zero-sequence R0/X0 | - | `r0tx0` |
| Voltage setpoint | pu | `usetp` |
| Initial phase angle | degrees | `phiini` |

The creator sets `bustp="SL"` and attaches the new `ElmXnet` to one existing
110, 345, or 380 kV bus. These field mappings were validated by live
PowerFactory 2026 SP1 readback; SP4 validation remains pending.

### Table 5 load mapping

The fifth executable database is
[`../data/evemtbench_loads.json`](../data/evemtbench_loads.json). It preserves
the paper's 20, 110, and 345 kV load-power ranges and the six ZIP coefficient
ranges and normalization constraints.

| Published quantity | Unit | PowerFactory `ElmLod` attribute |
|---|---:|---|
| Active power, P | MW | `plini` |
| Reactive power, Q | MVAr | `qlini` |

At 20 kV, the creator samples apparent power and an angle spanning 0.95
capacitive to 0.8 inductive, then converts them to P and Q. Positive Q denotes
inductive demand and negative Q denotes capacitive demand. Constant-power
creation remains the default. Opt-in `load_model="zip"` requires a new
`type_name` and creates a dedicated `TypLod` for load flow.

| ZIP quantity | `TypLod` attribute | Exponent attribute/value |
|---|---|---|
| kP,P / kQ,P | `aP` / `aQ` | `kpu0` / `kqu0` = 0 |
| kP,I / kQ,I | `bP` / `bQ` | `kpu1` / `kqu1` = 1 |
| kP,Z / kQ,Z | derived `cP` / `cQ` | `kpu` / `kqu` = 2 |

Each triplet sums to one. Negative coefficients are retained, not clamped.
Sampling is sequential uniform within feasible Z and conditional I intervals;
the power term is the residual. Power samples use the existing seeded stream;
ZIP coefficients use a separate stream. The old `catalog_only` JSON grouping
is retained for compatibility, but coefficients are available via opt-in ZIP.

Lab PC checks confirmed native Python writes, derived coefficients, and
load-flow response at 0.90-1.10 pu, including voltage-dependency-disabled
controls. See [FT-28](../evidence/FT-28_load_zip_mapping_lab_pc.txt).
Load flow must enable voltage dependency; the creator does not change `ComLdf`.
Integrated unified-tool creation and retained-value verification passed on
the Lab PC with the new load out of service; see
[FT-29](../evidence/FT-29_integrated_zip_load_creation_lab_pc.txt).
The voltage sweep used a separate diagnostic network, not the integrated load.
RMS/EMT ZIP behavior remains unvalidated.

### Table 13 synchronous-machine mapping

The seventh executable database is
[`../data/evemtbench_synchronous_machines.json`](../data/evemtbench_synchronous_machines.json).
The round-rotor creator maps the published type data to `TypSym` attributes
`sgn`, `ugn`, `cosn`, `rstr`, `xl`, `xd`, `xq`, `xds`, `xqs`, `xdss`, `xqss`,
`tds0`, `tqs0`, `tdss0`, `tqss0`, `x0sy`, `r0sy`, `x2sy`, `r2sy`, `tag`, `isat`,
`sg10`, `sg12`, `q_max`, and `q_min`. PowerFactory rotor mode `iturbo=1` is
used for round-rotor types. The connected `ElmSym` uses `typ_id`, `bus1`,
`pgini`, `qgini`, and `outserv`.

Table 13 publishes short-circuit time constants. PowerFactory derives those
from writable open-circuit inputs, so the creator converts them to `tds0`,
`tqs0`, `tdss0`, and `tqss0`, then verifies the derived `tds`, `tqs`, `tdss`,
and `tqss` values. These relationships and the rotor mode were established
through live PowerFactory 2026 SP1 inspection; confirmed creation still needs
to be repeated after this correction. Salient-pole creation is intentionally unavailable because
Table 13 leaves `x'q` and `T'q` undefined; inventing them would make a generated
type appear more completely paper-backed than it is.

## Affiliation

PowerFactory development and validation contributions by Aswin Krishna Poyil
are carried out at the **Institute of Electrical Energy Systems,
Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)** under the
supervision of Tobias Lorz and Timon Conrad, whose support provided the
opportunity to pursue this work independently.
