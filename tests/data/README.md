# Test fixtures

- `case9.m`: the MATPOWER 9 bus case (BSD 3-Clause, PSERC and contributors).
- `powerworld/ACTIVSg200.pwd`: the PowerWorld display fixture the powerio
  tests decode; see `.gitignore` for why it stays tracked.
- `opendss/fourwire_linecode.dss`: an original four wire OpenDSS feeder from the
  powerio test suite (`tests/data/dist/micro`, CC BY 4.0), used to exercise the
  explicit multiconductor to balanced transformation at the solver boundary.
