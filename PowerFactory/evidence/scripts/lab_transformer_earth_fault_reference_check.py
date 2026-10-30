"""Run as ComPython inside interactive PowerFactory; stop MCP first.

Temporary, lossless YNd network only. Independently calculates sequence-network
fault-current magnitudes from input impedances, not solver fault-current results.
Uses the earlier sensitivity test safeguards; not core/limb modelling or RMS/EMT.
Existing calculation results can be invalidated; no original network is rerun.
"""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Replace <user> with the Lab PC PowerFactory account before executing.
PROJECT = "\\<user>.IntUser\\test.IntPrj"
SOURCE = "EvEMTBench Test Type 110-20"
METHOD_TEMPLATE = "MCP Complete Method Template"
FIELDS = ("pfe", "curmg", "nntap0", "strn", "frnom", "utrn_h", "utrn_l", "tr2cn_h", "tr2cn_l", "nt2ag",
          "it0mt", "r1pu", "x1pu", "r0pu", "x0pu", "ur0tr", "uk0tr")
REL_TOL, ABS_TOL = 1e-6, 1e-6
CURRENT_REL_TOL, CURRENT_ABS_TOL_KA = 0.005, 1e-5

def name(obj):
    return None if obj is None else obj.GetFullName()


def network_grids(app):
    # GetCalcRelevantObjects also returns a case-owned Summary Grid (ElmNet).
    # Only actual networks below Network Data can be activated/deactivated.
    folder = app.GetProjectFolder("netdat")
    if folder is None:
        raise RuntimeError("Network Data folder not found")
    prefix = name(folder) + "\\"
    return [obj for obj in (app.GetCalcRelevantObjects("*.ElmNet") or [])
            if name(obj).startswith(prefix)]


def active_grids(app):
    return sorted(name(obj) for obj in network_grids(app))


def require_close(actual, expected, label, rel=REL_TOL, absolute=ABS_TOL):
    if not math.isclose(actual, expected, rel_tol=rel, abs_tol=absolute):
        raise RuntimeError(f"{label}: expected {expected}, actual {actual}")


def set_values(obj, values):
    for key, expected in values.items():
        setattr(obj, key, expected)
        actual = obj.GetAttribute(key)
        if isinstance(expected, (float, int)):
            require_close(float(actual), expected, key, rel=1e-6, absolute=1e-6)
        elif isinstance(expected, str):
            if actual != expected:
                raise RuntimeError(f"{key} was not retained: {actual}")
        elif name(actual) != name(expected):
            raise RuntimeError(f"{key} reference was not retained")


def command(obj, method):
    code = getattr(obj, method)()
    if code not in (None, 0):
        raise RuntimeError(f"{name(obj)}.{method} returned {code}")



def snapshot(obj):
    return {key: obj.GetAttribute(key) for key in FIELDS}


def read_ka(obj, key):
    unit = str(obj.GetAttributeUnit(key)).strip()
    if unit != "kA":
        raise RuntimeError(f"{name(obj)} {key}: expected kA, found {unit!r}")
    value = abs(float(obj.GetAttribute(key)))
    if not math.isfinite(value):
        raise RuntimeError(f"{key} is not finite")
    return value


def check_row(ik3, ikg, i0h, i0l):
    if min(ik3, ikg, i0h) <= 1e-6:
        raise RuntimeError("Fault current or star-side I0 is zero; test topology/results need inspection")
    require_close(3 * i0h, ikg, "3*I0(HV) versus ground-fault current", rel=0.005, absolute=1e-5)
    if i0l > max(1e-5, i0h * 1e-3):
        raise RuntimeError("Delta-side terminal I0 is not blocked")


def check_sensitivity(rows):
    if len(rows) != 4:
        raise RuntimeError("Expected all four scenarios")
    base = rows[0]
    for row in rows[1:]:
        require_close(row["three_phase_ka"], base["three_phase_ka"],
                      "three-phase control", rel=0.005, absolute=1e-5)
        if row["earth_fault_ka"] >= base["earth_fault_ka"] * 0.999:
            raise RuntimeError(f'{row["label"]}: earth-fault current did not decrease measurably')


def reference_currents(sn_mva, hv_kv, source_sk_mva, source_rx,
                       r1pu, x1pu, r0pu, x0pu, rn_ohm=0.0, xn_ohm=0.0):
    """All sequence impedances on transformer MVA / HV kV base; kV/ohm = kA.

    Source c=1 and Z2=Z1; transformer Z2=Z1. The delta blocks the
    external source's Z0 from the HV zero-sequence network.
    """
    inputs = (sn_mva, hv_kv, source_sk_mva, source_rx, r1pu, x1pu,
              r0pu, x0pu, rn_ohm, xn_ohm)
    if not all(math.isfinite(float(v)) for v in inputs):
        raise ValueError("Non-finite analytical input")
    if min(sn_mva, hv_kv, source_sk_mva) <= 0 or min(inputs[3:]) < 0:
        raise ValueError("Non-positive base or negative impedance input")
    zb = hv_kv ** 2 / sn_mva
    ib = sn_mva / (math.sqrt(3) * hv_kv)
    source_x = (sn_mva / source_sk_mva) / math.sqrt(1 + source_rx ** 2)
    source_z = complex(source_rx * source_x, source_x)
    z1 = source_z + complex(r1pu, x1pu)
    z2 = z1
    z0 = complex(r0pu, x0pu) + 3 * complex(rn_ohm, xn_ohm) / zb
    if abs(z1) == 0 or abs(z1 + z2 + z0) == 0:
        raise ValueError("Zero analytical fault-loop impedance")
    def pair(z):
        return {"real": z.real, "imag": z.imag}
    return {
        "three_phase_ka": ib / abs(z1),
        "earth_fault_ka": 3 * ib / abs(z1 + z2 + z0),
        "hv_terminal_I0_ka": ib / abs(z1 + z2 + z0),
        "lv_terminal_I0_ka": 0.0,
        "hv_impedance_base_ohm": zb, "hv_current_base_ka": ib,
        "source_Z1_pu": pair(source_z),
        "Z1_pu": pair(z1), "Z2_pu": pair(z2), "Z0_pu": pair(z0),
    }


def configure_reference_source(source):
    # Candidate names are probed read-only; write only fields whose live
    # metadata identifies a c-factor. Do not guess an unseen enum or attribute.
    factors = {}
    for key in ("c", "cfac", "cfactor", "c_factor", "cmax", "cmin"):
        try:
            description = str(source.GetAttributeDescription(key))
            value = source.GetAttribute(key)
        except Exception:
            continue
        normalized = description.casefold().replace("-", "").replace(" ", "")
        if "factor" not in normalized or "c" not in normalized:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        factors[key] = {"description": description, "before": value}
    if not factors:
        raise RuntimeError("No c-factor identified from external-grid metadata; "
                           "stop and inspect its Complete page; no fault calculation run")
    set_values(source, {key: 1.0 for key in factors})
    # Set both max/min data alike so no inherited maximum/minimum choice
    # changes the test's source sequence impedance.
    set_values(source, {"snss": 1000.0, "snssmin": 1000.0,
                        "rntxn": 0.1, "rntxnmin": 0.1,
                        "z2tz1": 1.0})
    for key in factors:
        factors[key]["retained"] = source.GetAttribute(key)
    return factors


def compare_reference(row, predicted):
    row["reference"] = predicted
    row["relative_errors"] = {}
    checks = []
    for key in ("three_phase_ka", "earth_fault_ka", "hv_terminal_I0_ka"):
        measured, expected = row[key], predicted[key]
        row["relative_errors"][key] = abs(measured - expected) / abs(expected)
        checks.append(math.isclose(measured, expected, rel_tol=CURRENT_REL_TOL,
                                   abs_tol=CURRENT_ABS_TOL_KA))
    checks.append(abs(row["lv_terminal_I0_ka"]) <= CURRENT_ABS_TOL_KA)
    row["absolute_reference_passed"] = all(checks)
    return all(checks)


def validate(app):
    report = dict(success=False, scope="YNd11 lossless sequence-network absolute current reference",
                  rows=[], restored=False, cleanup_ok=False, remaining_objects=[],
                  limitations=["Restricted lossless, unloaded network; not an absolute-current certification of the original lossy type.",
                               "No core/limb, internal-delta YNyn, RMS or EMT validation.",
                               "Perturbed impedances are diagnostic controls, not Table 10 samples."])
    project, original_case = app.GetActiveProject(), app.GetActiveStudyCase()
    if name(project) != PROJECT or name(original_case) != PROJECT + "\\Study Cases.IntPrjfolder\\Case 1.IntCase":
        raise RuntimeError("Activate test and Case 1 before running this script")
    # The operator selected 'complete' on this dedicated template in the GUI.
    # Read its enum directly: metadata may only say 'Method' with no choices.
    templates = original_case.GetContents(METHOD_TEMPLATE + ".ComShc", 0) or []
    if len(templates) != 1:
        raise RuntimeError("Expected one MCP Complete Method Template in the active study case; no test objects created")
    method_template = templates[0]
    if (method_template.GetClassName() != "ComShc"
            or name(method_template) != name(original_case) + "\\" + METHOD_TEMPLATE + ".ComShc"):
        raise RuntimeError("Unexpected method template location; no test objects created")
    method_code = method_template.GetAttribute("iopt_mde")
    if isinstance(method_code, bool) or not isinstance(method_code, int) or method_code != 3:
        raise RuntimeError("Dedicated template no longer has the Lab-validated Complete Method code 3; no test objects created")
    report.update(method_template=name(method_template), method_code=method_code,
                  method_selection_basis="operator selected complete on dedicated GUI template; enum read directly")
    originals = project.GetContents(SOURCE + ".TypTr2", 1) or []
    if len(originals) != 1:
        raise RuntimeError("Expected exactly one inspected source transformer type")
    source_type = originals[0]
    expected_source = (PROJECT + "\\Library.IntPrjfolder\\Equipment Type Library.IntPrjfolder"
                       "\\Transformer Types.IntPrjfolder\\" + SOURCE + ".TypTr2")
    if name(source_type) != expected_source:
        raise RuntimeError("Source type is not in the expected library")
    original_type = snapshot(source_type)
    for key, expected in dict(strn=20.0, frnom=60.0, utrn_h=110.0, utrn_l=20.0).items():
        require_close(float(original_type[key]), expected, key)
    require_close(float(original_type["nt2ag"]), 11.0, "source clock number")
    if (original_type["tr2cn_h"], original_type["tr2cn_l"]) != ("YN", "D"):
        raise RuntimeError("Expected YN/D windings")
    original_grids, original_scenario = active_grids(app), name(app.GetActiveScenario())
    net_folder, case_folder = app.GetProjectFolder("netdat"), app.GetProjectFolder("study")
    if net_folder is None or case_folder is None:
        raise RuntimeError("Network Data/Study Cases folder missing")
    tag = "MCP YNd Reference " + uuid.uuid4().hex[:8]
    report.update(test_name=tag, original_study_case=name(original_case),
                  original_active_grids=original_grids, original_scenario=original_scenario,
                  source_type=name(source_type), original_type=original_type)
    created = []

    def create(parent, cls, label):
        obj = parent.CreateObject(cls, label)
        if obj is None:
            raise RuntimeError(f"Could not create {cls} {label}")
        return obj

    def cubicle(bus, label):
        cub = create(bus, "StaCubic", label)
        switch = create(cub, "StaSwitch", "Switch")
        set_values(switch, {"aUsage": "cbk", "on_off": 1})
        return cub

    def fault(shc, ldf, grid, hv, transformer, kind):
        if active_grids(app) != [name(grid)]:
            raise RuntimeError("Isolation failed: another physical network is active")
        command(ldf, "Execute")
        set_values(shc, {"iopt_shc": kind})
        command(shc, "Execute")
        return read_ka(hv, "m:Ikss")

    try:
        case = create(case_folder, "IntCase", tag)
        created.append(case)
        command(case, "Activate")
        if name(app.GetActiveStudyCase()) != name(case):
            raise RuntimeError("Temporary study case activation failed")
        for other in network_grids(app):
            command(other, "Deactivate")
        if app.GetActiveScenario() is not None:
            raise RuntimeError("Temporary case unexpectedly has an active scenario")
        grid = create(net_folder, "ElmNet", tag)
        created.append(grid)
        set_values(grid, {"frnom": 60.0})
        command(grid, "Activate")
        if active_grids(app) != [name(grid)]:
            raise RuntimeError("Could not isolate temporary network")
        hv, lv = (create(grid, "ElmTerm", label) for label in ("HV Star 110", "LV Delta 20"))
        for bus, voltage in ((hv, 110.0), (lv, 20.0)):
            if bus.GetAttributeUnit("uknom").strip() != "kV":
                raise RuntimeError("Expected nominal voltages in kV")
            set_values(bus, {"uknom": voltage, "outserv": 0})
        typ = source_type.GetParent().AddCopy(source_type, tag)
        if typ is None:
            raise RuntimeError("Could not copy source type")
        created.append(typ)
        if name(typ) != name(source_type.GetParent()) + "\\" + tag + ".TypTr2":
            raise RuntimeError("Unexpected copy identity; no type writes attempted")
        if typ.GetClassName() != "TypTr2":
            raise RuntimeError("Unexpected copied class")
        set_values(typ, {"pfe": 0.0, "curmg": 0.0})
        typ.WriteChangesToDb()
        require_close(float(typ.GetAttribute("pfe")), 0.0, "temporary core losses")
        require_close(float(typ.GetAttribute("curmg")), 0.0, "temporary no-load current")
        source = create(grid, "ElmXnet", "LV Test Supply")
        if source.GetAttributeUnit("snss").strip() != "MVA":
            raise RuntimeError("Expected source short-circuit power units MVA")
        set_values(source, {"bus1": cubicle(lv, "Supply Cubicle"), "bustp": "SL",
                            "usetp": 1.0, "outserv": 0, "snss": 1000.0,
                            "rntxn": 0.1, "x0tx1": 1.0, "r0tx0": 0.1})
        report["source_c_factors"] = configure_reference_source(source)
        transformer = create(grid, "ElmTr2", "YNd Test Transformer")
        for key in ("re0tr_h", "xe0tr_h"):
            if transformer.GetAttributeUnit(key).strip().casefold() != "ohm":
                raise RuntimeError(f"Expected {key} units Ohm")
        set_values(transformer, {"typ_id": typ, "bushv": cubicle(hv, "HV Cubicle"),
                                 "buslv": cubicle(lv, "LV Cubicle"), "outserv": 0,
                                 "neutConfig": 0, "cgnd_h": 0, "re0tr_h": 0.0,
                                 "xe0tr_h": 0.0,
                                 "nntap": typ.GetAttribute("nntap0")})
        ldf = create(case, "ComLdf", "Fault Prefault Load Flow")
        set_values(ldf, {"iopt_net": 0, "iopt_at": 0})
        shc = create(case, "ComShc", "Isolated YNd Fault")
        method_description = str(shc.GetAttributeDescription("iopt_mde"))
        report["method_description"] = method_description
        set_values(shc, {"iopt_mde": method_code, "iopt_allbus": 0,
                         "shcobj": hv, "Rf": 0.0, "Xf": 0.0})
        report["fault_command"] = {"method_code": method_code, "fault_bus": name(hv),
                                    "faults": ["3psc", "spgf"], "Rf_ohm": 0.0, "Xf_ohm": 0.0}
        report["source_inputs"] = {key: source.GetAttribute(key) for key
                                   in ("snss", "rntxn", "x0tx1", "r0tx0", "usetp")}

        report["reference_assumptions"] = {
            "prefault_voltage_pu": 1.0, "source_c_factor": 1.0,
            "source_Z2_equals_Z1": True, "transformer_Z2_equals_Z1": True,
            "source_Z0_excluded_by_delta": True, "temporary_pfe_kw": 0.0,
            "temporary_curmg_pct": 0.0, "fault_impedance_ohm": 0.0,
            "current_relative_tolerance": CURRENT_REL_TOL,
            "current_absolute_tolerance_ka": CURRENT_ABS_TOL_KA,
            "formula_3ph": "Ibase / abs(Z1)",
            "formula_slg": "3 * Ibase / abs(Z1 + Z2 + Z0)",
            "formula_Z0": "R0pu + jX0pu + 3*(Rn+jXn)/Zbase",
        }
        # Independent source-only control. Never use the measured current to
        # tune c, Sk, R/X or any transformer input.
        set_values(transformer, {"outserv": 1})
        set_values(shc, {"shcobj": lv, "iopt_shc": "3psc"})
        if active_grids(app) != [name(grid)]:
            raise RuntimeError("Source-only control is not isolated")
        command(ldf, "Execute")
        command(shc, "Execute")
        source_expected = 1000.0 / (math.sqrt(3) * 20.0)
        source_measured = read_ka(lv, "m:Ikss")
        report["source_only_control"] = {
            "expected_ka": source_expected, "measured_ka": source_measured,
            "passed": math.isclose(source_measured, source_expected,
                                  rel_tol=CURRENT_REL_TOL,
                                  abs_tol=CURRENT_ABS_TOL_KA)}
        if not report["source_only_control"]["passed"]:
            raise RuntimeError("Source-only reference failed; inspect c-factor / Complete "
                               "Method settings, not transformer ratios")
        set_values(transformer, {"outserv": 0})
        set_values(shc, {"shcobj": hv})
        r0base = float(original_type["r1pu"]) * 2.15
        x0base = float(original_type["x1pu"]) * 0.925
        scenarios = (("baseline", 1.0, 1.0, 0.0), ("higher_R0", 10.0, 1.0, 0.0),
                     ("higher_X0", 1.0, 2.0, 0.0), ("neutral_resistance", 1.0, 1.0, 20.0))
        for label, rscale, xscale, rn in scenarios:
            set_values(typ, {"r0pu": r0base * rscale, "x0pu": x0base * xscale})
            typ.WriteChangesToDb()
            for key, value in (("r0pu", r0base * rscale), ("x0pu", x0base * xscale)):
                require_close(float(typ.GetAttribute(key)), value, key)
            set_values(transformer, {"re0tr_h": rn})

            command(ldf, "Execute")
            if str(hv.GetAttributeUnit("m:u")).strip() != "p.u.":
                raise RuntimeError("Expected m:u unit p.u.")
            prefault_u = float(hv.GetAttribute("m:u"))
            require_close(prefault_u, 1.0, "unloaded HV prefault voltage",
                          rel=1e-5, absolute=1e-5)
            predicted = reference_currents(
                float(typ.GetAttribute("strn")), float(typ.GetAttribute("utrn_h")),
                float(source.GetAttribute("snss")), float(source.GetAttribute("rntxn")),
                float(typ.GetAttribute("r1pu")), float(typ.GetAttribute("x1pu")),
                float(typ.GetAttribute("r0pu")), float(typ.GetAttribute("x0pu")),
                float(transformer.GetAttribute("re0tr_h")),
                float(transformer.GetAttribute("xe0tr_h")))
            ik3 = fault(shc, ldf, grid, hv, transformer, "3psc")
            ikg = fault(shc, ldf, grid, hv, transformer, "spgf")
            row = dict(label=label, three_phase_ka=ik3, earth_fault_ka=ikg,
                       retained_r0pu=typ.GetAttribute("r0pu"), retained_x0pu=typ.GetAttribute("x0pu"),
                       neutral_resistance_ohm=transformer.GetAttribute("re0tr_h"), passed=False)
            report["rows"].append(row)
            i0h = read_ka(transformer, "m:I0:bushv")
            i0l = read_ka(transformer, "m:I0:buslv")
            row.update(hv_terminal_I0_ka=i0h, lv_terminal_I0_ka=i0l)
            check_row(ik3, ikg, i0h, i0l)
            row["prefault_voltage_pu"] = prefault_u
            row["passed"] = compare_reference(row, predicted)
        check_sensitivity(report["rows"])
        report["success"] = all(row["passed"] for row in report["rows"])
        if not report["success"]:
            report["error"] = "Absolute current mismatch; retain reported inputs and investigate, do not fit the reference"
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        errors = []
        try:
            command(original_case, "Activate")
            if (name(app.GetActiveStudyCase()) != name(original_case)
                    or active_grids(app) != original_grids
                    or name(app.GetActiveScenario()) != original_scenario):
                raise RuntimeError("Original case/grid/scenario selection changed")
            for key, value in original_type.items():
                actual = source_type.GetAttribute(key)
                if isinstance(value, (int, float)):
                    require_close(float(actual), float(value), f"original {key}")
                elif actual != value:
                    raise RuntimeError(f"Original {key} changed")
            if method_template.GetAttribute("iopt_mde") != method_code:
                raise RuntimeError("Original template method value changed")
            report["method_template_unchanged"] = True
            report["restored"] = True
        except Exception as exc:
            errors.append(f"Restoration: {exc}")
        if report["restored"]:
            for obj in created:
                path = name(obj)
                try:
                    command(obj, "Delete")
                    if any(name(item) == path for item in project.GetContents("*", 1) or []):
                        raise RuntimeError("Object still exists")
                except Exception as exc:
                    report["remaining_objects"].append(path)
                    errors.append(f"Cleanup {path}: {exc}")
        else:
            report["remaining_objects"] = [name(obj) for obj in created]
        report["cleanup_ok"] = report["restored"] and not report["remaining_objects"]
        if errors:
            report["restoration_or_cleanup_errors"] = errors
        report["success"] = report["success"] and report["restored"] and report["cleanup_ok"] and not errors
    return report


def run_and_save(app, output_path):
    # Open before validation: an unwritable destination must not trigger a test.
    # Exclusive creation preserves every earlier run's evidence.
    with output_path.open("x", encoding="utf-8") as stream:
        try:
            result = validate(app)
        except Exception as exc:
            result = dict(success=False, error=str(exc))
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return result


def main():
    import powerfactory

    app = powerfactory.GetApplication()
    if app is None:
        raise RuntimeError("Run inside interactive PowerFactory with MCP stopped")
    try:
        folder = Path(__file__).resolve().parent / "lab_results"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = folder / f"YNd_reference_{stamp}_{uuid.uuid4().hex[:8]}.json"
        result = run_and_save(app, output)
    except Exception as exc:
        app.PrintPlain("TRANSFORMER_EARTH_FAULT_REFERENCE_EXPORT_ERROR")
        app.PrintPlain(str(exc))
        app.PrintPlain("No complete JSON export confirmed. Do not treat this run as passed.")
        return
    # Keep each Output Window message short; full evidence is in the file.
    app.PrintPlain("TRANSFORMER_EARTH_FAULT_REFERENCE_RESULT_FILE")
    app.PrintPlain(str(output))
    summary = {key: result.get(key) for key in
               ("success", "restored", "cleanup_ok", "remaining_objects")}
    app.PrintPlain(json.dumps(summary))
    app.PrintPlain("Attach the JSON file, not a copied Output Window transcript.")


if __name__ == "__main__":
    main()
