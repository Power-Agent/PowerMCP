# PowerFactory MCP supporting evidence

Latest follow-up records:

- [FT-38](FT-38_zip_rms_e2e_lab_pc.txt): real unified MCP preview/confirmation through RMS simulation of the actual two created loads, with [complete result](FT-38_zip_rms_e2e_lab_pc.json), [capture](FT-38_zip_rms_e2e_capture_lab_pc.json), [final state](FT-38_zip_rms_e2e_state_lab_pc.json) and [staged script](scripts/lab_zip_rms_e2e_check.py). Inductive/capacitive settled response passed; restoration and cleanup confirmed.
- [FT-37](FT-37_zip_rms_multiseed_lab_pc.txt): six sampled ZIP cases covering both Q signs plus six constant-power controls, with [complete JSON](FT-37_zip_rms_multiseed_lab_pc.json) and [standalone script](scripts/lab_zip_rms_multiseed_check.py). Settled balanced 20 kV / 50 Hz response only; not public creator integration.
- [FT-36](FT-36_integrated_rms_zip_creation_lab_pc.txt): successful `zip_rms` creation/readback, with [supplied compiled JSON capture](FT-36_integrated_rms_zip_creation_lab_pc.json); new load retained out of service, without simulation.
- [FT-35](FT-35_zip_rms_diagnostic_lab_pc.txt): isolated 50 Hz RMS comparison, with [complete traces/JSON](FT-35_zip_rms_diagnostic_lab_pc.json) and [standalone script](scripts/lab_zip_rms_diagnostic.py). Creator settings behaved as constant impedance; the explicit nonlinear diagnostic matched ZIP.
- [FT-34](FT-34_integrated_50hz_transformer_creation_lab_pc.txt): integrated 50 Hz creation/readback, with [compiled JSON extracts](FT-34_integrated_50hz_transformer_creation_lab_pc.json); new transformer retained out of service, no calculation.
- [FT-33](FT-33_ynd11_two_frequency_reference_lab_pc.txt): 50/60 Hz lossless YNd11 reference checks, with [complete JSON](FT-33_ynd11_two_frequency_reference_lab_pc.json) and [standalone script](scripts/lab_transformer_two_frequency_reference_check.py).
- [FT-32](FT-32_transformer_earth_fault_reference_lab_pc.txt): independent lossless YNd11 current reference, with [complete JSON](FT-32_transformer_earth_fault_reference_lab_pc.json) and [standalone script](scripts/lab_transformer_earth_fault_reference_check.py).
- [FT-31](FT-31_integrated_transformer_zero_sequence_creation_lab_pc.txt): successful unified-tool YNd11 zero-sequence creation and readback, with the transformer out of service.
- [FT-30](FT-30_transformer_zero_sequence_ynd_lab_pc.txt): YNd11 type writes and isolated earth-fault sensitivity/zero-sequence blocking checks on the Lab PC.
- [FT-29](FT-29_integrated_zip_load_creation_lab_pc.txt): successful integrated unified-tool ZIP creation and retained-value checks, with the load out of service.
- [FT-28](FT-28_load_zip_mapping_lab_pc.txt): ZIP attribute writes and isolated balanced load-flow voltage response, supplied from the Lab PC.
- [FT-27](FT-27_unified_evemtbench_catalog_mcp.txt): unified MCP tool exposure and filtered overhead-line listing with creation-parameter discovery.
- [FT-25](FT-25_bootstrap_confirmation_binding_sp1.txt): bootstrap stale-token rejection after the create/reuse plan changed.
- [FT-26](FT-26_pdf_diagram_restoration_sp1.txt): restoration of the previously active single-line diagram after successful PDF export.

These are compiled contributor-supplied records, with the validation limits stated in each file.

These files support the [function test report](POWERFACTORY_MCP_FUNCTION_TEST_REPORT.md).
The [contribution report](POWERFACTORY_MCP_CONTRIBUTION_REPORT.md) records the implementation scope.

- **Verbatim transcript:** copied from a complete captured MCP client transcript supplied during verification.
- **Verbatim extract:** an unchanged operation-and-response excerpt from a complete captured transcript.
- **Compiled evidence record:** assembled from raw responses supplied individually during verification; it is evidence, but not represented as a continuous terminal capture.
- **Captured automated transcript:** standard output from an actual automated run; only absolute machine-local executable and repository paths are replaced with documented placeholders.

PowerFactory account identifiers are replaced with `<user>` in committed records.

| ID | File | Classification |
|---|---|---|
| UT-01 | `UT-01_automated_tests.txt` | Captured automated transcript |
| UT-02 | `UT-02_pr95_review_tests.txt` | Compiled evidence record with captured output extracts |
| UT-03 | `UT-03_contingency_inspection_followup_tests.txt` | Compiled evidence record with captured output extracts |
| FT-01 | `FT-01_active_context.txt` | Verbatim extract |
| FT-02 | `FT-02_parameter_inspection.txt` | Verbatim extract |
| FT-03 | `FT-03_component_discovery.txt` | Verbatim extract |
| FT-04 | `FT-04_study_case_discovery.txt` | Verbatim extract |
| FT-05 | `FT-05_component_creation.txt` | Compiled evidence record |
| FT-06 | `FT-06_generator_verification.txt` | Verbatim extract |
| FT-07 | `FT-07_transformer_verification.txt` | Verbatim extract |
| FT-08 | `FT-08_component_deletion.txt` | Compiled evidence record |
| FT-09 | `FT-09_cleanup_calculations.txt` | Verbatim transcript |
| FT-10 | `FT-10_graphical_synchronization.txt` | Compiled evidence record |
| FT-11 | `FT-11_circuit_breaker_lifecycle.txt` | Compiled evidence record |
| FT-12 | `FT-12_contingency_recording_lifecycle.txt` | Compiled evidence record |
| FT-13 | `FT-13_contingency_inspection_sp1.txt` | Compiled evidence record |
| FT-14 | `FT-14_contingency_inspection_sp4.txt` | Compiled evidence record |
| FT-15 | `FT-15_active_grid_pdf_export_sp1.txt` | Compiled evidence record |
| FT-16 | `FT-16_evemtbench_transformer_creation_sp1.txt` | Compiled evidence record |
| FT-17 | `FT-17_evemtbench_overhead_line_creation_sp1.txt` | Compiled evidence record |
| FT-18 | `FT-18_greenfield_grid_bootstrap_sp1.txt` | Compiled evidence record |
| FT-19 | `FT-19_greenfield_bootstrap_transformer_sp1.txt` | Compiled evidence record |
| FT-20 | `FT-20_evemtbench_external_grid_creation_sp1.txt` | Compiled evidence record |
| FT-21 | `FT-21_evemtbench_load_creation_sp1.txt` | Compiled evidence record |
| FT-22 | `FT-22_evemtbench_underground_cable_creation_sp1.txt` | Compiled evidence record |
| FT-23 | `FT-23_evemtbench_synchronous_machine_creation_sp1.txt` | Compiled evidence record |
| FT-24 | `FT-24_unified_evemtbench_component_creation_sp1.txt` | Compiled evidence record |
| FT-28 | `FT-28_load_zip_mapping_lab_pc.txt` | Compiled evidence record; rounded summaries of user-supplied results |
| FT-29 | `FT-29_integrated_zip_load_creation_lab_pc.txt` | Compiled evidence record containing a user-supplied creation response |
| FT-30 | `FT-30_transformer_zero_sequence_ynd_lab_pc.txt` | Compiled evidence record; rounded summary of user-supplied Lab PC results |
| FT-31 | `FT-31_integrated_transformer_zero_sequence_creation_lab_pc.txt` | Compiled evidence record containing user-supplied creation and readback extracts |
| FT-32 | `FT-32_transformer_earth_fault_reference_lab_pc.txt` | Compiled evidence record with complete account-sanitized JSON and reproducible script |
| FT-33 | `FT-33_ynd11_two_frequency_reference_lab_pc.txt` | Compiled evidence record with complete account-sanitized two-frequency JSON and script |
| FT-34 | `FT-34_integrated_50hz_transformer_creation_lab_pc.txt` | Compiled record with creation/readback JSON extracts from supplied client transcript |
| FT-35 | `FT-35_zip_rms_diagnostic_lab_pc.txt` | Compiled record with complete account-sanitized RMS JSON and standalone script |
| FT-36 | `FT-36_integrated_rms_zip_creation_lab_pc.txt` | Compiled contributor capture; saved-output payloads and manually transcribed responses distinguished in the record |
| FT-37 | `FT-37_zip_rms_multiseed_lab_pc.txt` | Contributor-supplied complete account-sanitized JSON, standalone script and offline trace-reproduction checks |
| FT-38 | `FT-38_zip_rms_e2e_lab_pc.txt` | Complete account-sanitized successful E2E result/capture/state; corrected staged script and prompt; preceding failures disclosed separately |

UT-01 was refreshed on 19 September 2026 against PR #77 commit `2aeb38b`. The FT records retain their original dates and document separate live PowerFactory verification.

UT-02 and FT-12 were added for PR #95 on 7 October 2026. The contributor
reported the tested changes as committed in `04c1cbb`; the records disclose
that no independent byte-for-byte revision comparison was performed.
UT-02 retains the automated-run warning and distinguishes local tests from CI.
FT-12 records removal/repeat/restoration and the expected class-selection
removal rejection, without executing a calculation. Older records are unchanged.

UT-03 and FT-13 record the follow-up contingency inspection fixes developed on
top of PR #95. UT-03 covers the final automated suites. FT-13 records the live
PowerFactory 2026 SP1 bounded result read and explicitly distinguishes it from
the original SP4 reproduction. The restricted SP4 test machine consumes only
GitHub `main`, so post-fix SP4 validation remains pending until after merge.

FT-14 closes that validation gap after PR #95 was merged. It records positive
EvtShc discovery and a bounded, filtered read of the existing AC contingency
result on PowerFactory 2026 SP4. The result read completed without a timeout,
and the MCP server remained responsive afterward.

FT-15 records the live PowerFactory 2026 SP1 active-grid PDF export. It covers
diagram-name discovery, successful export, and filesystem verification of the
non-empty PDF. Visual inspection of the exported page is not claimed.

FT-16 records the live PowerFactory 2026 SP1 creation and readback of a new
EvEMTBench-backed two-winding transformer type and connected transformer. The
type was created without an existing transformer template, and its sampled
electrical values were recovered from the project library after creation.

FT-17 records the live PowerFactory 2026 SP1 creation and readback of a new
EvEMTBench-backed overhead-line sequence type and connected line. It covers the
preview confirmation boundary, unit conversion, retained sequence parameters,
type assignment, bus connections, length, and out-of-service state.

FT-18 records the live PowerFactory 2026 SP1 activation and readback of the
greenfield bootstrap grid and its two initial buses. It covers the preview and
confirmation boundary, immediate calculation-relevant discovery, retained
frequency and bus attributes, and idempotent reuse after activation.

FT-19 records the live PowerFactory 2026 SP1 integration from that activated
greenfield grid to a newly created EvEMTBench-backed transformer type and
connected transformer. It covers 50 Hz propagation, retained electrical
values, type assignment, both bus connections, and safe out-of-service state.

FT-20 records the live PowerFactory 2026 SP1 creation and readback of an
EvEMTBench Table 4 external-grid equivalent. It covers catalog filtering,
deterministic preview, explicit confirmation, retained short-circuit and
sequence-ratio values, terminal connection, and safe out-of-service state.

FT-21 records the live PowerFactory 2026 SP1 creation and readback of an
EvEMTBench Table 5 balanced load. It covers catalog filtering, deterministic
preview, explicit confirmation, retained active and reactive power, terminal
connection, and safe out-of-service state.

FT-22 records the live PowerFactory 2026 SP1 creation and readback of an
EvEMTBench Table 6 underground-cable sequence equivalent. It covers catalog
filtering, capacitance-unit conversion, explicit confirmation, retained
positive- and zero-sequence values, length, both terminal connections, and
safe out-of-service state.

FT-23 records the live PowerFactory 2026 SP1 creation and readback of an
EvEMTBench Table 13 round-rotor synchronous-machine type and connected
machine. It covers corrected time-constant conversion, retained electrical
and operating-point values, and serialization of a live PowerFactory type
reference as a plain full-name string on the dedicated PowerFactory thread.

FT-24 records the live PowerFactory 2026 SP1 creation and readback of a
round-rotor synchronous machine through the unified EvEMTBench component
creator. It covers nested-parameter routing, preview and confirmation,
persisted type and machine values, and server health after the operation.

FT-28 records user-supplied Lab PC ZIP load-type write/readback and isolated
balanced load-flow voltage-response checks. Negative coefficients and derived
terms were retained; all seven calculation points passed, with restoration
and cleanup confirmed. That record does not cover integrated creator execution.
See [FT-28](FT-28_load_zip_mapping_lab_pc.txt).

FT-29 records subsequent successful unified-tool creation and retained-value
checks for a dedicated ZIP type and out-of-service load. No calculation was
run on that load; the voltage-response test remains the separate FT-28 test.
FT-29 itself does not establish RMS or EMT ZIP behavior.

FT-35 subsequently distinguishes current creator settings from an explicitly
configured nonlinear RMS ZIP diagnostic. It validates settled response for one
coefficient set at 20 kV / 50 Hz with positive P/Q and zero time constants;
it does not validate the unchanged creator settings as RMS ZIP. The new
`zip_rms` mode's subsequent creation/readback passed in FT-36, without simulation
of the new load. Transient recovery,
frequency response and EMT remain unvalidated. FT-37 separately extends settled
response to six sampled cases, including capacitive Q. FT-28/FT-29 retain their
original load-flow-only scope.

FT-36 confirms retained sampled coefficients, RMS settings, operating point,
new type/bus assignment and out-of-service state in a grid already at 50 Hz.
The sampled Q is capacitive, but FT-36 does not validate its RMS response.
The supplied file preserves catalog/preview/creation/type-readback payloads
from saved output; other context/load/grid responses were transcribed by the
Lab assistant. Its classification is compiled evidence, not a continuous raw
capture. A corrected local evidence checker passed after initial field-location
errors; those checker errors were not a PowerFactory creation failure.

FT-37 records twelve isolated runs: sampled ZIP seeds 0, 1, 2 (inductive Q)
and 4, 7, 15 (capacitive Q), each paired with a constant-power control using the
same nominal P/Q. All settled comparisons passed; all 6036 samples are archived.
Each run restored context, checked its source type unchanged and cleaned up
without survivors. The offline test reproduces all twelve analyses with tight
roundoff tolerance and rejects a changed capacitive trace. This uses pure
creator plans on temporary copied types, not the public creation workflow or
the retained FT-36 load. Six seeds do not validate the full sampled domain;
transient recovery, nonzero time constants and other operating modes remain
outside scope. No creator restriction or default changes.

FT-38 separately joins real unified-tool preview/confirmation and actual-object
RMS response for seeds 0 (inductive) and 4 (capacitive). Both 503-sample runs
passed; the created types stayed unchanged. The already-active case guard
skipped redundant activation for both runs, while exact grid/scenario isolation
remained checked. Restoration and cleanup passed without survivors. The original
capture byte hash was verified before account sanitization; the archived hash
field is historical, not a hash of the sanitized file. Full result/capture/state
are included, along with the staged script, FT-37 helper and creation prompt.
Earlier activation, misplaced-token and capture-checker failures are disclosed
in the record and are not passing evidence. Only two seeds and settled balanced
50 Hz / 20 kV response are covered; no full-domain/transient/EMT claims or
creator default/restriction changes follow.

FT-31 records subsequent successful unified-tool creation of a dedicated YNd11
type and out-of-service transformer with the restricted zero-sequence equivalent.
Type impedance, derived values, type assignment and HV grounding were read back.
No calculation was run on this integrated transformer; fault-response evidence
remains the separate FT-30 test. Core/limb, magnetizing, saturation, absolute
fault-current accuracy and RMS/EMT validation remain outside FT-30/FT-31.

FT-32 separately records independent analytical agreement for an unloaded,
lossless temporary YNd11 equivalent. All four transformer comparisons and the
source-only control passed; restoration and cleanup were confirmed. This does
not certify absolute currents for the original lossy type or integrated
transformer, and does not widen the creator's supported configurations.

FT-33 extends the separate lossless reference checks to 50 Hz, retaining 60 Hz
as a regression control. Both source-only controls and all eight fault scenarios
passed; original context restoration, source-type checks and cleanup passed
after each frequency. This does not certify original lossy-type or integrated
transformer currents. FT-33 retains its historical pending-integration status.

FT-34 records subsequent successful 50 Hz unified-creator execution and retained
type, impedance, grounding and connection checks. The grid stayed at its existing
50 Hz and the new transformer remained out of service. Initial absolute-path
read queries failed; name-and-class queries then returned the intended objects.
No calculation, cleanup or failure-path rollback is claimed by this successful
creation. The complete preview is not archived in the supplied JSON extracts.
