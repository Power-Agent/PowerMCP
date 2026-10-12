# PowerFactory MCP supporting evidence

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
