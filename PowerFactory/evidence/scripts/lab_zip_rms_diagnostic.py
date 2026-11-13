"""Standalone ComPython diagnostic. Stop MCP and activate test / Case 1.

Three isolated RMS runs, no production model changes. New diagnostic feeder
parameters and zero time constants are not paper-derived dynamic parameters.
Full traces and failures are saved beside this script in lab_results.
"""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Replace <user> with the Lab PC PowerFactory account before execution.
PROJECT = "\\<user>.IntUser\\test.IntPrj"
SOURCE_NAME = "MCP ZIP Load Type Integration 01"
SOURCE_PATH = (PROJECT + "\\Library.IntPrjfolder\\Equipment Type Library.IntPrjfolder"
               "\\Load Types.IntPrjfolder\\" + SOURCE_NAME + ".TypLod")
FIELDS = ("aP", "bP", "cP", "aQ", "bQ", "cQ", "kpu0", "kpu1", "kpu",
          "kqu0", "kqu1", "kqu", "loddy", "i_nln", "t1", "tpf", "tqf",
          "tpu", "tqu", "kpf", "kqf")
P0, Q0 = 1.0, 0.4
DT, STOP = .01, 5.0
WINDOWS = (("before", .5, .9), ("dip", 2., 2.8), ("recovered", 4., 4.8))
POWER_REL, POWER_ABS = .005, .0001
MODES = ("creator_unchanged", "nonlinear_zip", "constant_power_control")


def name(obj):
    return None if obj is None else obj.GetFullName()


def check(actual, expected, label, rel=1e-6, absolute=1e-6):
    if not math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=absolute):
        raise RuntimeError(f"{label}: expected {expected}, found {actual}")


def set_values(obj, values):
    for key, expected in values.items():
        setattr(obj, key, expected)
        actual = obj.GetAttribute(key)
        if isinstance(expected, (float, int)):
            check(actual, expected, key)
        elif isinstance(expected, str):
            if actual != expected:
                raise RuntimeError(f"{key}: expected {expected!r}, found {actual!r}")
        elif name(actual) != name(expected):
            raise RuntimeError(f"{key}: reference not retained")


def command(obj, method):
    code = getattr(obj, method)()
    if code not in (None, 0):
        raise RuntimeError(f"{name(obj)}.{method} returned {code}")


def active_grids(app):
    folder = app.GetProjectFolder("netdat")
    if folder is None:
        raise RuntimeError("Network Data folder missing")
    prefix = name(folder) + "\\"
    return sorted(name(o) for o in (app.GetCalcRelevantObjects("*.ElmNet") or [])
                  if name(o).startswith(prefix))


def physical_grids(app):
    paths = set(active_grids(app))
    return [o for o in (app.GetCalcRelevantObjects("*.ElmNet") or []) if name(o) in paths]


def snapshot(typ):
    values = {field: float(typ.GetAttribute(field)) for field in FIELDS}
    if not all(math.isfinite(value) for value in values.values()):
        raise RuntimeError("Non-finite load-type attribute")
    return values


def zip_power(u, coefficients):
    return (P0 * (coefficients["aP"] + coefficients["bP"] * u + coefficients["cP"] * u*u),
            Q0 * (coefficients["aQ"] + coefficients["bQ"] * u + coefficients["cQ"] * u*u))


def power_close(p, q, ep, eq):
    return (math.isclose(p, ep, rel_tol=POWER_REL, abs_tol=POWER_ABS)
            and math.isclose(q, eq, rel_tol=POWER_REL, abs_tol=POWER_ABS))


def analyze(samples, coefficients, mode, loadflow):
    """Keep creator-mode classification separate from experimental validity."""
    if not samples or samples[0]["time_s"] > .05 or samples[-1]["time_s"] < STOP - .02:
        raise RuntimeError("RMS result does not cover the required simulation interval")
    times = [s["time_s"] for s in samples]
    if any(b < a for a, b in zip(times, times[1:])):
        raise RuntimeError("Result times are not ordered")
    rows = []
    for label, start, end in WINDOWS:
        points = [s for s in samples if start <= s["time_s"] <= end]
        if len(points) < 10:
            raise RuntimeError(f"Too few RMS samples in {label} window")
        means = {key: sum(p[key] for p in points) / len(points)
                 for key in ("u_pu", "p_mw", "q_mvar")}
        spans = {key: max(p[key] for p in points) - min(p[key] for p in points)
                 for key in means}
        if spans["u_pu"] > .001 or spans["p_mw"] > .002 or spans["q_mvar"] > .002:
            raise RuntimeError(f"{label} window has not settled; transient dynamics are not being validated")
        u, p, q = means["u_pu"], means["p_mw"], means["q_mvar"]
        if not .85 <= u <= 1.15:
            raise RuntimeError("Voltage outside the diagnostic comparison range")
        ep, eq = zip_power(u, coefficients)
        rows.append(dict(window=label, samples=len(points), means=means, spans=spans,
                         zip_expected_mw=ep, zip_expected_mvar=eq,
                         matches_zip=power_close(p, q, ep, eq),
                         matches_constant_power=power_close(p, q, P0, Q0)))
    initial = rows[0]["means"]
    check(initial["u_pu"], loadflow["u_pu"], "RMS versus LF initial voltage", rel=.001, absolute=.001)
    if not power_close(initial["p_mw"], initial["q_mvar"], loadflow["p_mw"], loadflow["q_mvar"]):
        raise RuntimeError("RMS initial power does not match load flow; inspect units/normalization")
    if initial["u_pu"] - rows[1]["means"]["u_pu"] < .01:
        raise RuntimeError("No sustained voltage dip of at least 0.01 p.u.; event/topology not validated")
    for key in initial:
        check(rows[2]["means"][key], initial[key], "recovery " + key, rel=.002, absolute=.001)
    for row in rows:
        u, p, q = (row["means"][k] for k in ("u_pu", "p_mw", "q_mvar"))
        zscale = (u / initial["u_pu"]) ** 2
        row["matches_initial_constant_impedance"] = power_close(
            p, q, initial["p_mw"] * zscale, initial["q_mvar"] * zscale)
        row["matches_initial_constant_power"] = power_close(
            p, q, initial["p_mw"], initial["q_mvar"])
    matches_zip = all(r["matches_zip"] for r in rows)
    matches_p = all(r["matches_constant_power"] for r in rows)
    matches_z = all(r["matches_initial_constant_impedance"] for r in rows)
    return dict(windows=rows, experiment_valid=True,
                matches_zip=matches_zip, matches_constant_power=matches_p,
                matches_initial_constant_power=all(r["matches_initial_constant_power"] for r in rows),
                matches_initial_constant_impedance=matches_z,
                control_passed=(matches_zip if mode == "nonlinear_zip" else
                                matches_p if mode == "constant_power_control" else None))


def cell(res, row, column):
    value = res.GetValue(row, column)
    if not isinstance(value, (list, tuple)) or len(value) != 2 or value[0] != 0:
        raise RuntimeError(f"ElmRes.GetValue({row},{column}) failed: {value!r}")
    number = float(value[1])
    if not math.isfinite(number):
        raise RuntimeError("Non-finite RMS result")
    return number


def read_series(res, bus, load, pvar, qvar):
    command(res, "Load")
    try:
        columns = [res.FindColumn(obj, variable) for obj, variable in
                   ((bus, "m:u"), (load, pvar), (load, qvar))]
        if any(not isinstance(c, int) or c < 0 for c in columns):
            raise RuntimeError(f"Registered RMS result columns missing: {columns}")
        rows = int(res.GetNumberOfRows())
        if not 10 <= rows <= 20000:
            raise RuntimeError(f"Unexpected number of result rows: {rows}")
        return [dict(time_s=cell(res, i, -1), u_pu=cell(res, i, columns[0]),
                     p_mw=cell(res, i, columns[1]), q_mvar=cell(res, i, columns[2]))
                for i in range(rows)]
    finally:
        command(res, "Release")


def validate_case(app, mode):
    report = dict(success=False, mode=mode, restored=False, cleanup_ok=False,
                  remaining_objects=[], trace=[])
    project, original_case = app.GetActiveProject(), app.GetActiveStudyCase()
    if name(project) != PROJECT or name(original_case) != PROJECT + "\\Study Cases.IntPrjfolder\\Case 1.IntCase":
        raise RuntimeError("Activate test and Case 1; no temporary objects created")
    if mode not in MODES:
        raise ValueError("Unknown diagnostic mode")
    found = project.GetContents(SOURCE_NAME + ".TypLod", 1) or []
    if len(found) != 1 or name(found[0]) != SOURCE_PATH:
        raise RuntimeError("Expected exactly the inspected integrated ZIP type at its library path")
    original_type = found[0]
    original_values = snapshot(original_type)
    expected_exp = dict(kpu0=0, kpu1=1, kpu=2, kqu0=0, kqu1=1, kqu=2)
    for key, expected in expected_exp.items():
        check(original_values[key], expected, "source " + key)
    # Require the source RMS settings inspected on the Lab PC, not an unknown type.
    for key in ("loddy", "i_nln", "t1", "tpf", "tqf", "tpu", "tqu", "kpf", "kqf"):
        check(original_values[key], 0, "inspected source " + key)
    for suffix in ("P", "Q"):
        check(sum(original_values[p + suffix] for p in ("a", "b", "c")), 1, "coefficient sum")
    original_grids, scenario = active_grids(app), name(app.GetActiveScenario())
    net_folder, case_folder = app.GetProjectFolder("netdat"), app.GetProjectFolder("study")
    if net_folder is None or case_folder is None:
        raise RuntimeError("Existing Network Data / Study Cases folder missing")
    tag = "MCP ZIP RMS " + uuid.uuid4().hex[:8]
    report.update(test_name=tag, source_type=name(original_type), original_type=original_values,
                  original_study_case=name(original_case), original_active_grids=original_grids,
                  original_scenario=scenario, nominal_frequency_hz=50,
                  p0_mw=P0, q0_mvar=Q0, time_step_s=DT, stop_s=STOP,
                  power_relative_tolerance=POWER_REL, power_absolute_tolerance=POWER_ABS)
    created = []

    def create(parent, cls, label):
        obj = parent.CreateObject(cls, label)
        if obj is None:
            raise RuntimeError(f"Cannot create {cls} {label}")
        return obj

    def cubicle(bus, label):
        cub = create(bus, "StaCubic", label)
        switch = create(cub, "StaSwitch", "Switch")
        set_values(switch, {"aUsage": "cbk", "on_off": 1})
        return cub

    def isolated_command(cls):
        obj = app.GetFromStudyCase(cls)
        if obj is None or not name(obj).startswith(name(case) + "\\"):
            raise RuntimeError(f"{cls} not owned by the temporary case")
        return obj

    def isolation():
        if active_grids(app) != [name(grid)] or name(app.GetActiveStudyCase()) != name(case):
            raise RuntimeError("Temporary network/case isolation failed")

    try:
        case = create(case_folder, "IntCase", tag)
        created.append(case)
        command(case, "Activate")
        if name(app.GetActiveStudyCase()) != name(case):
            raise RuntimeError("Temporary case not activated")
        for other in physical_grids(app):
            command(other, "Deactivate")
        if app.GetActiveScenario() is not None:
            raise RuntimeError("Unexpected scenario in temporary case")
        grid = create(net_folder, "ElmNet", tag)
        created.append(grid)
        set_values(grid, {"frnom": 50.})
        command(grid, "Activate")
        isolation()
        sending, receiving = [create(grid, "ElmTerm", label) for label in ("Slack 20", "ZIP 20")]
        for bus in (sending, receiving):
            if str(bus.GetAttributeUnit("uknom")).strip() != "kV":
                raise RuntimeError("Expected kV bus units")
            set_values(bus, {"uknom": 20., "outserv": 0})
        source = create(grid, "ElmXnet", "Diagnostic slack")
        set_values(source, {"bus1": cubicle(sending, "Slack cubicle"), "bustp": "SL",
                            "usetp": 1., "outserv": 0, "snss": 1000., "rntxn": .1})
        line_type = create(original_type.GetParent().GetParent(), "TypLne", tag + " feeder")
        created.append(line_type)
        for field in ("rline", "xline"):
            if str(line_type.GetAttributeUnit(field)).strip().lower() != "ohm/km":
                raise RuntimeError("Expected feeder resistance/reactance units Ohm/km")
        # Engineering diagnostic impedance, not an EvEMTBench sampled line.
        set_values(line_type, {"uline": 20., "frnom": 50., "sline": 1.,
                               "rline": 10., "xline": 40., "cline": 0.,
                               "rline0": 10., "xline0": 40., "cline0": 0.})
        report["diagnostic_feeder"] = dict(parallel_branches=2, length_km_each=1,
                                            r_ohm_per_km=10, x_ohm_per_km=40,
                                            capacitance_uf_per_km=0)
        lines = []
        for i in range(2):
            line = create(grid, "ElmLne", "Feeder " + str(i + 1))
            if str(line.GetAttributeUnit("dline")).strip().lower() != "km":
                raise RuntimeError("Expected feeder length units km")
            set_values(line, {"typ_id": line_type, "bus1": cubicle(sending, "Feeder S " + str(i)),
                              "bus2": cubicle(receiving, "Feeder R " + str(i)),
                              "dline": 1., "outserv": 0})
            lines.append(line)
        typ = original_type.GetParent().AddCopy(original_type, tag)
        if typ is None:
            raise RuntimeError("Could not copy inspected ZIP type")
        created.append(typ)
        if name(typ) != name(original_type.GetParent()) + "\\" + tag + ".TypLod":
            raise RuntimeError("Unexpected temporary type identity")
        if mode != "creator_unchanged":
            set_values(typ, dict(loddy=100, i_nln=1, t1=0., tpf=0., tqf=0.,
                                 tpu=0., tqu=0., kpf=0., kqf=0.))
        if mode == "constant_power_control":
            set_values(typ, dict(aP=1., bP=0., aQ=1., bQ=0.))
        typ.WriteChangesToDb()
        retained = snapshot(typ)
        if mode == "creator_unchanged":
            for key, value in original_values.items():
                check(retained[key], value, "creator copy " + key)
        else:
            for key, value in dict(loddy=100, i_nln=1, t1=0, tpf=0, tqf=0,
                                   tpu=0, tqu=0, kpf=0, kqf=0).items():
                check(retained[key], value, "RMS diagnostic " + key)
            for key, value in expected_exp.items():
                check(retained[key], value, "RMS diagnostic " + key)
            for key in ("aP", "bP", "cP", "aQ", "bQ", "cQ"):
                expected = (original_values[key] if mode == "nonlinear_zip"
                            else 1 if key in ("aP", "aQ") else 0)
                check(retained[key], expected, "RMS diagnostic " + key)
        report["retained_type"] = retained
        load = create(grid, "ElmLod", "Diagnostic load")
        for field, unit in (("plini", "mw"), ("qlini", "mvar")):
            if str(load.GetAttributeUnit(field)).strip().lower() != unit:
                raise RuntimeError("Unexpected input power units")
        set_values(load, {"typ_id": typ, "bus1": cubicle(receiving, "Load cubicle"),
                          "plini": P0, "qlini": Q0, "scale0": 1., "outserv": 0})
        ldf = isolated_command("ComLdf")
        if "voltage" not in str(ldf.GetAttributeDescription("iopt_pq")).lower():
            raise RuntimeError("Cannot identify load-flow voltage-dependency option")
        set_values(ldf, {"iopt_net": 0, "iopt_pq": 1, "iopt_at": 0})
        isolation()
        command(ldf, "Execute")
        pvar, qvar = "m:P:bus1", "m:Q:bus1"
        for obj, field, unit in ((receiving, "m:u", "p.u."),
                                 (load, pvar, "mw"), (load, qvar, "mvar")):
            if str(obj.GetAttributeUnit(field)).strip().lower() != unit:
                raise RuntimeError("Unexpected LF result units: " + field)
        lf = dict(u_pu=float(receiving.GetAttribute("m:u")),
                  p_mw=float(load.GetAttribute(pvar)), q_mvar=float(load.GetAttribute(qvar)))
        if not all(math.isfinite(value) for value in lf.values()):
            raise RuntimeError("Non-finite load-flow result")
        report["loadflow"] = lf
        ep, eq = zip_power(lf["u_pu"], retained)
        if not power_close(lf["p_mw"], lf["q_mvar"], ep, eq):
            raise RuntimeError("Load-flow polynomial control failed")
        events = create(case, "IntEvt", "ZIP RMS events")
        for label, time, state in (("Dip", 1., 0), ("Recovery", 3., 1)):
            event = create(events, "EvtSwitch", label)
            set_values(event, {"p_target": lines[1], "time": time, "i_switch": state})
        result = create(case, "ElmRes", "ZIP RMS trace")
        inc, sim = isolated_command("ComInc"), isolated_command("ComSim")
        set_values(inc, {"iopt_sim": "rms", "iopt_net": "sym", "iopt_show": 0,
                         "iopt_adapt": 0, "dtgrd": DT, "tstart": 0.,
                         "p_event": events, "p_resvar": result})
        set_values(sim, {"tstop": STOP})
        command(result, "Clear")
        # Prefer phase-summed RMS powers; reject absent/unreadable channels.
        chosen = None
        registration = []
        for pv, qv in (("m:Psum:bus1", "m:Qsum:bus1"), ("m:P:bus1", "m:Q:bus1")):
            try:
                pu, qu = (str(load.GetAttributeUnit(v)).strip().lower() for v in (pv, qv))
                if (pu, qu) != ("mw", "mvar"):
                    raise RuntimeError(f"Unexpected units: {pu}, {qu}")
                pc, qc = result.AddVariable(load, pv), result.AddVariable(load, qv)
                registration.append(dict(p=pv, q=qv, p_code=pc, q_code=qc))
                if pc in (None, 0) and qc in (None, 0):
                    chosen = pv, qv
                    break
            except Exception as exc:
                registration.append(dict(p=pv, q=qv, error=str(exc)))
        report["result_channel_registration"] = registration
        if chosen is None:
            raise RuntimeError("No supported RMS power channels identified")
        code = result.AddVariable(receiving, "m:u")
        if code not in (None, 0):
            raise RuntimeError("Could not register receiving voltage")
        report["rms_channels"] = dict(voltage="m:u", p=chosen[0], q=chosen[1],
                                       units=["p.u.", "MW", "Mvar"])
        isolation()
        command(inc, "Execute")
        command(sim, "Execute")
        report["trace"] = read_series(result, receiving, load, *chosen)
        report["analysis"] = analyze(report["trace"], retained, mode, lf)
        report["success"] = (report["analysis"]["experiment_valid"]
                             and report["analysis"]["control_passed"] is not False)
        if not report["success"]:
            report["error"] = "Nonlinear ZIP or constant-power control did not match; inspect full trace"
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        errors = []
        try:
            command(original_case, "Activate")
            if (name(app.GetActiveStudyCase()) != name(original_case)
                    or active_grids(app) != original_grids
                    or name(app.GetActiveScenario()) != scenario):
                raise RuntimeError("Original context mismatch")
            for key, value in original_values.items():
                check(original_type.GetAttribute(key), value, "original " + key)
            report["restored"] = True
        except Exception as exc:
            errors.append("Restoration: " + str(exc))
        if report["restored"]:
            for obj in created:
                path = name(obj)
                try:
                    command(obj, "Delete")
                    if any(name(o) == path for o in (project.GetContents("*", 1) or [])):
                        raise RuntimeError("Object still present after deletion")
                except Exception as exc:
                    report["remaining_objects"].append(path)
                    errors.append("Cleanup " + path + ": " + str(exc))
        else:
            report["remaining_objects"] = [name(o) for o in created]
        report["cleanup_ok"] = report["restored"] and not report["remaining_objects"] and not errors
        if errors:
            report["restoration_or_cleanup_errors"] = errors
        report["success"] = report["success"] and report["restored"] and report["cleanup_ok"]
    return report


def validate(app):
    report = dict(success=False, scope="Balanced 50 Hz isolated RMS ZIP settled-voltage diagnostic",
                  runs=[], restored=False, cleanup_ok=False, remaining_objects=[],
                  creator_rms_zip_validated=False,
                  limitations=["Diagnostic settings and feeder values are not paper-derived dynamic parameters.",
                               "Settled response only; no recovery-dynamics, EMT or frequency-response validation.",
                               "No existing type/load changes; no creator implementation changes."])
    for mode in MODES:
        try:
            run = validate_case(app, mode)
        except Exception as exc:
            run = dict(mode=mode, success=False, error=str(exc), restored=False,
                       cleanup_ok=False, remaining_objects=[])
        report["runs"].append(run)
        if not run.get("success") and not (
                run.get("restored") and run.get("cleanup_ok")
                and run.get("analysis", {}).get("experiment_valid")):
            report["error"] = mode + " did not complete; later modes not run"
            break
    report["restored"] = all(r.get("restored", False) for r in report["runs"])
    report["cleanup_ok"] = all(r.get("cleanup_ok", False) for r in report["runs"])
    report["remaining_objects"] = [p for r in report["runs"] for p in r.get("remaining_objects", [])]
    report["success"] = len(report["runs"]) == 3 and all(r.get("success") for r in report["runs"])
    if len(report["runs"]) == 3 and not report["success"]:
        report["error"] = "At least one configured control failed; see all three recorded cases"
    report["creator_rms_zip_validated"] = bool(
        report["success"] and report["runs"][0]["analysis"]["matches_zip"])
    report["success_meaning"] = "Diagnostic and configured controls passed; not a claim that creator defaults implement RMS ZIP."
    return report


def run_and_save(app, path):
    # Exclusive open before simulation catches destination errors before writes.
    with path.open("x", encoding="utf-8") as stream:
        report = validate(app)
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return report


def main():
    import powerfactory
    app = powerfactory.GetApplication()
    if app is None:
        raise RuntimeError("Use interactive ComPython with MCP stopped")
    try:
        folder = Path(__file__).resolve().parent / "lab_results"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = folder / f"ZIP_RMS_{stamp}_{uuid.uuid4().hex[:8]}.json"
        report = run_and_save(app, path)
    except Exception as exc:
        app.PrintPlain("ZIP_RMS_EXPORT_ERROR: " + str(exc))
        app.PrintPlain("No complete export confirmed; do not treat this run as passed.")
        return
    app.PrintPlain("ZIP_RMS_DIAGNOSTIC_RESULT_FILE")
    app.PrintPlain(str(path))
    app.PrintPlain(json.dumps({k: report[k] for k in
                              ("success", "creator_rms_zip_validated", "restored", "cleanup_ok", "remaining_objects")}))
    app.PrintPlain("Attach the complete JSON file. No creator settings were changed.")


if __name__ == "__main__":
    main()
