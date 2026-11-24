"""Staged MCP creation -> interactive RMS test. Read 0127 instructions first.

Keep lab_zip_rms_multiseed_check.py beside this file. Never run with MCP active.
Only PHASE is operator-selected: prepare, run, or cleanup.
"""
import copy
import hashlib
import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import lab_zip_rms_multiseed_check as h

PHASE = "prepare"
HOME = Path(__file__).resolve().parent
STATE = HOME / "lab_results/ZIP_RMS_E2E_state.json"
CAPTURE = HOME / "lab_results/ZIP_RMS_E2E_capture.json"


def save_state(state):
    temporary = STATE.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, STATE)


def exact(project, path, cls):
    matches = [o for o in (project.GetContents("*." + cls, 1) or []) if h.name(o) == path]
    if len(matches) != 1:
        raise RuntimeError("Expected one exact object: " + path)
    return matches[0]


def require_project(app):
    project = app.GetActiveProject()
    if h.name(project) != h.PROJECT:
        raise RuntimeError("Activate test; project path does not match")
    return project


def activate_case(app, case, expected_grid=None):
    before = h.name(app.GetActiveStudyCase())
    target = h.name(case)
    if before != target:
        h.command(case, "Activate")
    after = h.name(app.GetActiveStudyCase())
    if after != target:
        raise RuntimeError(f"Study-case activation mismatch: expected {target}, found {after}")
    if expected_grid is not None:
        if h.active_grids(app) != [expected_grid] or app.GetActiveScenario() is not None:
            raise RuntimeError("Simulation isolation failed after case activation check")
    return dict(before=before, target=target, after=after, activation_needed=before != target)


def restore(app, state):
    project = require_project(app)
    case = exact(project, state["original_case"], "IntCase")
    activate_case(app, case)
    if (h.name(app.GetActiveStudyCase()) != state["original_case"]
            or h.active_grids(app) != state["original_grids"]
            or h.name(app.GetActiveScenario()) != state["original_scenario"]):
        raise RuntimeError("Original context restoration mismatch; preserve temporary objects")


def prepare(app):
    project = require_project(app)
    case = app.GetActiveStudyCase()
    if h.name(case) != h.PROJECT + "\\Study Cases.IntPrjfolder\\Case 1.IntCase":
        raise RuntimeError("Activate Case 1 before preparing")
    if STATE.exists() or CAPTURE.exists():
        raise RuntimeError("Prior state/capture exists; do not overwrite. Review/archive the prior test first")
    equip = app.GetProjectFolder("equip")
    folders = [o for o in (equip.GetContents("*.IntPrjfolder", 1) or [])
               if o.GetAttribute("loc_name") == "Load Types"]
    if len(folders) != 1:
        raise RuntimeError("Requires one existing Load Types folder; no library folders will be created")
    plans, hashes = h.sampled_plans()
    plans = [next(p for p in plans if p["seed"] == seed) for seed in (0, 4)]
    tag = "MCP ZIP E2E " + uuid.uuid4().hex[:8]
    requests = []
    for seed in (0, 4):
        type_name = tag + " Type " + str(seed)
        if any(o.GetAttribute("loc_name") == type_name for o in (equip.GetContents("*.TypLod", 1) or [])):
            raise RuntimeError("Reserved type name exists")
        requests.append(dict(voltage_kv=20., seed=seed, load_model="zip_rms",
                             load_name=tag + " Load " + str(seed), type_name=type_name,
                             grid_name=tag, bus_name="Receiving 20", out_of_service=True,
                             open_digsilent=True))
    state = dict(schema=1, tag=tag, project=h.PROJECT, original_case=h.name(case),
                 original_grids=h.active_grids(app), original_scenario=h.name(app.GetActiveScenario()),
                 roots=[], requests=requests, plans=plans, sampler_sha256=hashes,
                 type_folder=h.name(folders[0]), ready=False, closed=False)
    STATE.parent.mkdir(exist_ok=True)
    with STATE.open("x", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)

    def create(parent, cls, label, root=False):
        obj = parent.CreateObject(cls, label)
        if obj is None:
            raise RuntimeError("Cannot create " + cls)
        if root:
            state["roots"].append(dict(path=h.name(obj), cls=cls))
            save_state(state)
        return obj

    def cub(bus, label):
        obj = create(bus, "StaCubic", label)
        switch = create(obj, "StaSwitch", "Switch")
        h.set_values(switch, dict(aUsage="cbk", on_off=1))
        return obj

    try:
        temp_case = create(app.GetProjectFolder("study"), "IntCase", tag, True)
        state["case"] = h.name(temp_case)
        save_state(state)
        activate_case(app, temp_case)
        for grid in h.physical_grids(app):
            h.command(grid, "Deactivate")
        if app.GetActiveScenario() is not None:
            raise RuntimeError("Unexpected active scenario in temporary case")
        grid = create(app.GetProjectFolder("netdat"), "ElmNet", tag, True)
        state["grid"] = h.name(grid)
        h.set_values(grid, dict(frnom=50.))
        h.command(grid, "Activate")
        if h.active_grids(app) != [h.name(grid)]:
            raise RuntimeError("Preparation isolation failed")
        buses = [create(grid, "ElmTerm", label) for label in ("Sending 20", "Receiving 20")]
        for bus in buses:
            if str(bus.GetAttributeUnit("uknom")).strip() != "kV":
                raise RuntimeError("Unexpected bus units")
            h.set_values(bus, dict(uknom=20., outserv=0))
        state["bus"] = h.name(buses[1])
        source = create(grid, "ElmXnet", "Diagnostic slack")
        h.set_values(source, dict(bus1=cub(buses[0], "Slack"), bustp="SL", usetp=1.,
                                  snss=1000., rntxn=.1, outserv=0))
        typ = create(equip, "TypLne", tag + " Feeder", True)
        for field in ("rline", "xline"):
            if str(typ.GetAttributeUnit(field)).strip().lower() != "ohm/km":
                raise RuntimeError("Unexpected feeder units")
        h.set_values(typ, dict(uline=20., frnom=50., sline=1., rline=30., xline=5.,
                               cline=0., rline0=30., xline0=5., cline0=0.))
        state["feeder_type"] = h.name(typ)
        state["lines"] = []
        for index in range(2):
            line = create(grid, "ElmLne", "Feeder " + str(index))
            if str(line.GetAttributeUnit("dline")).strip().lower() != "km":
                raise RuntimeError("Unexpected line units")
            h.set_values(line, dict(typ_id=typ, bus1=cub(buses[0], "S" + str(index)),
                                    bus2=cub(buses[1], "R" + str(index)), dline=1., outserv=0))
            state["lines"].append(h.name(line))
        state["ready"] = True
    except Exception as exc:
        state["preparation_error"] = str(exc)
        raise
    finally:
        save_state(state)
        restore(app, state)
    app.PrintPlain("ZIP_RMS_E2E_PREPARED: " + str(STATE))
    app.PrintPlain("Start MCP and use the supplied prompt. No load has been created yet.")
    return state


def check_capture(state, capture):
    if not isinstance(capture, dict) or set(capture) != {"0", "4"}:
        raise RuntimeError("Capture must contain exactly seed keys 0 and 4")
    for request, plan in zip(state["requests"], state["plans"]):
        pair = capture[str(request["seed"])]
        preview, creation = pair["preview"], pair["creation"]
        if not (preview.get("success") is True and preview.get("applied") is False
                and preview.get("load_created") is False and preview.get("type_created") is False):
            raise RuntimeError("Preview flags failed")
        if not all(creation.get(k) is True for k in ("success", "applied", "load_created", "type_created")):
            raise RuntimeError("Creation flags failed")
        if preview["confirmation_required"] != creation["confirmation_required"]:
            raise RuntimeError("Confirmation changed")
        if creation["created_load"] != state["grid"] + "\\" + request["load_name"] + ".ElmLod":
            raise RuntimeError("Unexpected created load identity")
        if creation["created_type"] != state["type_folder"] + "\\" + request["type_name"] + ".TypLod":
            raise RuntimeError("Unexpected created type identity")
        for response in (preview, creation):
            if response["load_model"] != "zip_rms" or response["seed"] != request["seed"]:
                raise RuntimeError("Unexpected model/seed")
            target = response["target"]
            if target["grid"] != state["grid"] or target["bus"] != state["bus"] or target["out_of_service"] is not True:
                raise RuntimeError("Unexpected target")
            item = response["item"]
            if item["resolved_grid_frequency_hz"] != 50:
                raise RuntimeError("Unexpected grid frequency")
            for group in ("powerfactory_attributes", "type_attributes", "derived_type_attributes"):
                if item[group] != plan[group]:
                    raise RuntimeError("Preview/creation plan differs from sampled plan: " + group)
    return capture


def simulate(app, state, request, creation):
    project = require_project(app)
    case = exact(project, state["case"], "IntCase")
    grid = exact(project, state["grid"], "ElmNet")
    bus = exact(project, state["bus"], "ElmTerm")
    load = exact(project, creation["created_load"], "ElmLod")
    typ = exact(project, creation["created_type"], "TypLod")
    activation = activate_case(app, case, state["grid"])
    h.check(grid.GetAttribute("frnom"), 50., "grid frequency")
    h.check(bus.GetAttribute("uknom"), 20., "bus voltage")
    if h.name(load.GetAttribute("typ_id")) != h.name(typ):
        raise RuntimeError("Load does not use the actual created type")
    cub = load.GetAttribute("bus1")
    if cub is None or h.name(cub.GetParent()) != state["bus"]:
        raise RuntimeError("Created load is not connected to the intended bus")
    retained = h.snapshot(typ)
    for key, expected in {**creation["item"]["type_attributes"],
                          **creation["item"]["derived_type_attributes"]}.items():
        h.check(retained[key], expected, "created " + key)
    p0, q0 = (float(load.GetAttribute(k)) for k in ("plini", "qlini"))
    if not math.isfinite(p0) or not math.isfinite(q0) or p0 <= 0 or (q0 > 0) != (request["seed"] == 0):
        raise RuntimeError("Invalid nominal power or unexpected Q sign")
    for key, expected in creation["item"]["powerfactory_attributes"].items():
        h.check(load.GetAttribute(key), expected, key)
    h.check(load.GetAttribute("scale0"), 1., "scale0")
    for field, unit in (("plini", "mw"), ("qlini", "mvar")):
        if str(load.GetAttributeUnit(field)).strip().lower() != unit:
            raise RuntimeError("Unexpected load input units")
    for other in (grid.GetContents("*.ElmLod", 1) or []):
        h.check(other.GetAttribute("outserv"), 1, "other load must remain out of service")
    feeder = exact(project, state["feeder_type"], "TypLne")
    h.set_values(feeder, dict(rline=30. / p0, xline=5. / p0,
                              rline0=30. / p0, xline0=5. / p0))
    lines = [exact(project, path, "ElmLne") for path in state["lines"]]
    for line in lines:
        h.set_values(line, dict(outserv=0))
        for key in ("bus1", "bus2"):
            for switch in (line.GetAttribute(key).GetContents("*.StaSwitch", 0) or []):
                h.set_values(switch, dict(on_off=1))

    def command(cls):
        obj = app.GetFromStudyCase(cls)
        if obj is None or not h.name(obj).startswith(state["case"] + "\\"):
            raise RuntimeError("Calculation command outside temporary case")
        return obj

    record = dict(seed=request["seed"], created_load=h.name(load), created_type=h.name(typ),
                  p0_mw=p0, q0_mvar=q0, retained_type=retained, trace=[], success=False,
                  case_activation=activation,
                  feeder_r_ohm_per_km=30. / p0, feeder_x_ohm_per_km=5. / p0)
    try:
        h.set_values(load, dict(outserv=0))
        ldf = command("ComLdf")
        if "voltage" not in str(ldf.GetAttributeDescription("iopt_pq")).lower():
            raise RuntimeError("Unknown voltage-dependency option")
        h.set_values(ldf, dict(iopt_net=0, iopt_pq=1, iopt_at=0))
        h.command(ldf, "Execute")
        for obj, var, unit in ((bus, "m:u", "p.u."), (load, "m:P:bus1", "mw"), (load, "m:Q:bus1", "mvar")):
            if str(obj.GetAttributeUnit(var)).strip().lower() != unit:
                raise RuntimeError("Unexpected load-flow result units")
        lf = dict(u_pu=float(bus.GetAttribute("m:u")), p_mw=float(load.GetAttribute("m:P:bus1")),
                  q_mvar=float(load.GetAttribute("m:Q:bus1")))
        if not all(math.isfinite(v) for v in lf.values()):
            raise RuntimeError("Nonfinite load flow")
        if not h.power_close(lf["p_mw"], lf["q_mvar"], *h.zip_power(lf["u_pu"], retained, p0, q0)):
            raise RuntimeError("Load-flow polynomial failed")
        record["loadflow"] = lf
        events = case.CreateObject("IntEvt", "Events " + str(request["seed"]))
        result = case.CreateObject("ElmRes", "Trace " + str(request["seed"]))
        if events is None or result is None:
            raise RuntimeError("Could not create temporary event/result objects")
        for label, time, switch in (("Dip", 1., 0), ("Recovery", 3., 1)):
            evt = events.CreateObject("EvtSwitch", label)
            if evt is None:
                raise RuntimeError("Could not create event")
            h.set_values(evt, dict(p_target=lines[1], time=time, i_switch=switch))
        inc, sim = command("ComInc"), command("ComSim")
        h.set_values(inc, dict(iopt_sim="rms", iopt_net="sym", iopt_show=0, iopt_adapt=0,
                               dtgrd=.01, tstart=0., p_event=events, p_resvar=result))
        h.set_values(sim, dict(tstop=5.))
        h.command(result, "Clear")
        for obj, var, unit in ((bus, "m:u", "p.u."), (load, "m:Psum:bus1", "mw"), (load, "m:Qsum:bus1", "mvar")):
            if str(obj.GetAttributeUnit(var)).strip().lower() != unit or result.AddVariable(obj, var) not in (None, 0):
                raise RuntimeError("RMS channel unavailable: " + var)
        h.command(inc, "Execute")
        h.command(sim, "Execute")
        record["trace"] = h.read_series(result, bus, load, "m:Psum:bus1", "m:Qsum:bus1")
        record["analysis"] = h.analyze(record["trace"], retained, "nonlinear_zip", lf, p0, q0)
        record["success"] = record["analysis"]["control_passed"] is True
        if not record["success"]:
            record["error"] = "Actual created load did not match settled ZIP response"
        for key, expected in retained.items():
            h.check(typ.GetAttribute(key), expected, "created type unchanged " + key)
        record["created_type_unchanged"] = True
    except Exception as exc:
        record["error"] = str(exc)
    finally:
        try:
            h.set_values(load, dict(outserv=1))
            record["returned_out_of_service"] = True
        except Exception as exc:
            record["service_restore_error"] = str(exc)
            record["success"] = False
    return record


def cleanup(app, state, capture):
    restore(app, state)
    project = require_project(app)
    owned = list(state["roots"])
    if capture is not None:
        owned += [dict(path=capture[str(r["seed"])]["creation"]["created_type"], cls="TypLod")
                  for r in state["requests"]]
    errors = []
    # Delete network before its library types, after original context is active.
    owned.sort(key=lambda item: {"IntCase": 0, "ElmNet": 1}.get(item["cls"], 2))
    for item in owned:
        found = [o for o in (project.GetContents("*." + item["cls"], 1) or []) if h.name(o) == item["path"]]
        try:
            for obj in found:
                h.command(obj, "Delete")
        except Exception as exc:
            errors.append(str(exc))
    remaining = [item["path"] for item in owned if any(h.name(o) == item["path"]
                 for o in (project.GetContents("*." + item["cls"], 1) or []))]
    # Without verified capture, never claim unknown/reserved library objects were cleaned.
    if capture is None:
        for r in state["requests"]:
            path = state["type_folder"] + "\\" + r["type_name"] + ".TypLod"
            if any(h.name(o) == path for o in (project.GetContents("*.TypLod", 1) or [])):
                remaining.append(path)
    return dict(restored=True, cleanup_ok=not remaining and not errors,
                remaining_objects=remaining, cleanup_errors=errors)


def run(app):
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("schema") != 1 or state.get("project") != h.PROJECT or state.get("closed"):
        raise RuntimeError("Invalid or closed state; do not rerun")
    report = dict(success=False, scope="MCP unified creation then actual-object balanced 50 Hz RMS settled-response test",
                  state=copy.deepcopy(state), runs=[], restored=False, cleanup_ok=False, remaining_objects=[],
                  limitations=["Two seeds only; not full sampled domain or recovery dynamics.",
                               "Engineering feeder scaled by P0, zero time constants; not paper-derived dynamics.",
                               "No unbalanced RMS, EMT, frequency-response or server run_rms_simulation validation."])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = STATE.parent / ("ZIP_RMS_E2E_" + stamp + "_" + uuid.uuid4().hex[:8] + ".json")
    verified = None
    with path.open("x", encoding="utf-8") as stream:
        try:
            if PHASE != "cleanup":
                if not state.get("ready"):
                    raise RuntimeError("Preparation incomplete")
                raw = CAPTURE.read_text(encoding="utf-8-sig")
                report["capture_text"] = raw
                report["capture_sha256"] = hashlib.sha256(CAPTURE.read_bytes()).hexdigest()
                verified = check_capture(state, json.loads(raw))
                report["capture"] = verified
                for request in state["requests"]:
                    item = simulate(app, state, request, verified[str(request["seed"])]["creation"])
                    report["runs"].append(item)
                    if not item.get("returned_out_of_service"):
                        raise RuntimeError("Load service state not restored; later runs stopped")
                report["success"] = len(report["runs"]) == 2 and all(r["success"] for r in report["runs"])
            elif CAPTURE.exists():
                verified = check_capture(state, json.loads(CAPTURE.read_text(encoding="utf-8-sig")))
        except Exception as exc:
            report["error"] = str(exc)
        finally:
            try:
                report.update(cleanup(app, state, verified))
            except Exception as exc:
                report["restoration_or_cleanup_error"] = str(exc)
                report["remaining_objects"] = ([r["path"] for r in state["roots"]]
                    + [state["type_folder"] + "\\" + r["type_name"] + ".TypLod"
                       for r in state["requests"]])
                report["remaining_objects_note"] = "Conservative candidate list; verification failed, not confirmed existence"
            report["success"] = report["success"] and report["restored"] and report["cleanup_ok"]
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    state["closed"] = bool(report["cleanup_ok"])
    state["result_file"] = str(path)
    save_state(state)
    app.PrintPlain("ZIP_RMS_E2E_RESULT_FILE: " + str(path))
    app.PrintPlain(json.dumps({k: report[k] for k in ("success", "restored", "cleanup_ok", "remaining_objects")}))
    return report


def main():
    import powerfactory
    app = powerfactory.GetApplication()
    if app is None:
        raise RuntimeError("Use interactive ComPython with MCP stopped")
    try:
        if PHASE == "prepare":
            prepare(app)
        elif PHASE in ("run", "cleanup"):
            run(app)
        else:
            raise ValueError("PHASE must be prepare, run, or cleanup")
    except Exception as exc:
        app.PrintPlain("ZIP_RMS_E2E_ERROR: " + str(exc))
        app.PrintPlain("Preserve state and output; no passing result is confirmed.")


if __name__ == "__main__":
    main()
