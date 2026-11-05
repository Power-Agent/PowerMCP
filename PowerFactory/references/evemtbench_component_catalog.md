# EvEMTBench component-data catalog

## Status and intended use

This file is the human-reviewable source catalog for future PowerMCP library
and grid-construction tools. It transcribes the parameter ranges in Tables
2-18 of the EvEMTBench paper. It is not itself a runtime database, and
production code must not parse these Markdown tables.

After review, the approved values should be copied into a versioned
machine-readable file with explicit units, fixed values, closed intervals,
discrete choices, dependencies, and source-table identifiers. MCP tools can
then validate requests against that file and create new PowerFactory library
types without relying on an existing project template.

Intervals written as `[a; b]` are closed intervals. Braced values are discrete
choices. A dash means that the source does not define or use the parameter for
that case. Values below are source data, not PowerFactory attribute mappings.

## Source and provenance

Georg Kordowich, Jonathan Loebel, Julian Oelhaf, Andreas Maier, Siming Bayer,
Christian Bergler, and Johann Jaeger, "A simulation based dataset of faults
and events for machine learning in power systems," arXiv:2608.19777, 2026.

- Paper: <https://arxiv.org/abs/2608.19777>
- Dataset: <https://data.fau.de/share/0e8d60feb7e65616c60aab78b93db77053275da53fd894bf5b75fc5e9ee7dfbf/>
- Tables transcribed: 2-18
- Local validation source: the PDF supplied for this work

## Event and fault parameters - Table 2

| Parameter | Value or range |
|---|---|
| Event/fault start time | `[1.1; 1.3] s` |
| Fault location on line | `[1; 99] %` |
| Short-circuit resistance | `[0.001; 50] ohm` |
| High-impedance fault resistance | `[50; 150000] ohm`, non-uniform sampling described in the paper |
| Two-phase fault phases | `{a-b, b-c, c-a}` |
| Single-phase fault phases | `{a, b, c}` |
| Incipient-fault duration | `[0.002; 0.08] s` |

## Network topology and length parameters - Table 3

| Parameter | 20 kV | 110 kV | 345 kV |
|---|---:|---:|---:|
| Number of MV feeders | `[1; 5]` | - | - |
| Number of MV nodes per feeder | `[1; 5]` | - | - |
| Number of MV laterals per feeder | `[0; 2]` | - | - |
| Number of HV/EHV nodes | - | `[4; 19]` | `[4; 19]` |
| Number of HV/EHV lines | - | `[1.2*N_nodes; 1.6*N_nodes]` | `[1.2*N_nodes; 1.6*N_nodes]` |
| Maximum lines per HV/EHV bus | - | `5` | `5` |
| Load connection | `true` | `{true, false}` | `{true, false}` |
| Source-connection probability | `20 %` | `50 %` | `50 %` |
| Source type | `IBR` | `{synchronous machine, IBR}` | `synchronous machine` |
| Cable probability | `70 %` | `0 %` | `0 %` |
| Overhead-line length | `[0.5; 9.5] km` | `[1; 32] km` | `[1; 111] km` |
| Cable length | `[0.5; 3.75] km` | - | - |

## External-grid equivalents - Table 4

| Parameter | 380/345 kV external grid | 110 kV external grid |
|---|---:|---:|
| Short-circuit power `S''k` | `[10000; 53000] MVA` | `[800; 8000] MVA` |
| Positive-sequence `R/X` | `[0.1; 0.2]` | `[0.1; 0.2]` |
| `X0/X1` | `[2; 4]` | `[2; 4]` |
| Zero-sequence `R0/X0` | `[0.1; 0.2]` | `[0.1; 0.2]` |
| Voltage setpoint | `[0.98; 1.02] pu` | `[0.98; 1.02] pu` |
| Initial phase angle | `[-180; 180] degrees` | `[-180; 180] degrees` |

## Loads - Table 5

### Voltage-dependent load-model coefficients

| Coefficient | Range |
|---|---:|
| `kP,Z` | `[0.20; 1.31]` |
| `kP,I` | `[-1.14; 0.50]` |
| `kP,P` | `[0.14; 0.83]` |
| `kQ,Z` | `[0.43; 4.74]` |
| `kQ,I` | `[-6.19; 0.71]` |
| `kQ,P` | `[-0.14; 2.45]` |

Constraints: `kP,Z + kP,I + kP,P = 1` and
`kQ,Z + kQ,I + kQ,P = 1`.

### Load power

| Voltage level | Active power | Reactive/apparent power |
|---|---:|---:|
| 345 kV | `P = [9; 326] MW` | `Q = [3.6; 116] MVAr` |
| 110 kV | `P = [0; 31] MW` | `Q = [0; 12.5] MVAr` |
| 20 kV | - | `S = [0.1; 1.6] MVA`, power factor `[0.8 inductive; 0.95 capacitive]` |

## Underground cables - Table 6

### Construction and installation

| Parameter | Value or range |
|---|---|
| Rated voltage | `20 kV` |
| Insulation | `{PE, XLPE, EPR}` |
| Conductor material | `aluminum` |
| Sheath material | `copper` |
| Conductor cross-section | `{50, 70, 95, 120, 150, 185, 240, 300, 400, 500} mm2` |
| Matching sheath cross-section | `{16, 16, 16, 16, 25, 25, 25, 25, 25, 25} mm2` |
| Conductor radius | `sqrt(Acond/pi) mm` |
| Insulation thickness | `5.5 mm` |
| Sheath thickness | `sqrt(Ash/pi + (rcond+tins)^2) - (rcond+tins) mm` |
| Oversheath thickness | `2.5 mm` |
| Aluminum conductor resistivity | `2.8264 micro-ohm cm` |
| Copper sheath resistivity | `1.7241 micro-ohm cm` |
| Relative permittivity for PE/XLPE/EPR | `2.3 / 2.4 / 3.0` |
| Dielectric loss factor for PE/XLPE/EPR | `0.3e-3 / 0.4e-3 / 5e-3` |
| Burial depth | `[0.7; 1.2] m` |
| Arrangement | `{flat, trefoil}` |
| Flat phase spacing | `[dcab+0.07; 0.3] m` |
| Trefoil phase spacing | `dcab+0.005 m` |
| Earth resistivity | `[5; 500] ohm m` |

### Electrical-parameter percentiles per kilometre

Values are 5th, 50th, and 95th percentiles of generated cables.

| Parameter | 5th | 50th | 95th |
|---|---:|---:|---:|
| `R1` (ohm/km) | 0.0841 | 0.2125 | 0.6457 |
| `X1` (ohm/km) | 0.1007 | 0.1411 | 0.2688 |
| `C1` (nF/km) | 154.08 | 247.06 | 420.35 |
| `R0` (ohm/km) | 0.6561 | 0.7775 | 1.4464 |
| `X0` (ohm/km) | 0.2397 | 0.2661 | 0.5100 |
| `C0` (nF/km) | 154.08 | 247.06 | 420.35 |

## Overhead lines - Table 7

### Geometry and construction

| Parameter | 20 kV | 110 kV | 345 kV |
|---|---|---|---|
| Tower arrangement | `{flat, vertical}` | `{Danube, fork, S-tower, flat, flat 2E}` | `{Danube, fork, S-tower, flat, flat 2E}` |
| Conductor height at tower `a` | `[9.5; 14] m` | `[19; 28] m` | `[22; 60] m` |
| Lowest-sag height `b` | `[6; 0.9*a] m` | `[6; 0.9*a] m` | `[7.8; 0.9*a] m` |
| Sag `c` | `a-b` | `a-b` | `a-b` |
| Average conductor height `h` | `a-(2/3)c` | `a-(2/3)c` | `a-(2/3)c` |
| Conductor spacing `d` | `[1.4; 2.2] m` | `[3; 4.7] m` | `[6; 11] m` |
| Earth-wire horizontal distance `e` | - | `[3.2; 5] m` | `[7; 8] m` |
| Earth-wire vertical distance `f` | - | `[4; 5] m` | `[8; 15] m` |
| Arrangement deviation `m` | `[0; 1] m` | `[0; 1] m` | `[0; 1] m` |
| Danube conductor angle | - | `[60; 90] degrees` | `[60; 90] degrees` |
| Earth resistivity | `[5; 500] ohm m` | `[5; 500] ohm m` | `[5; 500] ohm m` |
| Shunt conductance | `[1.5e-6; 3.7e-3] micro-S/km` | same | same |
| Bundle spacing | - | - | `[0.4; 0.5] m` |
| Sub-conductors | `1` | `{1, 2}` | `{3, 4}` |
| Earth wires | `0` | `{1, 2}` | `{1, 2}` |
| Transposition | `{yes, no}` | `yes` | `yes` |

### Electrical-parameter percentiles per kilometre

| Parameter | 20 kV (5/50/95) | 110 kV (5/50/95) | 345 kV (5/50/95) |
|---|---|---|---|
| `R1` (ohm/km) | `0.12 / 0.31 / 1.88` | `0.03 / 0.06 / 0.14` | `0.01 / 0.02 / 0.05` |
| `X1` (ohm/km) | `0.35 / 0.39 / 0.44` | `0.25 / 0.29 / 0.40` | `0.23 / 0.26 / 0.29` |
| `C1` (nF/km) | `8.24 / 9.44 / 10.47` | `9.08 / 12.58 / 14.62` | `12.49 / 13.82 / 15.70` |
| `R0` (ohm/km) | `0.27 / 0.45 / 2.02` | `0.23 / 0.31 / 0.41` | `0.17 / 0.22 / 0.28` |
| `X0` (ohm/km) | `1.38 / 1.60 / 1.70` | `0.78 / 1.07 / 1.24` | `0.74 / 0.95 / 1.06` |
| `C0` (nF/km) | `4.09 / 4.45 / 4.83` | `4.70 / 5.59 / 7.03` | `5.53 / 6.32 / 7.72` |

## Conductors - Tables 8 and 9

### Available conductor data - Table 8

| Parameter | AST (Al/St) | AL | ALD | Earth wire (Al/St) |
|---|---|---|---|---|
| Nominal cross-section (mm2) | `[16; 1045]` | `[15.9; 999.7]` | `[16.0; 999.7]` | `[35; 95]` |
| Inner diameter (mm) | `[1.80; 12.00]` | - | - | - |
| Outer diameter (mm) | `[5.40; 43.00]` | `[5.10; 41.10]` | `[5.10; 41.10]` | `[5.40; 13.60]` |
| DC resistance (ohm/km) | `[0.0277; 1.8769]` | `[0.0336; 2.091]` | `[0.029; 1.7986]` | `[0.3060; 0.8342]` |
| Rated current (A) | `[105; 1580]` | `[110; 1540]` | `[105; 1450]` | - |

### Selection criteria - Table 9

| Voltage level | Conductor type | Criterion |
|---|---|---|
| 20 kV | `AL`, `ALD`, or `AST` | `100 A <= rated current <= 650 A` |
| 110 kV | `AST` | `185 mm2 <= cross-section <= 525 mm2` |
| 345 kV | `AST` | `185 mm2 <= cross-section <= 800 mm2` |
| Earth wire | `AST` | `35 mm2 <= cross-section <= 95 mm2` |

## Transformer zero-sequence and limb data - Table 10

The executable opt-in `ynd11_equivalent` is restricted to 20 MVA, 110/20 kV,
60 Hz YNd11 with explicit ratios from the three-limb numerical intervals.
This is an impedance equivalent, not a physical limb/core implementation.
Other rows below remain catalog data; see [mapping limits](evemtbench.md#restricted-table-10-ynd11-equivalent).

| Class | Rating range | Limb/vector condition | `x0/x1` | `r0/r1` |
|---|---|---|---|---|
| 20/0.4 | all | `Dyn` | `[0.95; 1.0]` | `[1.2; 1.8]` |
| 20/0.4 | all | `Yzn` | `[0.07; 0.11]` | `[0.45; 0.54]` |
| 110/20 | all | `{3, 5}` limbs | `[0.85; 1.0]` (3), `[0.95; 1.05]` (5) | `[1.5; 2.8]` (3), `[1.05; 1.1]` (5) |
| 110/11 | all | `{3, 5}` limbs | `[0.85; 1.0]` (3), `[0.95; 1.05]` (5) | `[1.5; 2.8]` (3), `[1.05; 1.1]` (5) |
| 380/110 | all | `{3, 5}` limbs, with/without internal delta | `[1.8; 3.0]` (3 with delta), `[5; 10]` (3 without), `[2; 5]` (5 with), `[10; 100]` (5 without) | `[0.95; 1.05]` |
| 345/25 | `<50 MVA` | 3 limbs | `[0.85; 1.0]` | `[1.0; 3.0]` |
| 345/25 | `[50; 350] MVA` | 3 limbs | `[0.85; 0.95]` | `[1.8; 2.0]` |
| 345/25 | `>350 MVA` | 5 limbs | `[0.95; 1.05]` | `[1.0; 1.1]` |
| Block | `<40 MVA` | 3 limbs | `[0.85; 1.0]` | `[1.0; 3.0]` |
| Block | `[40; 200] MVA`, 110 kV | 3 limbs | `[0.85; 1.0]` | `[1.5; 2.8]` |
| Block | `[40; 200] MVA`, 345 kV | 3 limbs | `[0.85; 0.95]` | `[1.8; 2.0]` |
| Block | `>200 MVA` | 5 limbs | `[0.95; 1.05]` | `[1.0; 1.1]` |

## Transformer ratings and losses - Table 11

Columns are rated apparent power `Sn`, short-circuit voltage `uk`, winding loss
`Pk`, no-load loss `Pl`, no-load current `Il`, and vector group.

| Class | Sn (MVA) | uk (%) | Pk (kW) | Pl (kW) | Il (%) | Group |
|---|---:|---:|---:|---:|---:|---|
| 20/0.4 | 0.16 | 4.0 | `[2.35; 3.10]` | `[0.375; 0.460]` | `[1.1; 1.7]` | `Dyn`, `Yzn` |
| 20/0.4 | 0.25 | `[4.0; 6.0]` | `[2.75; 4.20]` | `[0.425; 0.650]` | `[1.1; 1.7]` | `Dyn`, `Yzn` |
| 20/0.4 | 0.40 | `[4.0; 6.0]` | `[3.85; 6.00]` | `[0.610; 0.930]` | `[0.9; 1.4]` | `Dyn` |
| 20/0.4 | 0.63 | `[4.0; 6.0]` | `[5.40; 8.70]` | `[0.800; 1.300]` | `[0.8; 1.2]` | `Dyn` |
| 20/0.4 | 1.00 | 6.0 | `[9.50; 13.00]` | `[1.100; 1.700]` | `[0.8; 1.2]` | `Dyn` |
| 20/0.4 | 1.60 | 6.0 | `[14.00; 20.00]` | `[1.700; 2.600]` | `[0.7; 1.1]` | `Dyn` |
| 110/20 | 20 | `[10.0; 12.0]` | `[95; 100]` | `[14; 16]` | `[0.4; 0.5]` | `YNd` |
| 110/20 | 25 | `[10.0; 12.0]` | `[110; 115]` | `[16; 19]` | `[0.4; 0.5]` | `YNd` |
| 110/20 | 31.5 | `[10.0; 13.0]` | `[130; 135]` | `[19; 23]` | `[0.4; 0.45]` | `YNd` |
| 110/20 | 40 | `[10.0; 15.0]` | `[155; 160]` | `[23; 27]` | `[0.35; 0.4]` | `YNd` |
| 110/20 | 50 | `[13.0; 15.8]` | 190 | 32 | `[0.35; 0.4]` | `YNd` |
| 110/20 | 63 | `[13.0; 16.0]` | 220 | 38 | `[0.35; 0.4]` | `YNd` |
| 110/20 | 80 | `[14.0; 16.0]` | 260 | 45 | 0.35 | `YNd` |
| 110/11 | 20 | `[10.0; 12.0]` | `[95; 100]` | `[14; 16]` | `[0.4; 0.5]` | `YNd` |
| 380/110 | 100 | `[14.0; 16.0]` | `[350; 460]` | `[40; 60]` | `[0.35; 0.46]` | `YNyn` |
| 380/110 | 160 | `[14.0; 16.0]` | `[480; 560]` | `[64; 96]` | `[0.30; 0.35]` | `YNyn` |
| 380/110 | 200 | `[14.0; 16.0]` | `[560; 700]` | `[80; 120]` | `[0.28; 0.35]` | `YNyn` |
| 380/110 | 250 | `[15.0; 17.0]` | `[650; 825]` | `[100; 150]` | `[0.26; 0.33]` | `YNyn` |
| 380/110 | 300 | `[16.0; 19.0]` | `[690; 930]` | `[120; 180]` | `[0.23; 0.31]` | `YNyn` |
| 380/110 | 400 | `[16.0; 20.0]` | `[840; 1160]` | `[160; 240]` | `[0.21; 0.29]` | `YNyn` |
| 380/110 | 500 | `[16.0; 20.0]` | `[1000; 1400]` | `[200; 300]` | `[0.20; 0.28]` | `YNyn` |
| 345/25 | 100 | `[14.0; 16.0]` | `[350; 460]` | `[40; 60]` | `[0.35; 0.46]` | `YNd` |
| 345/25 | 160 | `[14.0; 16.0]` | `[480; 560]` | `[64; 96]` | `[0.30; 0.35]` | `YNd` |
| 345/25 | 200 | `[14.0; 16.0]` | `[560; 700]` | `[80; 120]` | `[0.28; 0.35]` | `YNd` |
| 345/25 | 250 | `[15.0; 17.0]` | `[650; 825]` | `[100; 150]` | `[0.26; 0.33]` | `YNd` |
| 345/25 | 300 | `[16.0; 19.0]` | `[690; 930]` | `[120; 180]` | `[0.23; 0.31]` | `YNd` |
| 345/25 | 400 | `[16.0; 20.0]` | `[840; 1160]` | `[160; 240]` | `[0.21; 0.29]` | `YNd` |
| 345/25 | 500 | `[16.0; 20.0]` | `[1000; 1400]` | `[200; 300]` | `[0.20; 0.28]` | `YNd` |
| 345/25 | 600 | `[16.0; 20.0]` | `[1200; 1680]` | `[240; 360]` | `[0.20; 0.28]` | `YNd` |
| 345/25 | 800 | `[16.0; 20.0]` | `[1440; 2080]` | `[320; 480]` | `[0.18; 0.26]` | `YNd` |

The `Block` class uses the same rows as 110/20 and 345/25 plus the following:

| Sn (MVA) | uk (%) | Pk (kW) | Pl (kW) | Il (%) | Group |
|---:|---:|---:|---:|---:|---|
| 1000 | `[16.0; 20.0]` | `[1600; 2400]` | `[400; 600]` | `[0.16; 0.24]` | `YNd` |
| 1200 | `[16.0; 20.0]` | `[1680; 2640]` | `[480; 720]` | `[0.14; 0.22]` | `YNd` |

For block transformers the low-side generator voltage depends on generator
rating: 6.3 kV up to 40 MVA, 10.5 kV up to 200 MVA, 21 kV up to 800 MVA, and
27 kV above 800 MVA. The high side is the relevant primary transmission or
subtransmission voltage. The paper notes common `YNd5/11`, `Dyn5`, and `Yzn5`
usage, but Table 11 itself does not select one clock number for each row.

## Transformer saturation - Table 12

| Parameter | Value or range |
|---|---|
| Flux linkage `psi0` | `[1.20; 1.25] pu` |
| Saturated/air-core reactance `XM,air` | `[1; 2] * uk/100 pu` |

The paper additionally states that saturation sharpness `ksat` is set to 15.

## Synchronous machines - Table 13

| Parameter | Salient pole | Round rotor |
|---|---|---|
| `Sgn` (MVA) | `[17.5; 700]` | `[25; 1200]` |
| Rated power factor | `[0.8; 0.95]` | `[0.8; 0.975]` |
| `Vgn` (kV) | 6.3 if `Sgn<=40`; 10.5 if `Sgn<=200`; 21 if `Sgn<=800`; 27 otherwise | same rule |
| `x''d` (pu) | `[0.12; 0.3]` | `[0.09; 0.22]` |
| `x''q` (pu) | `[1*x''d; 3*x''d]` | `[1*x''d; 1.1*x''d]` |
| `x'd` (pu) | `[0.20; 0.45]`, minimum `1.01*x''d` | `[0.14; 0.35]`, minimum `1.01*x''d` |
| `x'q` (pu) | - | `[0.9*x'd; 1.0*x'd]`, minimum `1.01*x''q` |
| `xd` (pu) | `[0.8; 1.4]`, minimum `1.01*x'd` | `[1.4; 3.0]`, minimum `1.01*x'd` |
| `xq` (pu) | `[0.6*xd; 0.7*xd]`, minimum `1.01*x''q` | `[0.9*xd; 1.0*xd]`, minimum `1.01*x'q` |
| `T'd` (s) | `[0.7; 2.2]` | `[0.8; 1.5]` |
| `T'q` (s) | - | `[0.298; 0.756]` |
| `T''d` (s) | `[0.02; 0.1]` | `[0.02; 0.05]` |
| `T''q` (s) | `[0.017; 0.035]` | `[0.01; 0.035]` |
| `x(0)` (pu) | `[0.05; 0.2]` | `[0.03; 0.1]` |
| `r(0)` (pu) | 0 | 0 |
| `x(2)` (pu) | `[0.9; 1.1]*x''d` | `[0.9; 1.1]*x''d` |
| `r(2)` (pu) | `[0.014; 0.060]` | `[0.005; 0.029]` |
| `Tag` (s) | `[5; 10]` | `[5; 10]` |
| `isat` | 3 | 3 |
| `SG1.0` (pu) | `[0.064; 0.313]` | `[0.07; 0.340]` |
| `SG1.2` (pu) | `[0.282; 1.018]`, minimum `SG1.0` | `[0.290; 1.12]`, minimum `SG1.0` |
| `rstr` (pu) | `[0.0014; 0.006]` | `[0.0016; 0.005]` |
| Leakage reactance `xl` (pu) | `[0.12; min(0.9, x''d, x''q)]` | `[0.07; min(0.333, x''d, x''q)]` |
| `qmax` (pu) | 0.48 | 0.48 |
| `qmin` (pu) | -0.41 | -0.41 |

The `qmax` and `qmin` values correspond to inductive power factor 0.906 and
capacitive power factor 0.925, respectively, as footnoted in the source.

## AC1A excitation systems - Table 14

Unless marked fixed, sample each nominal value within +/-10 percent.

| Parameter | Nominal | Rule |
|---|---:|---|
| `Ka` | 400 | +/-10% |
| `Kc` | 0.2 | +/-10% |
| `Ta` | 0.02 | +/-10% |
| `Kf` | 0.03 | +/-10% |
| `Tf` | 1 | +/-10% |
| `Te` | 0.8 | +/-10% |
| `Ke` | 1 | +/-10% |
| `Kd` | 0.38 | +/-10% |
| `E1` | 3.14 | +/-10% |
| `SE1` | 0.03 | +/-10% |
| `E2` | 4.18 | +/-10% |
| `SE2` | 0.1 | +/-10% |
| `Vamin` | -14.5 | +/-10% |
| `Vamax` | 14.5 | +/-10% |
| `Tb` | 0 | fixed |
| `Tc` | 0 | fixed |
| `Tr` | 0 | fixed |
| `Vrmin` | -999 | fixed |
| `Vrmax` | 999 | fixed |

## Inverter-based resources - Table 15

| Parameter | 20 kV | 110 kV |
|---|---:|---:|
| IBR rated apparent power `Sn` | `[1; 15] MVA` | `[20; 50] MVA` |
| Active-power setpoint `Pn` | `[0.1; 0.9] pu` | `[0.1; 0.9] pu` |
| Reactive/active-power ratio `Qn/Pn` | `[0.05; 0.1] pu` | `[0.05; 0.1] pu` |
| Transformer rated power | identical to IBR | identical to IBR |
| Transformer `uk` | `6 %` | `12 %` |
| Transformer winding losses | `18 kW` | `130 kW` |

## Grounding systems - Table 16

| Parameter | 20 kV | 110 kV | 345 kV |
|---|---|---|---|
| Grounding type | `{solid, resistive, resonant}` | `{solid, resistive, resonant}` | `solid` |
| Arc-suppression-coil tuning | `[-10; 10] A` | `[-10; 10] A` | - |
| Resistive share of coil current | `[2; 3] %` | `[2; 3] %` | - |
| Solid-grounding resistance | `[0.1; 2] ohm` | `[0.1; 2] ohm` | `[0.1; 2] ohm` |
| Resistive-grounding resistance | `[5.77; 9.62] ohm` | `[6.35; 31.75] ohm` | - |

## Shunt capacitors - Table 17

| Voltage level | Three-phase reactive power |
|---|---:|
| 20 kV | `[0.3; 2.4] MVAr` |
| 110/345 kV | `[60; 200] MVAr` |

## Arc models - Table 18

| Parameter | Cable | 20 kV OHL | 110 kV OHL | 345 kV OHL |
|---|---:|---:|---:|---:|
| Time constant | `[0.05; 0.4] ms` | `[0.05; 0.65] ms` | `[0.3; 1.2] ms` | `[0.3; 1.2] ms` |
| Arc voltage | `[300; 4000] V` | `[535; 1075] V` | `[2200; 5800] V` | `[4900; 13900] V` |
| Arc resistance | `[0; 0.015] ohm` | `[0.014; 0.038] ohm` | `[0.088; 0.248] ohm` | `[0.208; 0.608] ohm` |

## Induction motors

The paper does not publish a new motor parameter table. It states that the
dataset randomly selects from 157 predefined models in PowerFactory's built-in
induction-motor library. This is not sufficient for a template-free motor
creator and must not be represented as a complete motor database.

## Rules for future PowerMCP creators

1. Create project-library types directly; do not require an existing grid
   component or type as a template.
2. Keep a preview and exact-confirmation boundary around every operation that
   writes library types or grid elements.
3. Require or create the connection buses separately, and validate their
   nominal voltages before connecting equipment.
4. Treat every dependency and conditional range in this catalog as validation,
   not merely documentation.
5. Never infer a transformer clock number from a vector-group family when the
   paper does not select it. Require the caller to choose from a documented
   engineering policy.
6. Keep parameters absent from the paper visibly unresolved. Do not silently
   describe PowerFactory defaults as paper-derived values.
7. Store the catalog version and paper table number in every generated plan so
   evidence can reproduce the chosen values and random seed.
8. Roll back both the library type and connected grid element when a confirmed
   atomic creation fails.

## PowerFactory mapping status

| Data family | Source captured | PowerFactory attribute mapping | Template-free creator |
|---|---|---|---|
| Events/faults | yes | partial, existing tools | not planned as a library type |
| External grids | yes | validated on PowerFactory 2026 SP1 | implemented |
| Loads | yes | power mapped (`plini`, `qlini`); opt-in ZIP `TypLod` for load flow | constant power default; RMS/EMT ZIP unvalidated |
| Underground cables | yes | sequence equivalent validated on SP1 | implemented |
| Overhead lines/conductors | yes | sequence equivalent validated on SP1 | implemented |
| Transformers | yes, Tables 10-12 | Table 11; restricted opt-in Table 10 YNd11 equivalent | full core/limb and Table 12 unsupported |
| Synchronous machines | yes | round-rotor attributes inspected on SP1; open-circuit time-input correction awaits creation retest | round-rotor creator implemented; salient profile catalog-only |
| AC1A exciters | yes | pending | pending |
| IBRs | yes | pending | pending |
| Grounding systems | yes | pending | pending |
| Shunt capacitors | yes | pending | pending |
| Arc models | yes | pending | pending |
| Induction motors | incomplete in paper | not mapped | blocked without another source |

## Affiliation

PowerFactory development and validation contributions by Aswin Krishna Poyil
are carried out at the **Institute of Electrical Energy Systems,
Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)** under the
supervision of Tobias Lorz and Timon Conrad, whose support provided the
opportunity to pursue this work independently.
