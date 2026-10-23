# Test fixtures

- `case9.m`: the MATPOWER 9 bus case (BSD 3-Clause, PSERC and contributors).
- `powerworld/ACTIVSg200.pwd`: the PowerWorld display fixture the powerio
  tests decode; see `.gitignore` for why it stays tracked.
- `opendss/fourwire_linecode.dss`: an original four wire OpenDSS feeder from the
  powerio test suite (`tests/data/dist/micro`, CC BY 4.0), used to exercise the
  explicit multiconductor to balanced transformation at the solver boundary.
- `opendss/geometry_unresolved.dss`: a four conductor feeder whose line geometry
  carries no resolved impedance matrix, so a balanced transformation of it
  fails with a diagnostic instead of a network.
- `fake_tellegen.py`: a stand-in for the compiled `tellegen` CLI that speaks
  its JSON protocol, so the tellegen server tests run without a Rust toolchain.
