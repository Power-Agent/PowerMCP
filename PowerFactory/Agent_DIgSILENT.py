"""
╔══════════════════════════════════════════════════════════════════╗
║           DIGSILENT AGENT — Standalone RMS Simulation            ║
╚══════════════════════════════════════════════════════════════════╝

Author
------
  Andrea Pomarico
  Aswin Krishna Poyil
  
"""

import sys
import os
import json
import csv
import hashlib
import inspect
import math
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _add_plot_legend(ax, series_count: int) -> None:
    """Keep large legends outside the axes so they do not cover the plot."""
    if series_count > 12:
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),
            ncol=min(6, series_count),
            fontsize=8,
        )
    else:
        ax.legend(loc="best", fontsize=9)

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.sandbox import checked_path, ensure_checked_directory
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

# ── PowerFactory Python path ──────────────────────────────────────
# The bundled vendor `powerfactory` module lives next to the PowerFactory
# installation. Its directory is resolved lazily (from powermcp config, with an
# environment-variable fallback) and injected onto sys.path only at the moment
# of the deferred `import powerfactory`, never at module import time.

def _powerfactory_python_path():
    import os
    try:
        from powermcp.config import get_path
        p = get_path("powerfactory", "python_path", must_exist=False)
        if p:
            return p
    except Exception:
        pass
    return os.environ.get("POWERFACTORY_PYTHON_PATH") or os.environ.get("PYTHONPATH")


def _ensure_powerfactory_on_path():
    """Inject the PowerFactory python_path dir onto sys.path if not present."""
    raw = _powerfactory_python_path()
    if not raw:
        return
    for _path in [part.strip() for part in raw.split(os.pathsep) if part.strip()]:
        if _path not in sys.path:
            sys.path.append(_path)


# Deferred import: powerfactory is only available when PowerFactory is running.
# Importing it at module level would crash the MCP server on startup if PF isn't
# open yet.  The actual import happens inside connect() when a tool is invoked.
pf = None

# ══════════════════════════════════════════════════════════════════
# CONFIGURATION — edit this block to match your setup
# ══════════════════════════════════════════════════════════════════

@dataclass
class SimulationConfig:
    """All parameters needed to run one RMS simulation."""

    # ── Project ───────────────────────────────────────────────────
    project_path: str = ""
    study_case:   str = r"ctocto"
    base_study_case: str = r"0. Base"

    # ── Fault ─────────────────────────────────────────────────────
    # fault_type : "bus"  → EvtShc ON + EvtShc OFF (clear)
    #              "line" → EvtShc ON + EvtSwitch OPEN (trip line)
    #              "gen_switch" → EvtSwitch on generator (open/close)
    fault_type:    str = "bus"
    fault_element: str = "Bus 01.ElmTerm"   # PF object name for the short-circuit
    switch_element: str = ""                # PF object name for generator switch event (e.g., Gen 05.ElmSym)
    t_switch: float = 1.0                    # time when generator switch is applied
    switch_state: int = 0                    # EvtSwitch.i_switch (0=open, 1=close)

    # ── RMS simulation timing (seconds) ──────────────────────────
    t_start: float = 0.0
    t_fault: float = 1.0    # time when fault is applied
    t_clear: float = 1.08   # fault clearance time  (FCT = 80 ms)
    t_end:   float = 10.0   # total simulation duration

    # ── Time step ─────────────────────────────────────────────────
    dt_rms: float = 0.01    # seconds

    # ── CSV output ────────────────────────────────────────────────
    output_dir:   str = r""
    run_label:    str = "run_001"
    result_name:  str = "All calculations.ElmRes"
    export_pfd: int = 0
    open_digsilent: int = 1
    word_document: int = 0
    final_word_document: int = 1
    final_presentation: int = 1

    # Set to 1 to enable optional LLM pipeline steps.
    # Disabled by default to reduce API quota usage on quick test runs.
    run_review_agent: int = 0
    run_final_report_agent: int = 0
    run_mitigation_agent: int = 0

    # ──────────────────────────────────────────────────────────────
    @classmethod
    def from_json(cls, path: str) -> "SimulationConfig":
        """Load config from a JSON file, overriding only the keys present."""
        path = checked_path(path, purpose="config path")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    # ── Signals to export ─────────────────────────────────────────
    # Each entry: (object_name, variable_name, friendly_label)
    # Adjust names to match elements in your network model.
    signals: list = field(default_factory=lambda: [
        # Bus voltages
        ("Bus 01.ElmTerm",    "m:u",    "V_01_pu"),
        ("Bus 02.ElmTerm",   "m:u",    "V_02_pu"),
        ("Bus 03.ElmTerm",   "m:u",    "V_03_pu"),

        # # Generator rotor angles
        # ("Gen 01.ElmSym",       "s:firel","Angle_CS1_deg"),
        # ("Gen 02.ElmSym",       "s:firel","Angle_CS2_deg"),

        # # System frequency (measured at reference bus or machine)
        # ("Gen 01.ElmSym",       "m:f",    "Freq_CS1_Hz"),
    ])


# ══════════════════════════════════════════════════════════════════
# LOGGER
# ══════════════════════════════════════════════════════════════════

class Logger:
    """Simple timestamped console logger."""

    @staticmethod
    def info(msg: str):  print(f"[INFO]  {time.strftime('%H:%M:%S')} | {msg}")

    @staticmethod
    def ok(msg: str):    print(f"[OK]    {time.strftime('%H:%M:%S')} | ✅ {msg}")

    @staticmethod
    def warn(msg: str):  print(f"[WARN]  {time.strftime('%H:%M:%S')} | ⚠️  {msg}")

    @staticmethod
    def error(msg: str): print(f"[ERROR] {time.strftime('%H:%M:%S')} | ❌ {msg}")

    @staticmethod
    def section(title: str):
        bar = "═" * 60
        print(f"\n{bar}\n  {title}\n{bar}")


log = Logger()


def _safe_path_label(value: str, default: str = "run") -> str:
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or default)
    if label in {".", ".."}:
        return default
    label = label.replace("..", "_").strip(".")
    return label or default


def _ensure_output_directory(path: str, purpose: str) -> str:
    return ensure_checked_directory(path, purpose=purpose)


# ══════════════════════════════════════════════════════════════════
# DIGSILENT AGENT
# ══════════════════════════════════════════════════════════════════

class DIgSILENTAgent:
    """
    Standalone agent that wraps the PowerFactory Python API.
    All public methods return (success: bool, message: str).
    """

    # Keep one PowerFactory handle per Python process.
    # PowerFactory cannot be started multiple times in the same process.
    _shared_app: Optional[object] = None
    _shared_project_path: Optional[str] = None
    _shared_project: Optional[object] = None
    _create_case_request_cache: dict[str, tuple[bool, str, float]] = {}
    _create_case_request_ttl_sec: int = 3600
    _max_loc_name_length: int = 40
    _evemtbench_database_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "evemtbench_transformers.json",
    )
    _evemtbench_line_database_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "evemtbench_overhead_lines.json",
    )
    _evemtbench_cable_database_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "evemtbench_underground_cables.json",
    )
    _evemtbench_external_grid_database_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "evemtbench_external_grids.json",
    )
    _evemtbench_load_database_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "evemtbench_loads.json",
    )
    _evemtbench_synchronous_machine_database_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "evemtbench_synchronous_machines.json",
    )
    _component_specs = {
        "bus": {
            "class_name": "ElmTerm",
            "label": "Bus",
            "required": {"nominal_voltage_kv"},
            "optional": set(),
            "bus_parameters": (),
            "bus_details": (),
            "connections": (),
            "template": None,
            "numbers": (
                ("uknom", "nominal_voltage_kv", "positive", None),
            ),
        },
        "load": {
            "class_name": "ElmLod",
            "label": "Load",
            "required": {"bus_name", "active_power_mw"},
            "optional": {"reactive_power_mvar"},
            "bus_parameters": ("bus_name",),
            "bus_details": ("bus",),
            "connections": ("bus1",),
            "template": None,
            "numbers": (
                ("plini", "active_power_mw", "non_negative", None),
                ("qlini", "reactive_power_mvar", "finite", 0.0),
            ),
        },
        "generator": {
            "class_name": "ElmSym",
            "label": "Generator",
            "required": {
                "bus_name",
                "template_generator",
                "active_power_mw",
            },
            "optional": {"reactive_power_mvar"},
            "bus_parameters": ("bus_name",),
            "bus_details": ("bus",),
            "connections": ("bus1",),
            "template": (
                "template_generator",
                "generator",
                "synchronous-machine type",
            ),
            "numbers": (
                ("pgini", "active_power_mw", "non_negative", None),
                ("qgini", "reactive_power_mvar", "finite", 0.0),
            ),
        },
        "line": {
            "class_name": "ElmLne",
            "label": "Line",
            "required": {
                "bus1_name",
                "bus2_name",
                "template_line",
                "length_km",
            },
            "optional": set(),
            "bus_parameters": ("bus1_name", "bus2_name"),
            "bus_details": ("bus1", "bus2"),
            "connections": ("bus1", "bus2"),
            "template": ("template_line", "line", "line type"),
            "numbers": (
                ("dline", "length_km", "positive", None),
            ),
        },
        "transformer": {
            "class_name": "ElmTr2",
            "label": "Transformer",
            "required": {
                "high_voltage_bus_name",
                "low_voltage_bus_name",
                "template_transformer",
            },
            "optional": set(),
            "bus_parameters": (
                "high_voltage_bus_name",
                "low_voltage_bus_name",
            ),
            "bus_details": (
                "high_voltage_bus",
                "low_voltage_bus",
            ),
            "connections": ("bushv", "buslv"),
            "template": (
                "template_transformer",
                "transformer",
                "transformer type",
            ),
            "numbers": (),
        },
    }

    @classmethod
    def _apply_show_preference(cls, app, open_digsilent: bool = True) -> None:
        """Show PowerFactory window only when requested."""
        if not open_digsilent:
            return
        for attempt in range(1, 6):
            try:
                app.Show()
                return
            except Exception as e:
                if attempt == 5:
                    log.warn(f"app.Show() failed after 5 attempts: {e}")
                else:
                    log.warn(f"app.Show() attempt {attempt} failed: {e} — retrying in 2s")
                    time.sleep(2)

    def __init__(self, config: SimulationConfig):
        self.cfg = config
        self.app: Optional[object] = None
        self.project: Optional[object] = None
        self.result_objects: dict = {}   # label → PF result object
        # Subfolder for this run's outputs
        self.run_output_dir: str = ""

    def _ensure_run_output_dir(self) -> str:
        """Create and return the run-specific output subdirectory."""
        if not self.run_output_dir:
            safe_label = _safe_path_label(self.cfg.run_label)
            base_dir = _ensure_output_directory(
                self.cfg.output_dir, purpose="configured output directory"
            )
            self.run_output_dir = checked_path(
                os.path.join(base_dir, safe_label),
                purpose="generated run output directory",
                for_write=True,
            )
            os.makedirs(self.run_output_dir, exist_ok=True)
            log.info(f"Run output directory: {self.run_output_dir}")
        return self.run_output_dir

    @staticmethod
    def _find_study_case_exact(folder, case_name: str):
        """Return the IntCase whose loc_name exactly matches case_name."""
        try:
            cases = folder.GetContents("*.IntCase") or []
        except Exception:
            cases = folder.GetContents() or []

        for case in cases:
            if getattr(case, "loc_name", None) == case_name:
                return case
        return None

    @staticmethod
    def _list_study_case_names(folder) -> set[str]:
        """Return all study case loc_name values in the study folder."""
        try:
            cases = folder.GetContents("*.IntCase") or []
        except Exception:
            cases = folder.GetContents() or []
        names = set()
        for case in cases:
            name = getattr(case, "loc_name", None)
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
        return names

    @classmethod
    def _prune_create_case_request_cache(cls) -> None:
        """Remove expired create_study_case idempotency entries."""
        now = time.time()
        expired = [
            key
            for key, (_, _, ts) in cls._create_case_request_cache.items()
            if now - ts > cls._create_case_request_ttl_sec
        ]
        for key in expired:
            cls._create_case_request_cache.pop(key, None)

    # ──────────────────────────────────────────────────────────────
    # STEP 1 — Connect to PowerFactory & activate project
    # ──────────────────────────────────────────────────────────────

    def connect(self) -> tuple[bool, str]:
        log.section("STEP 1 — Connect to PowerFactory")
        try:
            open_digsilent = bool(getattr(self.cfg, "open_digsilent", 1))
            self.app = self._get_application(open_digsilent)
            log.ok("PowerFactory application obtained")
        except Exception as e:
            log.error(f"Cannot connect to PowerFactory: {e}")
            return False, str(e)

        try:
            if DIgSILENTAgent._shared_project_path != self.cfg.project_path:
                self.project = self.app.ActivateProject(self.cfg.project_path)
                if self.project is None:
                    raise RuntimeError(f"Project not found: {self.cfg.project_path}")
                DIgSILENTAgent._shared_project = self.project
                DIgSILENTAgent._shared_project_path = self.cfg.project_path
                log.ok(f"Project activated: {self.cfg.project_path}")
            else:
                self.project = DIgSILENTAgent._shared_project
                log.ok(f"Reusing already active project: {self.cfg.project_path}")
        except Exception as e:
            log.error(f"Cannot activate project: {e}")
            return False, str(e)

        return True, "Connected and project activated"

    # ──────────────────────────────────────────────────────────────
    # STEP 2 — Activate study case
    # ──────────────────────────────────────────────────────────────

    def activate_study_case(self) -> tuple[bool, str]:
        log.section("STEP 2 — Activate Study Case")
        try:
            folder = self.app.GetProjectFolder('study')
            target_name = self.cfg.study_case
            base_name = getattr(self.cfg, "base_study_case", "0. Base")
            created = False

            if folder is not None:
                # Standard project: study cases folder exists
                target_case = self._find_study_case_exact(folder, target_name)
                if target_case is not None:
                    target_case.Activate()
                else:
                    base_case = self._find_study_case_exact(folder, base_name)
                    if base_case is None:
                        raise RuntimeError(
                            f"Base study case not found in study folder: '{base_name}'"
                        )
                    if target_name == base_name:
                        base_case.Activate()
                    else:
                        created = True
                        new_study_case = folder.AddCopy(base_case, target_name)
                        if new_study_case is None:
                            target_case = self._find_study_case_exact(folder, target_name)
                            if target_case is None:
                                raise RuntimeError(
                                    f"Study case copy failed: '{target_name}'"
                                )
                            new_study_case = target_case
                        new_study_case.Activate()
                        log.ok(f"Study case copied from '{base_name}' to '{target_name}'")
            else:
                # Non-standard project: search the whole project for *.IntCase by name
                log.warn("GetProjectFolder('study') returned None — searching project for IntCase objects")
                case_name = target_name.split('\\')[-1]
                matches = self.app.GetCalcRelevantObjects(f"{case_name}.IntCase")
                if not matches:
                    raise RuntimeError(
                        f"Study case '{case_name}' not found via GetCalcRelevantObjects either. "
                        "Check the name in PowerFactory's Data Manager."
                    )
                matches[0].Activate()

            log.ok(f"Study case activated: {target_name}")
            return True, "Study case created and activated" if created else "Study case activated"
        except Exception as e:
            log.error(f"Study case activation failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # STEP 4 — Run load flow
    # ──────────────────────────────────────────────────────────────

    def run_loadflow(self) -> tuple[bool, str]:
        log.section("STEP 4 — Load Flow (ComLdf)")
        try:
            ldf = self.app.GetFromStudyCase('ComLdf')
            if ldf is None:
                raise RuntimeError("ComLdf not found in study case")
            err = ldf.Execute()
            if err:
                raise RuntimeError(f"ComLdf returned error code {err}")
            log.ok("Load flow converged successfully")
            return True, "Load flow OK"
        except Exception as e:
            log.error(f"Load flow failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # STEP 5 — Configure & run RMS simulation
    # ──────────────────────────────────────────────────────────────

    def run_rms_simulation(self) -> tuple[bool, str]:
        log.section("STEP 5 — RMS Simulation (ComInc + ComSim)")
        try:
            # -- Build fault events BEFORE initialisation -------------
            log.info(f"Applying fault at t={self.cfg.t_fault}s, clearing at t={self.cfg.t_clear}s")
            self._apply_fault_event()

            # -- Initialise simulation --------------------------------
            inc = self.app.GetFromStudyCase('ComInc')
            inc.iopt_sim   = 'rms'
            inc.iopt_show  = 0
            inc.iopt_adapt = 0
            inc.dtgrd      = self.cfg.dt_rms
            inc.start      = self.cfg.t_start
            self.app.EchoOff()
            err = inc.Execute()
            self.app.EchoOn()
            if err:
                raise RuntimeError(f"ComInc (initialisation) returned error code {err}")
            log.ok(f"Simulation initialised | dt={self.cfg.dt_rms}s")

            # -- Run simulation ---------------------------------------
            sim = self.app.GetFromStudyCase('ComSim')
            sim.tstop = self.cfg.t_end
            err = sim.Execute()
            if err:
                raise RuntimeError(f"ComSim returned error code {err}")
            log.ok(f"RMS simulation completed | t_end={self.cfg.t_end}s")
            return True, "RMS simulation OK"

        except Exception as e:
            log.error(f"RMS simulation failed: {e}")
            return False, str(e)

    def _apply_fault_event(self):
        """
        Clear all existing events, then create fault ON + clearance events.

        fault_type = "bus"  : EvtShc ON → EvtShc OFF (removes short-circuit)
        fault_type = "line" : EvtShc ON → EvtSwitch OPEN (trips the line)
        fault_type = "gen_switch" : EvtSwitch on selected generator
        """
        try:
            evt_folder = self.app.GetFromStudyCase('Simulation Events/Fault.IntEvt')
            if evt_folder is None:
                raise RuntimeError("Event folder not found: Simulation Events/Fault.IntEvt")

            # -- Clear existing events --------------------------------
            for obj in evt_folder.GetContents():
                obj.Delete()
            log.info("Existing simulation events cleared")

            raw_fault_type = str(getattr(self.cfg, "fault_type", "bus") or "bus")
            fault_type = raw_fault_type.strip().lower().replace("-", "_").replace(" ", "_")
            if fault_type in ("generator", "switch", "generator_switch"):
                fault_type = "gen_switch"

            if fault_type == "gen_switch":
                switch_element = (
                    getattr(self.cfg, "switch_element", "")
                    or getattr(self.cfg, "fault_element", "")
                )
                switch_time = float(
                    getattr(self.cfg, "t_switch", getattr(self.cfg, "switch_time", getattr(self.cfg, "t_fault", 1.0)))
                )

                raw_switch_state = getattr(self.cfg, "switch_state", getattr(self.cfg, "open_close", 0))
                if isinstance(raw_switch_state, str):
                    s = raw_switch_state.strip().lower()
                    if s in ("open", "trip", "off"):
                        switch_state = 0
                    elif s in ("close", "on"):
                        switch_state = 1
                    else:
                        switch_state = int(raw_switch_state)
                else:
                    switch_state = int(raw_switch_state)

                matches = self.app.GetCalcRelevantObjects(switch_element)
                if (not matches) and switch_element and ("." not in switch_element):
                    matches = self.app.GetCalcRelevantObjects(f"{switch_element}.ElmSym")
                if not matches:
                    all_gens = self.app.GetCalcRelevantObjects("*.ElmSym")
                    matches = [g for g in all_gens if getattr(g, "loc_name", "") == switch_element]
                if not matches:
                    raise RuntimeError(f"Switch target not found: {switch_element}")
                target = matches[0]

                # If a dedicated switch object exists for this generator name, prefer it.
                switch_obj_matches = self.app.GetCalcRelevantObjects(f"{target.loc_name}.StaSwitch")
                if switch_obj_matches:
                    target = switch_obj_matches[0]

                self.addSwitchEvent(target, switch_time, switch_state)
                action = "OPEN" if switch_state == 0 else "CLOSE"
                target_name = getattr(target, "loc_name", switch_element)
                log.info(f"EvtSwitch {action} → {target_name} at t={switch_time}s")
                return

            if fault_type not in ("bus", "line"):
                raise RuntimeError(f"Unsupported fault_type '{raw_fault_type}'. Use bus, line, or gen_switch.")

            # -- Faulted element --------------------------------------
            target = self.app.GetCalcRelevantObjects(self.cfg.fault_element)[0]

            # -- Short-circuit ON (same for both types) ---------------
            sc_on          = evt_folder.CreateObject('EvtShc', target.loc_name)
            sc_on.p_target = target
            sc_on.time     = self.cfg.t_fault
            sc_on.i_shc    = 0   # 3-phase fault
            log.info(f"EvtShc ON  → {self.cfg.fault_element} at t={self.cfg.t_fault}s")

            # -- Clearance (depends on fault_type) --------------------
            if fault_type == "line":
                # Trip the line: open its switch at t_clear
                self.addSwitchEvent(target, self.cfg.t_clear, 0)
                log.info(f"EvtSwitch OPEN → {self.cfg.fault_element} at t={self.cfg.t_clear}s")
            else:
                # Bus fault: remove short-circuit at t_clear
                sc_off          = evt_folder.CreateObject('EvtShc', target.loc_name)
                sc_off.p_target = target
                sc_off.time     = self.cfg.t_clear
                sc_off.i_shc    = 4   # clear fault
                log.info(f"EvtShc OFF → {self.cfg.fault_element} at t={self.cfg.t_clear}s")

        except Exception as e:
            log.warn(f"Could not create fault events automatically: {e}")
            log.warn("Continuing simulation without explicit fault — check your IntEvt folder")

    def addSwitchEvent(self, obj, sec, open_close):
        faultFolder = self.app.GetFromStudyCase("Simulation Events/Fault.IntEvt")
        if faultFolder is None:
            raise RuntimeError("Event folder not found: Simulation Events/Fault.IntEvt")
        event = faultFolder.CreateObject("EvtSwitch", obj.loc_name)
        if event is None:
            raise RuntimeError(f"Could not create EvtSwitch for target '{obj.loc_name}'")
        event.p_target = obj
        event.time = sec
        event.i_switch = open_close
        return event

    # ──────────────────────────────────────────────────────────────
    # STEP 6 — Export results to CSV
    # ──────────────────────────────────────────────────────────────

    def export_results_to_csv(self) -> tuple[bool, str]:
        log.section("STEP 6 — Export Results to CSV")
        try:
            run_dir = self._ensure_run_output_dir()

            filename = os.path.join(
                run_dir,
                f"{_safe_path_label(self.cfg.run_label)}_RMS.csv"
            )
            filename = checked_path(
                filename, purpose="generated RMS CSV path", for_write=True
            )

            # -- Use ComRes (PowerFactory built-in CSV exporter) ------
            comRes = self.app.GetFromStudyCase("ComRes")
            comRes.pResult  = self.app.GetFromStudyCase(self.cfg.result_name)
            comRes.f_name   = filename
            comRes.iopt_sep = 0   # use custom separators below
            comRes.col_Sep  = ";" # column separator
            comRes.dec_Sep  = "." # decimal separator
            comRes.iopt_exp = 6   # export format: CSV with time column
            comRes.iopt_csel = 0  # all columns
            comRes.iopt_vars = 0  # all variables
            comRes.iopt_tsel = 0  # full time range
            comRes.iopt_rscl = 0  # no rescaling
            err = comRes.Execute()
            if err:
                raise RuntimeError(f"ComRes.Execute() returned error code {err}")

            log.ok(f"CSV saved → {filename}")
            return True, filename

        except Exception as e:
            log.error(f"CSV export failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # STEP 7 — Optional export active project to PFD
    # ──────────────────────────────────────────────────────────────

    def export_project_to_pfd(self) -> tuple[bool, str]:
        log.section("STEP 7 — Export Active Project to PFD")
        try:
            active_project = self.app.GetActiveProject()
            if active_project is None:
                raise RuntimeError("No active project found")

            run_dir = self._ensure_run_output_dir()
            safe_label = _safe_path_label(self.cfg.run_label)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pfd_path = checked_path(
                os.path.join(run_dir, f"{safe_label}_{timestamp}.pfd"),
                purpose="generated PFD path",
                for_write=True,
            )

            pfd_export = self.app.GetFromStudyCase("ComPfdexport")
            if pfd_export is None:
                raise RuntimeError("ComPfdexport command not found in study case")

            pfd_export.SetAttribute("g_objects", [active_project])
            pfd_export.SetAttribute("g_file", pfd_path)
            err = pfd_export.Execute()
            if err:
                raise RuntimeError(f"ComPfdexport.Execute() returned error code {err}")

            log.ok(f"PFD exported → {pfd_path}")
            return True, pfd_path

        except Exception as e:
            log.error(f"PFD export failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # STEP 8 — Generate standard plots from CSV
    # ──────────────────────────────────────────────────────────────

    def generate_standard_plots(self, csv_path: str) -> tuple[bool, str]:
        log.section("STEP 8 — Generate Standard Plots")
        try:
            csv_path = checked_path(csv_path, purpose="results CSV path")
            if not os.path.exists(csv_path):
                raise RuntimeError(f"CSV file not found: {csv_path}")

            import pandas as pd
            run_dir = self._ensure_run_output_dir()
            safe_label = _safe_path_label(self.cfg.run_label)

            # Detect delimiter from the first line; PF exports are usually ';'.
            with open(csv_path, "r", encoding="utf-8", errors="replace") as fh:
                line_1 = fh.readline()
                line_2 = fh.readline()
            delimiter = ";" if line_1.count(";") >= line_1.count(",") else ","

            # PowerFactory often exports two header rows:
            #   row 1: object names (Bus 01, G 01, ...)
            #   row 2: variable labels (u1, Magnitude in p.u., Speed in p.u., ...)
            has_two_row_header = (
                bool(line_2)
                and "Time in s" in line_2
                and (
                    "Magnitude in p.u." in line_2
                    or "Speed in p.u." in line_2
                    or "rel.Angle" in line_2
                )
            )

            if has_two_row_header:
                df = pd.read_csv(csv_path, sep=delimiter, header=[0, 1], decimal=".")
                if df.empty or len(df.columns) <= 1:
                    raise RuntimeError(f"Could not parse CSV: {csv_path}")

                time_data = pd.to_numeric(df.iloc[:, 0], errors="coerce")
                voltage_series = []
                speed_series = []
                used_labels = set()

                def _unique_label(base: str) -> str:
                    label = base
                    idx = 2
                    while label in used_labels:
                        label = f"{base}_{idx}"
                        idx += 1
                    used_labels.add(label)
                    return label

                for i in range(1, len(df.columns)):
                    col = df.columns[i]
                    obj_name = str(col[0]).strip()
                    var_name = str(col[1]).strip().lower()
                    series = pd.to_numeric(df.iloc[:, i], errors="coerce")
                    if series.notna().sum() == 0:
                        continue

                    if "magnitude in p.u." in var_name:
                        voltage_series.append((_unique_label(obj_name), series))
                    elif "speed" in var_name:
                        speed_series.append((_unique_label(obj_name), series))

            else:
                df = pd.read_csv(csv_path, sep=delimiter, decimal=".")
                if df.empty or len(df.columns) <= 1:
                    raise RuntimeError(f"Could not parse CSV: {csv_path}")

                time_data = pd.to_numeric(df.iloc[:, 0], errors="coerce")
                voltage_series = []
                speed_series = []
                for col in df.columns[1:]:
                    col_text = str(col).lower()
                    series = pd.to_numeric(df[col], errors="coerce")
                    if series.notna().sum() == 0:
                        continue

                    if (
                        "magnitude in p.u." in col_text
                        or col_text.endswith("_pu")
                        or "voltage" in col_text
                    ):
                        voltage_series.append((str(col), series))
                    elif "speed" in col_text:
                        speed_series.append((str(col), series))

            # Generate voltage magnitude plot
            if voltage_series:
                fig, ax = plt.subplots(figsize=(12, 6))
                for label, series in voltage_series:
                    ax.plot(time_data, series, label=label, linewidth=1.5)
                ax.set_xlabel('Time (s)', fontsize=11)
                ax.set_ylabel('Voltage (pu)', fontsize=11)
                ax.set_title(f'Bus Voltages — {self.cfg.run_label}', fontsize=13, fontweight='bold')
                ax.grid(True, alpha=0.3)
                _add_plot_legend(ax, len(voltage_series))
                fig.tight_layout()
                voltage_plot = checked_path(
                    os.path.join(run_dir, f"{safe_label}_voltages.png"),
                    purpose="generated voltage plot path",
                    for_write=True,
                )
                fig.savefig(voltage_plot, dpi=150, bbox_inches='tight')
                plt.close(fig)
                log.ok(f"Voltage plot saved → {voltage_plot}")
            else:
                log.warn("No voltage columns found in CSV for plotting")

            # Generate generator speed plot if available
            if speed_series:
                fig, ax = plt.subplots(figsize=(12, 6))
                for label, series in speed_series:
                    ax.plot(time_data, series, label=label, linewidth=1.5)
                ax.set_xlabel('Time (s)', fontsize=11)
                ax.set_ylabel('Speed (p.u.)', fontsize=11)
                ax.set_title(f'Generator Speeds — {self.cfg.run_label}', fontsize=13, fontweight='bold')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best', fontsize=9)
                fig.tight_layout()
                speed_plot = checked_path(
                    os.path.join(run_dir, f"{safe_label}_gen_speeds.png"),
                    purpose="generated speed plot path",
                    for_write=True,
                )
                fig.savefig(speed_plot, dpi=150, bbox_inches='tight')
                plt.close(fig)
                log.ok(f"Generator speed plot saved → {speed_plot}")
            else:
                log.warn("No generator speed columns found in CSV for plotting")

            if not voltage_series and not speed_series:
                raise RuntimeError("No voltage or generator speed columns could be identified in CSV")

            return True, "Standard plots generated successfully"

        except Exception as e:
            log.error(f"Standard plots generation failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # CLOSE — shut down PowerFactory
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def close(cls) -> None:
        """Exit PowerFactory and reset the shared application handle."""
        if cls._shared_app is not None:
            try:
                cls._shared_app.Exit()
                log.ok("PowerFactory closed")
            except Exception as e:
                log.warn(f"PowerFactory Exit() raised: {e}")
            finally:
                cls._shared_app = None
                cls._shared_project = None
                cls._shared_project_path = None

    # ──────────────────────────────────────────────────────────────
    # IMPORT PROJECT — load a .pfd file into PowerFactory
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def export_active_grid_pdf(
        cls,
        file_path: str,
        diagram_name: str = "",
        open_digsilent: bool = True,
    ) -> tuple[bool, str]:
        """Export one single-line diagram from the active project as PDF."""
        try:
            file_path = checked_path(
                file_path,
                purpose="file_path",
                for_write=True,
            )
            if not file_path.lower().endswith(".pdf"):
                raise RuntimeError("file_path must end with .pdf")
            if os.path.exists(file_path):
                raise RuntimeError(f"Output file already exists: {file_path}")

            parent = os.path.dirname(file_path) or os.curdir
            if not os.path.isdir(parent):
                raise RuntimeError(f"Output directory not found: {parent}")

            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")
            if app.GetActiveStudyCase() is None:
                raise RuntimeError("No PowerFactory study case is active")

            graphics_board = app.GetGraphicsBoard()
            if graphics_board is None:
                raise RuntimeError("PowerFactory Graphics Board is unavailable")

            pages = list(graphics_board.GetContents("*.SetDeskpage") or [])
            named_pages = []
            for page in pages:
                try:
                    name = str(page.GetAttribute("loc_name"))
                except Exception:
                    name = str(getattr(page, "loc_name", ""))
                named_pages.append((name, page))

            requested_name = str(diagram_name or "").strip()
            if requested_name:
                matches = [
                    page
                    for name, page in named_pages
                    if name == requested_name
                ]
                if not matches:
                    available = ", ".join(
                        sorted(name for name, _ in named_pages if name)
                    ) or "none"
                    raise RuntimeError(
                        f"Diagram not found: {requested_name}. "
                        f"Available diagrams: {available}"
                    )
                if len(matches) > 1:
                    raise RuntimeError(
                        f"Multiple diagrams matched: {requested_name}"
                    )
                selected_page = matches[0]
                selected_name = requested_name
            else:
                if not named_pages:
                    raise RuntimeError(
                        "No single-line diagram is available in the Graphics Board"
                    )
                if len(named_pages) > 1:
                    available = ", ".join(
                        sorted(name for name, _ in named_pages if name)
                    )
                    raise RuntimeError(
                        "Multiple single-line diagrams are available; provide "
                        f"diagram_name. Available diagrams: {available}"
                    )
                selected_name, selected_page = named_pages[0]

            graphics_board.Show(selected_page)

            export_command = app.GetFromStudyCase("ComWr")
            if export_command is None:
                raise RuntimeError("ComWr export command is unavailable")
            export_command.SetAttribute("iopt_rd", "pdf")
            export_command.SetAttribute("iopt_savas", 0)
            export_command.SetAttribute("f", file_path)

            export_code = export_command.Execute()
            if export_code not in (None, 0):
                raise RuntimeError(
                    f"ComWr.Execute() returned error code {export_code}"
                )
            if not os.path.isfile(file_path):
                raise RuntimeError(
                    "ComWr reported success but did not create the PDF file"
                )

            log.ok(f"Grid diagram exported to PDF → {file_path}")
            return True, (
                f"Grid diagram '{selected_name}' exported to {file_path}"
            )
        except Exception as exc:
            log.error(f"Grid PDF export failed: {exc}")
            return False, str(exc)

    @classmethod
    def import_project(cls, file_path: str, open_digsilent: bool = True) -> tuple[bool, str]:
        """
        Import a .pfd project file into PowerFactory and activate it.

        Parameters
        ----------
        file_path : str
            Absolute path to the .pfd export file.

        Returns
        -------
        (success, message)
        """
        file_path = checked_path(file_path, purpose="file_path")
        if not os.path.isfile(file_path):
            return False, f"File not found: {file_path}"

        try:
            app = cls._get_application(open_digsilent)

            Pfdimport = app.GetFromStudyCase("ComPfdimport")
            if Pfdimport is None:
                raise RuntimeError("ComPfdimport command not found in study case")

            Pfdimport.SetAttribute("g_file", file_path)
            Pfdimport.activatePrj = 1
            err = Pfdimport.Execute()
            if err:
                raise RuntimeError(f"ComPfdimport.Execute() returned error code {err}")

            # Reset shared project so the next connect() re-activates properly.
            cls._shared_project = None
            cls._shared_project_path = None

            log.ok(f"Project imported and activated from: {file_path}")
            return True, f"Project imported successfully from {file_path}"

        except Exception as e:
            log.error(f"Project import failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # MODIFY OBJECT PARAMETER — set a PowerFactory attribute by name
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def modify_parameter(
        cls,
        object_name: str,
        variable: str,
        new_value,
        open_digsilent: bool = True,
    ) -> tuple[bool, str]:
        """
        Modify one attribute on all PowerFactory objects matching object_name.

        Parameters
        ----------
        object_name : str
            PowerFactory object query passed to GetCalcRelevantObjects
            (example: "G 10.ElmSym").
        variable : str
            Attribute name to modify (example: "e:outserv").
        new_value : Any
            New value written through SetAttribute.

        Returns
        -------
        (success, message)
        """
        try:
            app = cls._get_application(open_digsilent)

            objects = app.GetCalcRelevantObjects(object_name)
            if not objects:
                raise RuntimeError(f"No objects found for query: {object_name}")

            def _coerce_value(current_value, incoming_value):
                if incoming_value is None:
                    return None

                # Preserve non-string values that are already typed.
                if not isinstance(incoming_value, str):
                    if isinstance(current_value, bool):
                        return bool(incoming_value)
                    if isinstance(current_value, int) and not isinstance(current_value, bool):
                        return int(incoming_value)
                    if isinstance(current_value, float):
                        return float(incoming_value)
                    return incoming_value

                raw = incoming_value.strip()

                # Coerce by current attribute type when available.
                if isinstance(current_value, bool):
                    token = raw.lower()
                    if token in ("1", "true", "yes", "on"):
                        return True
                    if token in ("0", "false", "no", "off"):
                        return False
                    raise ValueError(f"Cannot cast '{incoming_value}' to bool")

                if isinstance(current_value, int) and not isinstance(current_value, bool):
                    return int(float(raw))

                if isinstance(current_value, float):
                    return float(raw)

                # Fallback inference when current value is string/None/unknown.
                token = raw.lower()
                if token in ("true", "false"):
                    return token == "true"
                try:
                    if "." not in raw and "e" not in token:
                        return int(raw)
                    return float(raw)
                except ValueError:
                    return incoming_value

            for obj in objects:
                current_value = obj.GetAttribute(variable)
                typed_value = _coerce_value(current_value, new_value)
                obj.SetAttribute(variable, typed_value)

            log.ok(
                f"Updated '{variable}' to '{new_value}' for {len(objects)} object(s) matching '{object_name}'"
            )
            return (
                True,
                f"Updated {len(objects)} object(s): {object_name} | {variable}={new_value}",
            )

        except Exception as e:
            log.error(f"Parameter update failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # COMPONENT MANAGEMENT
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _creation_confirmation_token(readable_prefix: str, plan: dict[str, Any]) -> str:
        """Bind confirmation to a canonical, lossless representation of the plan."""
        canonical_plan = json.dumps(
            plan,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        digest = hashlib.sha256(canonical_plan.encode("utf-8")).hexdigest()
        return f"{readable_prefix} plan={digest}"

    @staticmethod
    def _find_named_contents(parent, name: str, class_name: str):
        requested = str(name or "").strip()
        # GetContents name patterns are case-sensitive; match names in Python.
        return [
            obj
            for obj in (
                parent.GetContents(f"*.{class_name}", 1) or []
            )
            if str(obj.GetAttribute("loc_name")).casefold()
            == requested.casefold()
        ]

    @classmethod
    def _load_evemtbench_database(cls):
        """Load and validate the versioned transformer source database."""
        with open(cls._evemtbench_database_file, "r", encoding="utf-8") as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError("Unsupported EvEMTBench database schema")
        classes = database.get("classes")
        vector_groups = database.get("vector_groups")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError("EvEMTBench database has no transformer classes")
        if not isinstance(vector_groups, dict) or not vector_groups:
            raise RuntimeError("EvEMTBench database has no vector groups")
        frequencies = database.get("sampling", {}).get(
            "nominal_frequencies_hz"
        )
        if frequencies != [50.0, 60.0]:
            raise RuntimeError("EvEMTBench database has invalid frequencies")

        def validate_spec(spec, label):
            if not isinstance(spec, dict):
                raise RuntimeError(f"Invalid numeric specification: {label}")
            if set(spec) == {"value"}:
                values = (spec["value"],)
            elif set(spec) == {"min", "max"}:
                values = (spec["min"], spec["max"])
                if float(values[0]) > float(values[1]):
                    raise RuntimeError(f"Invalid interval ordering: {label}")
            else:
                raise RuntimeError(f"Invalid numeric specification: {label}")
            if any(
                isinstance(value, bool) or not math.isfinite(float(value))
                for value in values
            ):
                raise RuntimeError(f"Non-finite database value: {label}")

        parameter_names = (
            "short_circuit_voltage_pct",
            "winding_losses_kw",
            "no_load_losses_kw",
            "no_load_current_pct",
        )
        for class_name, transformer_class in classes.items():
            for voltage_name in ("high_voltage_kv", "low_voltage_kv"):
                voltage = transformer_class.get(voltage_name)
                if (
                    isinstance(voltage, bool)
                    or not math.isfinite(float(voltage))
                    or float(voltage) <= 0
                ):
                    raise RuntimeError(
                        f"Invalid {voltage_name} for transformer class {class_name}"
                    )
            ratings = transformer_class.get("ratings")
            if not isinstance(ratings, list) or not ratings:
                raise RuntimeError(
                    f"No ratings for transformer class {class_name}"
                )
            seen_ratings = set()
            for index, rating in enumerate(ratings):
                rated_power = float(rating.get("rated_power_mva"))
                if not math.isfinite(rated_power) or rated_power <= 0:
                    raise RuntimeError(
                        f"Invalid rating for transformer class {class_name}"
                    )
                if rated_power in seen_ratings:
                    raise RuntimeError(
                        f"Duplicate rating for transformer class {class_name}: "
                        f"{rated_power:g}"
                    )
                seen_ratings.add(rated_power)
                for parameter_name in parameter_names:
                    validate_spec(
                        rating.get(parameter_name),
                        f"{class_name}.ratings[{index}].{parameter_name}",
                    )
                groups = rating.get("vector_groups")
                if not isinstance(groups, list) or not groups:
                    raise RuntimeError(
                        f"No vector group for {class_name} rating {rated_power:g}"
                    )
                unknown = sorted(set(groups) - set(vector_groups))
                if unknown:
                    raise RuntimeError(
                        f"Unknown vector group(s): {', '.join(unknown)}"
                    )
        return database

    @classmethod
    def _load_evemtbench_sequence_database(cls, path: str, label: str):
        """Load and validate a versioned line/cable sequence database."""
        with open(path, "r", encoding="utf-8") as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError(
                f"Unsupported EvEMTBench {label} database schema"
            )
        if database.get("nominal_frequencies_hz") != [50.0, 60.0]:
            raise RuntimeError(
                f"EvEMTBench {label} database has invalid frequencies"
            )
        profiles = database.get("profiles")
        if profiles != ["p05", "p50", "p95"]:
            raise RuntimeError(
                f"EvEMTBench {label} database has invalid profiles"
            )
        classes = database.get("classes")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError(
                f"EvEMTBench {label} database has no voltage classes"
            )

        parameter_names = (
            "r1_ohm_per_km",
            "x1_ohm_per_km",
            "c1_nf_per_km",
            "r0_ohm_per_km",
            "x0_ohm_per_km",
            "c0_nf_per_km",
        )
        for class_name, line_class in classes.items():
            voltage = float(line_class.get("nominal_voltage_kv"))
            if not math.isfinite(voltage) or voltage <= 0:
                raise RuntimeError(
                    f"Invalid nominal voltage for line class {class_name}"
                )
            length = line_class.get("length_km")
            if (
                not isinstance(length, dict)
                or set(length) != {"min", "max"}
                or float(length["min"]) <= 0
                or float(length["min"]) > float(length["max"])
            ):
                raise RuntimeError(
                    f"Invalid length range for line class {class_name}"
                )
            electrical = line_class.get("electrical_profiles")
            if not isinstance(electrical, dict) or list(electrical) != profiles:
                raise RuntimeError(
                    f"Invalid electrical profiles for line class {class_name}"
                )
            for profile_name, profile in electrical.items():
                if set(profile) != set(parameter_names):
                    raise RuntimeError(
                        f"Invalid {profile_name} fields for line class "
                        f"{class_name}"
                    )
                if any(
                    not math.isfinite(float(profile[name]))
                    or float(profile[name]) < 0
                    for name in parameter_names
                ):
                    raise RuntimeError(
                        f"Invalid {profile_name} values for line class "
                        f"{class_name}"
                    )
        return database

    @classmethod
    def _load_evemtbench_line_database(cls):
        """Load and validate the versioned overhead-line source database."""
        return cls._load_evemtbench_sequence_database(
            cls._evemtbench_line_database_file,
            "line",
        )

    @classmethod
    def _load_evemtbench_cable_database(cls):
        """Load and validate the versioned underground-cable database."""
        return cls._load_evemtbench_sequence_database(
            cls._evemtbench_cable_database_file,
            "cable",
        )

    @classmethod
    def _load_evemtbench_external_grid_database(cls):
        """Load and validate the versioned external-grid source database."""
        with open(
            cls._evemtbench_external_grid_database_file,
            "r",
            encoding="utf-8",
        ) as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError(
                "Unsupported EvEMTBench external-grid database schema"
            )
        classes = database.get("classes")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError(
                "EvEMTBench external-grid database has no voltage classes"
            )
        parameters = (
            "short_circuit_power_mva",
            "positive_sequence_r_x",
            "x0_x1",
            "zero_sequence_r_x",
            "voltage_setpoint_pu",
            "initial_phase_angle_deg",
        )
        seen_voltages = set()
        for class_name, source_class in classes.items():
            voltages = source_class.get("nominal_voltages_kv")
            if not isinstance(voltages, list) or not voltages:
                raise RuntimeError(
                    f"No nominal voltages for external-grid class {class_name}"
                )
            for raw_voltage in voltages:
                voltage = float(raw_voltage)
                if not math.isfinite(voltage) or voltage <= 0:
                    raise RuntimeError(
                        f"Invalid nominal voltage for external-grid class "
                        f"{class_name}"
                    )
                if voltage in seen_voltages:
                    raise RuntimeError(
                        f"Duplicate external-grid voltage: {voltage:g}"
                    )
                seen_voltages.add(voltage)
            for parameter in parameters:
                interval = source_class.get(parameter)
                if (
                    not isinstance(interval, dict)
                    or set(interval) != {"min", "max"}
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for external-grid "
                        f"class {class_name}"
                    )
                lower = float(interval["min"])
                upper = float(interval["max"])
                if (
                    not math.isfinite(lower)
                    or not math.isfinite(upper)
                    or lower > upper
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for external-grid "
                        f"class {class_name}"
                    )
                if parameter != "initial_phase_angle_deg" and lower <= 0:
                    raise RuntimeError(
                        f"Invalid {parameter} interval for external-grid "
                        f"class {class_name}"
                    )
        return database

    @classmethod
    def _load_evemtbench_load_database(cls):
        """Load and validate the versioned Table 5 load database."""
        with open(
            cls._evemtbench_load_database_file,
            "r",
            encoding="utf-8",
        ) as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError("Unsupported EvEMTBench load database schema")
        classes = database.get("classes")
        if not isinstance(classes, dict) or not classes:
            raise RuntimeError("EvEMTBench load database has no voltage classes")
        seen_voltages = set()
        for class_name, load_class in classes.items():
            voltage = float(load_class.get("nominal_voltage_kv"))
            if not math.isfinite(voltage) or voltage <= 0:
                raise RuntimeError(
                    f"Invalid nominal voltage for load class {class_name}"
                )
            if voltage in seen_voltages:
                raise RuntimeError(f"Duplicate load voltage: {voltage:g}")
            seen_voltages.add(voltage)

            if voltage == 20.0:
                intervals = ("apparent_power_mva",)
            else:
                intervals = (
                    "active_power_mw",
                    "reactive_power_mvar",
                )
            for parameter in intervals:
                interval = load_class.get(parameter)
                if (
                    not isinstance(interval, dict)
                    or set(interval) != {"min", "max"}
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for load class "
                        f"{class_name}"
                    )
                lower = float(interval["min"])
                upper = float(interval["max"])
                if (
                    not math.isfinite(lower)
                    or not math.isfinite(upper)
                    or lower < 0
                    or lower > upper
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for load class "
                        f"{class_name}"
                    )

        power_factor = database.get("twenty_kv_power_factor")
        if not isinstance(power_factor, dict):
            raise RuntimeError("EvEMTBench load database has no power factor")
        inductive = float(power_factor.get("inductive_min"))
        capacitive = float(power_factor.get("capacitive_min"))
        if not 0 < inductive <= 1 or not 0 < capacitive <= 1:
            raise RuntimeError("EvEMTBench load database has invalid power factor")
        return database

    @classmethod
    def _load_evemtbench_synchronous_machine_database(cls):
        """Load and validate the versioned Table 13 machine catalog."""
        with open(
            cls._evemtbench_synchronous_machine_database_file,
            "r",
            encoding="utf-8",
        ) as stream:
            database = json.load(stream)

        if database.get("schema_version") != 1:
            raise RuntimeError(
                "Unsupported EvEMTBench synchronous-machine database schema"
            )
        classes = database.get("classes")
        if not isinstance(classes, dict) or set(classes) != {
            "salient_pole",
            "round_rotor",
        }:
            raise RuntimeError(
                "EvEMTBench synchronous-machine database must contain "
                "salient_pole and round_rotor classes"
            )
        for class_name, profile in classes.items():
            for parameter in (
                "rated_apparent_power_mva",
                "rated_power_factor",
            ):
                interval = profile.get(parameter)
                if (
                    not isinstance(interval, dict)
                    or set(interval) != {"min", "max"}
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for synchronous-machine "
                        f"class {class_name}"
                    )
                lower = float(interval["min"])
                upper = float(interval["max"])
                if (
                    not math.isfinite(lower)
                    or not math.isfinite(upper)
                    or lower <= 0
                    or lower > upper
                ):
                    raise RuntimeError(
                        f"Invalid {parameter} interval for synchronous-machine "
                        f"class {class_name}"
                    )
            if not isinstance(profile.get("parameters"), dict):
                raise RuntimeError(
                    f"Synchronous-machine class {class_name} has no parameters"
                )
        rules = database.get("rated_voltage_rule")
        if not isinstance(rules, list) or len(rules) != 4:
            raise RuntimeError(
                "EvEMTBench synchronous-machine voltage rule is invalid"
            )
        return database

    @classmethod
    def list_evemtbench_line_profiles(
        cls,
        voltage_kv: Optional[float] = None,
        profile: str = "",
    ) -> dict[str, Any]:
        """List executable overhead-line profiles without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_line_database()
            requested_profile = str(profile or "").strip().lower()
            if requested_profile and requested_profile not in database["profiles"]:
                return {
                    "success": False,
                    "message": "profile must be one of: "
                    + ", ".join(database["profiles"]),
                }

            if voltage_kv is None:
                selected = database["classes"]
            else:
                if isinstance(voltage_kv, bool):
                    return {
                        "success": False,
                        "message": "voltage_kv must be a number",
                    }
                requested_voltage = float(voltage_kv)
                selected = {
                    name: value
                    for name, value in database["classes"].items()
                    if math.isclose(
                        float(value["nominal_voltage_kv"]),
                        requested_voltage,
                    )
                }
                if not selected:
                    available = ", ".join(database["classes"])
                    return {
                        "success": False,
                        "message": "voltage_kv must be one of: " + available,
                    }

            results = []
            for class_name, line_class in selected.items():
                item = {
                    "voltage_class": class_name,
                    "nominal_voltage_kv": line_class["nominal_voltage_kv"],
                    "length_km": line_class["length_km"],
                    "electrical_profiles": line_class["electrical_profiles"],
                }
                if requested_profile:
                    item["electrical_profiles"] = {
                        requested_profile: line_class["electrical_profiles"][
                            requested_profile
                        ]
                    }
                if "rated_current_guidance_ka" in line_class:
                    item["rated_current_guidance_ka"] = line_class[
                        "rated_current_guidance_ka"
                    ]
                results.append(item)
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "overhead_line_sequence_equivalent",
                "nominal_frequencies_hz": database[
                    "nominal_frequencies_hz"
                ],
                "returned_count": len(results),
                "results": results,
                "powerfactory": database["powerfactory"],
                "catalog_only": database["catalog_only"],
            }
        except (TypeError, ValueError):
            return {"success": False, "message": "voltage_kv must be a number"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def list_evemtbench_cable_profiles(
        cls,
        profile: str = "",
    ) -> dict[str, Any]:
        """List executable 20 kV cable profiles without PowerFactory."""
        try:
            database = cls._load_evemtbench_cable_database()
            requested_profile = str(profile or "").strip().lower()
            if requested_profile and requested_profile not in database["profiles"]:
                return {
                    "success": False,
                    "message": "profile must be one of: "
                    + ", ".join(database["profiles"]),
                }

            cable_class = database["classes"]["20"]
            electrical = cable_class["electrical_profiles"]
            if requested_profile:
                electrical = {requested_profile: electrical[requested_profile]}
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "underground_cable_sequence_equivalent",
                "nominal_frequencies_hz": database[
                    "nominal_frequencies_hz"
                ],
                "returned_count": 1,
                "results": [{
                    "voltage_class": "20",
                    "nominal_voltage_kv": cable_class["nominal_voltage_kv"],
                    "length_km": cable_class["length_km"],
                    "electrical_profiles": electrical,
                }],
                "construction": database["construction"],
                "powerfactory": database["powerfactory"],
                "catalog_only": database["catalog_only"],
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_line_plan(
        cls,
        voltage_kv: float,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        type_name: str,
    ):
        database = cls._load_evemtbench_line_database()
        class_name, line_class = next(
            (
                (name, value)
                for name, value in database["classes"].items()
                if math.isclose(
                    float(value["nominal_voltage_kv"]),
                    voltage_kv,
                )
            ),
            (None, None),
        )
        if line_class is None:
            raise RuntimeError(
                "voltage_kv must be one of: "
                + ", ".join(database["classes"])
            )
        if profile not in database["profiles"]:
            raise RuntimeError(
                "profile must be one of: " + ", ".join(database["profiles"])
            )
        values = line_class["electrical_profiles"][profile]
        capacitance_factor = float(
            database["powerfactory"]["capacitance_conversion_factor"]
        )
        attributes = {
            "uline": voltage_kv,
            "sline": rated_current_ka,
            "frnom": nominal_frequency_hz,
            "rline": float(values["r1_ohm_per_km"]),
            "xline": float(values["x1_ohm_per_km"]),
            "cline": float(values["c1_nf_per_km"]) * capacitance_factor,
            "rline0": float(values["r0_ohm_per_km"]),
            "xline0": float(values["x0_ohm_per_km"]),
            "cline0": float(values["c0_nf_per_km"]) * capacitance_factor,
        }
        return class_name, line_class, {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": line_class["source_tables"],
            "profile": profile,
            "parameters": {
                "nominal_voltage_kv": voltage_kv,
                "nominal_frequency_hz": nominal_frequency_hz,
                "rated_current_ka": rated_current_ka,
                **values,
            },
            "powerfactory_attributes": attributes,
            "capacitance_conversion": "nF/km to uF/km (multiply by 0.001)",
            "model": database["powerfactory"]["model"],
        }

    @classmethod
    def _evemtbench_cable_plan(
        cls,
        voltage_kv: float,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        type_name: str,
    ):
        database = cls._load_evemtbench_cable_database()
        cable_class = database["classes"].get("20")
        if cable_class is None or not math.isclose(voltage_kv, 20.0):
            raise RuntimeError("voltage_kv must be 20 for underground cables")
        if profile not in database["profiles"]:
            raise RuntimeError(
                "profile must be one of: " + ", ".join(database["profiles"])
            )
        values = cable_class["electrical_profiles"][profile]
        capacitance_factor = float(
            database["powerfactory"]["capacitance_conversion_factor"]
        )
        attributes = {
            "uline": 20.0,
            "sline": rated_current_ka,
            "frnom": nominal_frequency_hz,
            "rline": float(values["r1_ohm_per_km"]),
            "xline": float(values["x1_ohm_per_km"]),
            "cline": float(values["c1_nf_per_km"]) * capacitance_factor,
            "rline0": float(values["r0_ohm_per_km"]),
            "xline0": float(values["x0_ohm_per_km"]),
            "cline0": float(values["c0_nf_per_km"]) * capacitance_factor,
        }
        return "20", cable_class, {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": cable_class["source_tables"],
            "profile": profile,
            "parameters": {
                "nominal_voltage_kv": 20.0,
                "nominal_frequency_hz": nominal_frequency_hz,
                "rated_current_ka": rated_current_ka,
                **values,
            },
            "powerfactory_attributes": attributes,
            "capacitance_conversion": "nF/km to uF/km (multiply by 0.001)",
            "model": database["powerfactory"]["model"],
            "construction_catalog": database["construction"],
        }

    @classmethod
    def list_evemtbench_external_grid_profiles(
        cls,
        voltage_kv: Optional[float] = None,
    ) -> dict[str, Any]:
        """List executable Table 4 profiles without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_external_grid_database()
            selected = []
            if voltage_kv is None:
                selected = list(database["classes"].items())
            else:
                if isinstance(voltage_kv, bool):
                    raise ValueError
                requested = float(voltage_kv)
                selected = [
                    (name, source_class)
                    for name, source_class in database["classes"].items()
                    if any(
                        math.isclose(float(value), requested)
                        for value in source_class["nominal_voltages_kv"]
                    )
                ]
                if not selected:
                    available = sorted(
                        float(value)
                        for source_class in database["classes"].values()
                        for value in source_class["nominal_voltages_kv"]
                    )
                    return {
                        "success": False,
                        "message": "voltage_kv must be one of: "
                        + ", ".join(f"{value:g}" for value in available),
                    }
            results = [
                {
                    "voltage_class": class_name,
                    **source_class,
                }
                for class_name, source_class in selected
            ]
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "external_grid_equivalent",
                "returned_count": len(results),
                "results": results,
                "powerfactory": database["powerfactory"],
            }
        except (TypeError, ValueError):
            return {"success": False, "message": "voltage_kv must be a number"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_external_grid_plan(
        cls,
        voltage_kv: float,
        external_grid_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_external_grid_database()
        class_name, source_class = next(
            (
                (name, value)
                for name, value in database["classes"].items()
                if any(
                    math.isclose(float(candidate), voltage_kv)
                    for candidate in value["nominal_voltages_kv"]
                )
            ),
            (None, None),
        )
        if source_class is None:
            available = sorted(
                float(value)
                for value in (
                    candidate
                    for item in database["classes"].values()
                    for candidate in item["nominal_voltages_kv"]
                )
            )
            raise RuntimeError(
                "voltage_kv must be one of: "
                + ", ".join(f"{value:g}" for value in available)
            )
        rng = random.Random(seed)

        def sampled(parameter):
            interval = source_class[parameter]
            return round(
                rng.uniform(float(interval["min"]), float(interval["max"])),
                6,
            )

        parameters = {
            "nominal_voltage_kv": voltage_kv,
            "short_circuit_power_mva": sampled(
                "short_circuit_power_mva"
            ),
            "positive_sequence_r_x": sampled("positive_sequence_r_x"),
            "x0_x1": sampled("x0_x1"),
            "zero_sequence_r_x": sampled("zero_sequence_r_x"),
            "voltage_setpoint_pu": sampled("voltage_setpoint_pu"),
            "initial_phase_angle_deg": sampled("initial_phase_angle_deg"),
        }
        attributes = {
            "bustp": "SL",
            "snss": parameters["short_circuit_power_mva"],
            "rntxn": parameters["positive_sequence_r_x"],
            "x0tx1": parameters["x0_x1"],
            "r0tx0": parameters["zero_sequence_r_x"],
            "usetp": parameters["voltage_setpoint_pu"],
            "phiini": parameters["initial_phase_angle_deg"],
        }
        return class_name, {
            "name": external_grid_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "voltage_class": class_name,
            "seed": seed,
            "parameters": parameters,
            "powerfactory_attributes": attributes,
            "model": database["powerfactory"]["model"],
        }

    @classmethod
    def list_evemtbench_load_profiles(
        cls,
        voltage_kv: Optional[float] = None,
    ) -> dict[str, Any]:
        """List executable Table 5 load-power profiles."""
        try:
            database = cls._load_evemtbench_load_database()
            classes = database["classes"]
            if voltage_kv is None:
                selected = classes.items()
            else:
                if isinstance(voltage_kv, bool):
                    raise ValueError
                requested = float(voltage_kv)
                selected = [
                    (name, profile)
                    for name, profile in classes.items()
                    if math.isclose(
                        float(profile["nominal_voltage_kv"]),
                        requested,
                    )
                ]
                if not selected:
                    return {
                        "success": False,
                        "message": "voltage_kv must be one of: "
                        + ", ".join(classes),
                    }
            results = [
                {"voltage_class": name, **profile}
                for name, profile in selected
            ]
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "balanced_load",
                "returned_count": len(results),
                "results": results,
                "twenty_kv_power_factor": database[
                    "twenty_kv_power_factor"
                ],
                "powerfactory": database["powerfactory"],
                "catalog_only": database["catalog_only"],
            }
        except (TypeError, ValueError):
            return {"success": False, "message": "voltage_kv must be a number"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def list_evemtbench_synchronous_machine_profiles(
        cls,
        machine_type: str = "",
    ) -> dict[str, Any]:
        """List captured Table 13 profiles without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_synchronous_machine_database()
            requested = str(machine_type or "").strip().lower()
            classes = database["classes"]
            if requested and requested not in classes:
                return {
                    "success": False,
                    "message": "machine_type must be one of: "
                    + ", ".join(classes),
                }
            selected = (
                [(requested, classes[requested])]
                if requested
                else classes.items()
            )
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "synchronous_machine",
                "returned_count": len(selected),
                "rated_voltage_rule": database["rated_voltage_rule"],
                "results": [
                    {"machine_type": name, **profile}
                    for name, profile in selected
                ],
                "powerfactory": database["powerfactory"],
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_synchronous_machine_plan(
        cls,
        machine_type: str,
        rated_power_mva: float,
        type_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_synchronous_machine_database()
        if machine_type != "round_rotor":
            if machine_type == "salient_pole":
                raise RuntimeError(
                    "salient_pole is catalog-only because Table 13 does not "
                    "provide xq transient data"
                )
            raise RuntimeError(
                "machine_type must be one of: round_rotor"
            )

        profile = database["classes"][machine_type]
        power_range = profile["rated_apparent_power_mva"]
        if not (
            float(power_range["min"])
            <= rated_power_mva
            <= float(power_range["max"])
        ):
            raise RuntimeError(
                "rated_power_mva must be between "
                f"{power_range['min']:g} and {power_range['max']:g} "
                "for round_rotor"
            )

        rated_voltage = next(
            float(rule["rated_voltage_kv"])
            for rule in database["rated_voltage_rule"]
            if rule["maximum_rated_power_mva"] is None
            or rated_power_mva
            <= float(rule["maximum_rated_power_mva"])
        )
        parameters = profile["parameters"]
        rng = random.Random(seed)

        def sampled(spec, lower=None, upper=None):
            minimum = float(spec["min"] if lower is None else lower)
            maximum = float(spec["max"] if upper is None else upper)
            if minimum > maximum:
                raise RuntimeError(
                    "Table 13 dependency constraints produced an empty "
                    "sampling interval"
                )
            return round(rng.uniform(minimum, maximum), 6)

        xdss = sampled(parameters["xd_subtransient_pu"])
        xqss_multiplier = sampled(
            parameters[
                "xq_subtransient_multiplier_of_xd_subtransient"
            ]
        )
        xqss = round(xdss * xqss_multiplier, 6)
        xds_spec = parameters["xd_transient_pu"]
        xds = sampled(
            xds_spec,
            max(
                float(xds_spec["min"]),
                float(xds_spec["minimum_multiplier_of_xd_subtransient"])
                * xdss,
                1.01 * xqss,
            ),
            float(xds_spec["max"]),
        )
        xqs_spec = parameters[
            "xq_transient_multiplier_of_xd_transient"
        ]
        xqs = sampled(
            xqs_spec,
            max(
                float(xqs_spec["min"]) * xds,
                float(xqs_spec["minimum_multiplier_of_xq_subtransient"])
                * xqss,
            ),
            float(xqs_spec["max"]) * xds,
        )
        xd_spec = parameters["xd_synchronous_pu"]
        xd = sampled(
            xd_spec,
            max(
                float(xd_spec["min"]),
                float(xd_spec["minimum_multiplier_of_xd_transient"])
                * xds,
            ),
            float(xd_spec["max"]),
        )
        xq_spec = parameters[
            "xq_synchronous_multiplier_of_xd_synchronous"
        ]
        xq = sampled(
            xq_spec,
            max(
                float(xq_spec["min"]) * xd,
                float(xq_spec["minimum_multiplier_of_xq_transient"])
                * xqs,
            ),
            float(xq_spec["max"]) * xd,
        )
        sg10 = sampled(parameters["saturation_factor_1_0_pu"])
        sg12_spec = parameters["saturation_factor_1_2_pu"]
        sg12 = sampled(
            sg12_spec,
            max(float(sg12_spec["min"]), sg10),
            float(sg12_spec["max"]),
        )
        xl_spec = parameters["leakage_reactance_pu"]
        xl = sampled(
            xl_spec,
            float(xl_spec["min"]),
            min(0.333, xdss, xqss),
        )
        x2_multiplier = sampled(
            parameters[
                "negative_sequence_reactance_multiplier_of_xd_subtransient"
            ]
        )
        source_parameters = {
            "rated_apparent_power_mva": rated_power_mva,
            "rated_voltage_kv": rated_voltage,
            "rated_power_factor": sampled(profile["rated_power_factor"]),
            "stator_resistance_pu": sampled(
                parameters["stator_resistance_pu"]
            ),
            "leakage_reactance_pu": xl,
            "xd_synchronous_pu": xd,
            "xq_synchronous_pu": xq,
            "xd_transient_pu": xds,
            "xq_transient_pu": xqs,
            "xd_subtransient_pu": xdss,
            "xq_subtransient_pu": xqss,
            "td_transient_s": sampled(parameters["td_transient_s"]),
            "tq_transient_s": sampled(parameters["tq_transient_s"]),
            "td_subtransient_s": sampled(
                parameters["td_subtransient_s"]
            ),
            "tq_subtransient_s": sampled(
                parameters["tq_subtransient_s"]
            ),
            "zero_sequence_reactance_pu": sampled(
                parameters["zero_sequence_reactance_pu"]
            ),
            "zero_sequence_resistance_pu": float(
                parameters["zero_sequence_resistance_pu"]["value"]
            ),
            "negative_sequence_reactance_pu": round(
                xdss * x2_multiplier,
                6,
            ),
            "negative_sequence_resistance_pu": sampled(
                parameters["negative_sequence_resistance_pu"]
            ),
            "acceleration_time_constant_s": sampled(
                parameters["acceleration_time_constant_s"]
            ),
            "saturation_mode": int(
                parameters["saturation_mode"]["value"]
            ),
            "saturation_factor_1_0_pu": sg10,
            "saturation_factor_1_2_pu": sg12,
            "reactive_power_max_pu": float(
                parameters["reactive_power_max_pu"]["value"]
            ),
            "reactive_power_min_pu": float(
                parameters["reactive_power_min_pu"]["value"]
            ),
        }
        mapped = database["powerfactory"]["mapped_attributes"]
        time_constant_inputs = {
            "td_transient_s": (
                source_parameters["td_transient_s"] * xd / xds
            ),
            "tq_transient_s": (
                source_parameters["tq_transient_s"] * xq / xqs
            ),
            "td_subtransient_s": (
                source_parameters["td_subtransient_s"] * xds / xdss
            ),
            "tq_subtransient_s": (
                source_parameters["tq_subtransient_s"] * xqs / xqss
            ),
        }
        attributes = {
            "iturbo": database["powerfactory"]["rotor_mode"][machine_type],
            **{
                mapped[name]: time_constant_inputs.get(name, value)
                for name, value in source_parameters.items()
            },
        }
        return {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "machine_type": machine_type,
            "seed": seed,
            "parameters": source_parameters,
            "powerfactory_attributes": attributes,
            "powerfactory_derived_attributes": {
                "tds": source_parameters["td_transient_s"],
                "tqs": source_parameters["tq_transient_s"],
                "tdss": source_parameters["td_subtransient_s"],
                "tqss": source_parameters["tq_subtransient_s"],
            },
        }

    @classmethod
    def _evemtbench_load_plan(
        cls,
        voltage_kv: float,
        load_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_load_database()
        class_name, profile = next(
            (
                (name, value)
                for name, value in database["classes"].items()
                if math.isclose(
                    float(value["nominal_voltage_kv"]),
                    voltage_kv,
                )
            ),
            (None, None),
        )
        if profile is None:
            raise RuntimeError(
                "voltage_kv must be one of: "
                + ", ".join(database["classes"])
            )
        rng = random.Random(seed)

        def sampled(interval):
            return rng.uniform(
                float(interval["min"]),
                float(interval["max"]),
            )

        if voltage_kv == 20.0:
            apparent_power = sampled(profile["apparent_power_mva"])
            power_factor = database["twenty_kv_power_factor"]
            capacitive_angle = -math.acos(
                float(power_factor["capacitive_min"])
            )
            inductive_angle = math.acos(
                float(power_factor["inductive_min"])
            )
            angle = rng.uniform(capacitive_angle, inductive_angle)
            active_power = apparent_power * math.cos(angle)
            reactive_power = apparent_power * math.sin(angle)
            source_parameters = {
                "apparent_power_mva": round(apparent_power, 6),
                "power_factor": round(math.cos(angle), 6),
                "power_factor_mode": (
                    "inductive" if angle >= 0 else "capacitive"
                ),
                "reactive_power_angle_deg": round(
                    math.degrees(angle),
                    6,
                ),
            }
        else:
            active_power = sampled(profile["active_power_mw"])
            reactive_power = sampled(profile["reactive_power_mvar"])
            source_parameters = {}

        active_power = round(active_power, 6)
        reactive_power = round(reactive_power, 6)
        return class_name, {
            "name": load_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "voltage_class": class_name,
            "seed": seed,
            "parameters": {
                "nominal_voltage_kv": voltage_kv,
                "active_power_mw": active_power,
                "reactive_power_mvar": reactive_power,
                **source_parameters,
            },
            "powerfactory_attributes": {
                "plini": active_power,
                "qlini": reactive_power,
            },
            "model": database["powerfactory"]["model"],
            "catalog_only": database["catalog_only"],
        }

    @classmethod
    def list_evemtbench_components(
        cls,
        voltage_class: str = "",
        rated_power_mva: Optional[float] = None,
    ) -> dict[str, Any]:
        """List the executable transformer catalog without opening PowerFactory."""
        try:
            database = cls._load_evemtbench_database()
            requested_class = str(voltage_class or "").strip()
            classes = database["classes"]
            if requested_class and requested_class not in classes:
                return {
                    "success": False,
                    "message": "voltage_class must be one of: "
                    + ", ".join(classes),
                }

            if rated_power_mva is not None:
                if not requested_class:
                    return {
                        "success": False,
                        "message": (
                            "voltage_class is required when rated_power_mva "
                            "is provided"
                        ),
                    }
                if isinstance(rated_power_mva, bool):
                    return {
                        "success": False,
                        "message": "rated_power_mva must be a number",
                    }
                requested_rating = float(rated_power_mva)
            else:
                requested_rating = None

            selected = (
                {requested_class: classes[requested_class]}
                if requested_class
                else classes
            )
            results = []
            for class_name, transformer_class in selected.items():
                ratings = transformer_class["ratings"]
                if requested_rating is not None:
                    ratings = [
                        rating
                        for rating in ratings
                        if math.isclose(
                            float(rating["rated_power_mva"]),
                            requested_rating,
                        )
                    ]
                    if not ratings:
                        available = ", ".join(
                            str(item["rated_power_mva"])
                            for item in transformer_class["ratings"]
                        )
                        return {
                            "success": False,
                            "message": (
                                "rated_power_mva must be one of: " + available
                            ),
                        }
                results.append({
                    "voltage_class": class_name,
                    "high_voltage_kv": transformer_class["high_voltage_kv"],
                    "low_voltage_kv": transformer_class["low_voltage_kv"],
                    "ratings": ratings,
                    "zero_sequence_rules": transformer_class[
                        "zero_sequence_rules"
                    ],
                })
            return {
                "success": True,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "component_type": "two_winding_transformer",
                "nominal_frequencies_hz": database["sampling"][
                    "nominal_frequencies_hz"
                ],
                "returned_count": len(results),
                "results": results,
                "vector_groups": database["vector_groups"],
                "saturation": database["saturation"],
                "unmapped_source_tables": database["powerfactory"][
                    "unmapped_source_tables"
                ],
                "catalog_only": database["catalog_only"],
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @classmethod
    def _evemtbench_transformer_plan(
        cls,
        voltage_class: str,
        rated_power_mva: float,
        nominal_frequency_hz: float,
        vector_group: str,
        clock_number: int,
        type_name: str,
        seed: int,
    ):
        database = cls._load_evemtbench_database()
        source = database["classes"][voltage_class]
        rng = random.Random(seed)

        def sampled(value):
            if "value" in value:
                return float(value["value"])
            return round(rng.uniform(float(value["min"]), float(value["max"])), 6)

        rating = next(
            (
                item
                for item in source["ratings"]
                if math.isclose(
                    float(item["rated_power_mva"]),
                    rated_power_mva,
                )
            ),
            None,
        )
        if rating is None:
            available = ", ".join(
                str(item["rated_power_mva"])
                for item in source["ratings"]
            )
            raise RuntimeError(
                f"rated_power_mva must be one of: {available}"
            )
        if vector_group not in rating["vector_groups"]:
            raise RuntimeError(
                "vector_group must be one of: "
                + ", ".join(rating["vector_groups"])
            )
        vector = database["vector_groups"][vector_group]
        # A blank TypTr2 needs its technology and frequency before its
        # impedance fields become usable.
        attributes = {
            "nt2ph": 3,
            "frnom": nominal_frequency_hz,
            "itrmt": 0,
            "itrdr": 0.5,
            "itrdl": 0.5,
            "it0mt": 0,
            "tr2cn_h": vector["high_winding_connection"],
            "tr2cn_l": vector["low_winding_connection"],
            "nt2ag": clock_number,
            "strn": float(rating["rated_power_mva"]),
            "utrn_h": float(source["high_voltage_kv"]),
            "utrn_l": float(source["low_voltage_kv"]),
            "uktr": sampled(rating["short_circuit_voltage_pct"]),
            "pcutr": sampled(rating["winding_losses_kw"]),
            "pfe": sampled(rating["no_load_losses_kw"]),
            "curmg": sampled(rating["no_load_current_pct"]),
        }
        return {
            "name": type_name,
            "catalog_id": database["catalog_id"],
            "source_tables": database["source"]["tables"],
            "published_vector_groups": rating["vector_groups"],
            "selected_vector_group": vector_group,
            "clock_number": clock_number,
            "clock_numbers_referenced_in_text": vector[
                "clock_numbers_referenced_in_text"
            ],
            "parameters": {
                "rated_power_mva": attributes["strn"],
                "nominal_frequency_hz": attributes["frnom"],
                "high_voltage_kv": attributes["utrn_h"],
                "low_voltage_kv": attributes["utrn_l"],
                "short_circuit_voltage_pct": attributes["uktr"],
                "winding_losses_kw": attributes["pcutr"],
                "no_load_losses_kw": attributes["pfe"],
                "no_load_current_pct": attributes["curmg"],
            },
            "powerfactory_attributes": attributes,
            "unmapped_source_tables": database["powerfactory"][
                "unmapped_source_tables"
            ],
        }

    @classmethod
    def create_evemtbench_component(
        cls,
        component_type: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Route one component request to its validated EvEMTBench creator."""
        creators = {
            "transformer": "create_evemtbench_transformer",
            "overhead_line": "create_evemtbench_line",
            "underground_cable": "create_evemtbench_cable",
            "external_grid": "create_evemtbench_external_grid",
            "load": "create_evemtbench_load",
            "synchronous_machine": "create_evemtbench_synchronous_machine",
        }
        kind = str(component_type or "").strip().lower().replace("-", "_")
        method_name = creators.get(kind)
        supported = ", ".join(creators)
        if method_name is None:
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": f"component_type must be one of: {supported}",
            }
        if not isinstance(parameters, dict):
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": "parameters must be an object",
            }

        options = dict(parameters)
        private = sorted(
            str(name) for name in options if str(name).startswith("_")
        )
        if private:
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": (
                    "parameters must not contain private options: "
                    + ", ".join(private)
                ),
            }

        creator = getattr(cls, method_name)
        try:
            inspect.signature(creator).bind(**options)
        except TypeError as exc:
            return {
                "success": False,
                "applied": False,
                "component_type": kind,
                "message": f"Invalid {kind} parameters: {exc}",
            }

        result = dict(creator(**options))
        result["component_type"] = kind
        return result

    @classmethod
    def create_evemtbench_transformer(
        cls,
        voltage_class: str,
        rated_power_mva: float,
        nominal_frequency_hz: float,
        vector_group: str,
        clock_number: int,
        transformer_name: str,
        type_name: str,
        high_voltage_bus_name: str,
        low_voltage_bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a new database-backed TypTr2 and ElmTr2."""
        voltage_class = str(voltage_class or "").strip()
        vector_group = str(vector_group or "").strip()
        transformer_name = str(transformer_name or "").strip()
        type_name = str(type_name or "").strip()
        high_bus_name = str(high_voltage_bus_name or "").strip()
        low_bus_name = str(low_voltage_bus_name or "").strip()
        created_type = None
        created_type_folder = None
        equipment_folder = None
        type_folder = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "type_created": False,
                "transformer_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        try:
            database = cls._load_evemtbench_database()
        except Exception as exc:
            return failure(str(exc))
        if voltage_class not in database["classes"]:
            return failure(
                "voltage_class must be one of: "
                + ", ".join(database["classes"])
            )
        for field_name, value in (
            ("transformer_name", transformer_name),
            ("type_name", type_name),
            ("high_voltage_bus_name", high_bus_name),
            ("low_voltage_bus_name", low_bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        for field_name, value in (
            ("transformer_name", transformer_name),
            ("type_name", type_name),
        ):
            if len(value) > cls._max_loc_name_length:
                return failure(
                    f"{field_name} must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
        if high_bus_name.casefold() == low_bus_name.casefold():
            return failure("Transformer buses must be different")
        if isinstance(rated_power_mva, bool):
            return failure("rated_power_mva must be a number")
        try:
            rated_power = float(rated_power_mva)
        except (TypeError, ValueError):
            return failure("rated_power_mva must be a number")
        if not math.isfinite(rated_power) or rated_power <= 0:
            return failure("rated_power_mva must be a finite positive number")
        if isinstance(nominal_frequency_hz, bool):
            return failure("nominal_frequency_hz must be 50 or 60")
        try:
            nominal_frequency = float(nominal_frequency_hz)
        except (TypeError, ValueError):
            return failure("nominal_frequency_hz must be 50 or 60")
        available_frequencies = database["sampling"][
            "nominal_frequencies_hz"
        ]
        if nominal_frequency not in available_frequencies:
            return failure("nominal_frequency_hz must be 50 or 60")
        if (
            isinstance(clock_number, bool)
            or not isinstance(clock_number, int)
            or not 0 <= clock_number <= 11
        ):
            return failure("clock_number must be an integer from 0 to 11")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        try:
            item = cls._evemtbench_transformer_plan(
                voltage_class,
                rated_power,
                nominal_frequency,
                vector_group,
                clock_number,
                type_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        confirmation_prefix = (
            f"CREATE {transformer_name} WITH {type_name} {voltage_class} "
            f"{rated_power:g}MVA {vector_group}{clock_number} "
            f"{nominal_frequency:g}Hz seed={seed} "
            f"grid={grid_name or '<active>'} "
            f"buses={high_voltage_bus_name}->{low_voltage_bus_name} "
            f"out_of_service={int(bool(out_of_service))}"
        )

        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")

            equipment_folder = app.GetProjectFolder("equip")
            if equipment_folder is None:
                raise RuntimeError(
                    "Equipment Type Library is unavailable: "
                    "GetProjectFolder('equip') returned None"
                )

            type_folders = cls._find_named_contents(
                equipment_folder,
                "Transformer Types",
                "IntPrjfolder",
            )
            if len(type_folders) > 1:
                raise RuntimeError(
                    "Multiple Transformer Types folders were found"
                )
            type_folder = type_folders[0] if type_folders else None

            if cls._find_named_contents(
                equipment_folder,
                type_name,
                "TypTr2",
            ):
                raise RuntimeError(
                    f"Transformer type already exists: {type_name}"
                )

            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(
                grid,
                transformer_name,
                "ElmTr2",
            ):
                raise RuntimeError(
                    f"Transformer already exists in the selected grid: "
                    f"{transformer_name}"
                )
            high_bus = cls._select_bus(grid, high_bus_name)
            low_bus = cls._select_bus(grid, low_bus_name)
            transformer_class = database["classes"][voltage_class]
            for label, bus, expected in (
                (
                    "high-voltage",
                    high_bus,
                    float(transformer_class["high_voltage_kv"]),
                ),
                (
                    "low-voltage",
                    low_bus,
                    float(transformer_class["low_voltage_kv"]),
                ),
            ):
                actual = float(bus.GetAttribute("uknom"))
                if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-6):
                    raise RuntimeError(
                        f"{label} bus nominal voltage is {actual:g} kV; "
                        f"expected {expected:g} kV for {voltage_class}"
                    )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "transformer",
                    "voltage_class": voltage_class,
                    "rated_power_mva": rated_power,
                    "nominal_frequency_hz": nominal_frequency,
                    "vector_group": vector_group,
                    "clock_number": clock_number,
                    "transformer_name": transformer_name,
                    "type_name": type_name,
                    "high_voltage_bus_name": high_bus_name,
                    "low_voltage_bus_name": low_bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_high_voltage_bus": high_bus.GetFullName(),
                    "resolved_low_voltage_bus": low_bus.GetFullName(),
                    "seed": seed,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "type_created": False,
                "transformer_created": False,
                "voltage_class": voltage_class,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "transformer_name": transformer_name,
                    "type_name": type_name,
                    "high_voltage_bus": high_bus.GetFullName(),
                    "low_voltage_bus": low_bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
                "equipment_folder": (
                    type_folder or equipment_folder
                ).GetFullName(),
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no transformer type, grid element, cubicle, "
                    "or switch was created. Tables 10 and 12 are present in "
                    "the database but remain unmapped to PowerFactory."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: {required_confirmation}",
                    item=item,
                )

            if type_folder is None:
                type_folder = equipment_folder.CreateObject(
                    "IntPrjfolder",
                    "Transformer Types",
                )
                if type_folder is None:
                    raise RuntimeError(
                        "Could not create Transformer Types folder"
                    )
                created_type_folder = type_folder

            created_type = type_folder.CreateObject("TypTr2", type_name)
            if created_type is None:
                raise RuntimeError(
                    f"Could not create transformer type: {type_name}"
                )
            if created_type.GetClassName() != "TypTr2":
                raise RuntimeError("PowerFactory created an unexpected type class")
            attributes = item["powerfactory_attributes"]
            structural_names = {
                "nt2ph",
                "frnom",
                "itrmt",
                "itrdr",
                "itrdl",
                "it0mt",
                "tr2cn_h",
                "tr2cn_l",
                "nt2ag",
            }
            structural = {
                name: value
                for name, value in attributes.items()
                if name in structural_names
            }
            electrical = {
                name: value
                for name, value in attributes.items()
                if name not in structural_names
            }
            nameplate = {
                name: electrical.pop(name)
                for name in ("strn", "utrn_h", "utrn_l")
            }
            resistance_pu = electrical["pcutr"] / (
                nameplate["strn"] * 1000.0
            )
            impedance_pu = electrical["uktr"] / 100.0
            if resistance_pu > impedance_pu:
                raise RuntimeError(
                    "Transformer copper losses exceed the sampled "
                    "short-circuit impedance"
                )
            performance = {
                "r1pu": resistance_pu,
                "x1pu": math.sqrt(
                    max(0.0, impedance_pu**2 - resistance_pu**2)
                ),
                "pfe": electrical["pfe"],
                "curmg": electrical["curmg"],
            }

            def commit_type_attributes(values, stage, direct=False):
                if direct:
                    for name, value in values.items():
                        setattr(created_type, name, value)
                        cls._verify_attributes(
                            created_type,
                            {name: value},
                            "Transformer type",
                            "immediately after direct assignment",
                        )
                else:
                    cls._set_and_verify_attributes(
                        created_type,
                        values,
                        "Transformer type",
                    )
                created_type.WriteChangesToDb()
                cls._verify_attributes(
                    created_type,
                    values,
                    "Transformer type",
                    f"after committing {stage} attributes",
                )

            commit_type_attributes(structural, "structural")
            commit_type_attributes(nameplate, "nameplate")
            commit_type_attributes(performance, "performance", direct=True)
            cls._verify_attributes(
                created_type,
                {
                    name: electrical[name]
                    for name in ("pcutr", "uktr", "pfe", "curmg")
                },
                "Transformer type",
                "after deriving source performance values",
            )
            cls._verify_attributes(
                created_type,
                attributes,
                "Transformer type",
                "after completing transformer type initialization",
            )
            if str(created_type.GetAttribute("loc_name")) != type_name:
                raise RuntimeError(
                    f"PowerFactory did not retain type name: {type_name}"
                )
            item["full_name"] = created_type.GetFullName()

            _, _, created_transformer, _ = cls._create_connected_element(
                app,
                "ElmTr2",
                "Transformer",
                transformer_name,
                (high_bus_name, low_bus_name),
                grid_name,
                attributes={
                    "typ_id": created_type,
                    "outserv": int(bool(out_of_service)),
                },
                connection_attributes=("bushv", "buslv"),
            )

            result.update({
                "applied": True,
                "type_created": True,
                "transformer_created": True,
                "created_type": created_type.GetFullName(),
                "created_transformer": created_transformer.GetFullName(),
                "message": (
                    f"Created TypTr2 '{type_name}' and connected ElmTr2 "
                    f"'{transformer_name}'"
                ),
            })
            return result

        except Exception as exc:
            rolled_back = None
            remaining_type = False
            remaining_folder = False
            if created_type is not None:
                try:
                    created_type.Delete()
                except Exception:
                    pass
                try:
                    remaining_type = bool(cls._find_named_contents(
                        equipment_folder,
                        type_name,
                        "TypTr2",
                    ))
                    rolled_back = not remaining_type
                except Exception:
                    remaining_type = True
            if created_type_folder is not None:
                try:
                    if not (created_type_folder.GetContents("*", 0) or []):
                        created_type_folder.Delete()
                except Exception:
                    pass
                try:
                    remaining_folder = bool(cls._find_named_contents(
                        equipment_folder,
                        "Transformer Types",
                        "IntPrjfolder",
                    ))
                except Exception:
                    remaining_folder = True
            if created_type is not None or created_type_folder is not None:
                rolled_back = not remaining_type and not remaining_folder
            return failure(
                str(exc),
                rolled_back=rolled_back,
                type_created=remaining_type,
                remaining_type=type_name if remaining_type else None,
                item=item,
            )

    @classmethod
    def create_evemtbench_line(
        cls,
        voltage_kv: float,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        length_km: float,
        line_name: str,
        type_name: str,
        bus1_name: str,
        bus2_name: str,
        grid_name: str = "",
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
        _database_loader=None,
        _plan_builder=None,
        _component_label: str = "overhead lines",
        _preview_message: str = "",
    ) -> dict[str, Any]:
        """Preview or create a new EvEMTBench TypLne and connected ElmLne."""
        profile = str(profile or "").strip().lower()
        line_name = str(line_name or "").strip()
        type_name = str(type_name or "").strip()
        first_bus_name = str(bus1_name or "").strip()
        second_bus_name = str(bus2_name or "").strip()
        created_type = None
        created_type_folder = None
        equipment_folder = None
        type_folder = None
        item = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "type_created": False,
                "line_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        database_loader = _database_loader or cls._load_evemtbench_line_database
        plan_builder = _plan_builder or cls._evemtbench_line_plan
        try:
            database = database_loader()
        except Exception as exc:
            return failure(str(exc))
        for field_name, value in (
            ("line_name", line_name),
            ("type_name", type_name),
            ("bus1_name", first_bus_name),
            ("bus2_name", second_bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        for field_name, value in (
            ("line_name", line_name),
            ("type_name", type_name),
        ):
            if len(value) > cls._max_loc_name_length:
                return failure(
                    f"{field_name} must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
        if first_bus_name.casefold() == second_bus_name.casefold():
            return failure("Line buses must be different")

        def positive_number(name, value):
            if isinstance(value, bool):
                raise ValueError(f"{name} must be a number")
            try:
                converted = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be a number") from exc
            if not math.isfinite(converted) or converted <= 0:
                raise ValueError(f"{name} must be a finite positive number")
            return converted

        try:
            voltage = positive_number("voltage_kv", voltage_kv)
            nominal_frequency = positive_number(
                "nominal_frequency_hz",
                nominal_frequency_hz,
            )
            rated_current = positive_number(
                "rated_current_ka",
                rated_current_ka,
            )
            line_length = positive_number("length_km", length_km)
        except ValueError as exc:
            return failure(str(exc))
        if nominal_frequency not in database["nominal_frequencies_hz"]:
            return failure("nominal_frequency_hz must be 50 or 60")

        try:
            voltage_class, line_class, item = plan_builder(
                voltage,
                nominal_frequency,
                rated_current,
                profile,
                type_name,
            )
        except Exception as exc:
            return failure(str(exc))
        length_range = line_class["length_km"]
        if not (
            float(length_range["min"])
            <= line_length
            <= float(length_range["max"])
        ):
            return failure(
                f"length_km must be between {length_range['min']:g} and "
                f"{length_range['max']:g} for {voltage_class} kV "
                f"{_component_label}",
                item=item,
            )
        current_guidance = line_class.get("rated_current_guidance_ka")
        if current_guidance and not (
            float(current_guidance["min"])
            <= rated_current
            <= float(current_guidance["max"])
        ):
            return failure(
                f"rated_current_ka must be between "
                f"{current_guidance['min']:g} and "
                f"{current_guidance['max']:g} for {voltage_class} kV "
                "overhead lines",
                item=item,
            )

        confirmation_prefix = (
            f"CREATE {line_name} WITH {type_name} {voltage_class}kV "
            f"{profile} {line_length:g}km {rated_current:g}kA "
            f"{nominal_frequency:g}Hz grid={grid_name or '<active>'} "
            f"buses={bus1_name}->{bus2_name} "
            f"out_of_service={int(bool(out_of_service))}"
        )

        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")

            equipment_folder = app.GetProjectFolder("equip")
            if equipment_folder is None:
                raise RuntimeError(
                    "Equipment Type Library is unavailable: "
                    "GetProjectFolder('equip') returned None"
                )
            type_folders = cls._find_named_contents(
                equipment_folder,
                "Line Types",
                "IntPrjfolder",
            )
            if len(type_folders) > 1:
                raise RuntimeError("Multiple Line Types folders were found")
            type_folder = type_folders[0] if type_folders else None
            if cls._find_named_contents(equipment_folder, type_name, "TypLne"):
                raise RuntimeError(f"Line type already exists: {type_name}")

            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(grid, line_name, "ElmLne"):
                raise RuntimeError(
                    f"Line already exists in the selected grid: {line_name}"
                )
            first_bus = cls._select_bus(grid, first_bus_name)
            second_bus = cls._select_bus(grid, second_bus_name)
            for label, bus in (("first", first_bus), ("second", second_bus)):
                actual = float(bus.GetAttribute("uknom"))
                if not math.isclose(actual, voltage, rel_tol=1e-9, abs_tol=1e-6):
                    raise RuntimeError(
                        f"{label} bus nominal voltage is {actual:g} kV; "
                        f"expected {voltage_class} kV"
                    )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": _component_label,
                    "line_name": line_name,
                    "type_name": type_name,
                    "voltage_kv": voltage,
                    "nominal_frequency_hz": nominal_frequency,
                    "rated_current_ka": rated_current,
                    "profile": profile,
                    "length_km": line_length,
                    "requested_bus1_name": first_bus_name,
                    "requested_bus2_name": second_bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus1": first_bus.GetFullName(),
                    "resolved_bus2": second_bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "type_created": False,
                "line_created": False,
                "voltage_class": voltage_class,
                "profile": profile,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "line_name": line_name,
                    "type_name": type_name,
                    "bus1": first_bus.GetFullName(),
                    "bus2": second_bus.GetFullName(),
                    "length_km": line_length,
                    "out_of_service": bool(out_of_service),
                },
                "equipment_folder": (
                    type_folder or equipment_folder
                ).GetFullName(),
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    _preview_message
                    or "Preview only; no line type, grid element, cubicle, or "
                    "switch was created. The profile uses the paper's "
                    "published sequence-parameter percentile, not a geometric "
                    "ULM model."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: {required_confirmation}",
                    item=item,
                )

            if type_folder is None:
                type_folder = equipment_folder.CreateObject(
                    "IntPrjfolder",
                    "Line Types",
                )
                if type_folder is None:
                    raise RuntimeError("Could not create Line Types folder")
                created_type_folder = type_folder

            created_type = type_folder.CreateObject("TypLne", type_name)
            if created_type is None:
                raise RuntimeError(f"Could not create line type: {type_name}")
            if created_type.GetClassName() != "TypLne":
                raise RuntimeError("PowerFactory created an unexpected type class")
            attributes = item["powerfactory_attributes"]
            nameplate = {
                name: attributes[name]
                for name in ("uline", "sline", "frnom")
            }
            electrical = {
                name: value
                for name, value in attributes.items()
                if name not in nameplate
            }
            cls._set_and_verify_attributes(
                created_type,
                nameplate,
                "Line type",
            )
            created_type.WriteChangesToDb()
            cls._verify_attributes(
                created_type,
                nameplate,
                "Line type",
                "after committing nameplate attributes",
            )
            cls._set_and_verify_attributes(
                created_type,
                electrical,
                "Line type",
            )
            created_type.WriteChangesToDb()
            cls._verify_attributes(
                created_type,
                attributes,
                "Line type",
                "after completing line type initialization",
            )
            if str(created_type.GetAttribute("loc_name")) != type_name:
                raise RuntimeError(
                    f"PowerFactory did not retain type name: {type_name}"
                )
            item["full_name"] = created_type.GetFullName()

            _, _, created_line, _ = cls._create_connected_element(
                app,
                "ElmLne",
                "Line",
                line_name,
                (first_bus_name, second_bus_name),
                grid_name,
                attributes={
                    "typ_id": created_type,
                    "dline": line_length,
                    "outserv": int(bool(out_of_service)),
                },
                connection_attributes=("bus1", "bus2"),
            )
            result.update({
                "applied": True,
                "type_created": True,
                "line_created": True,
                "created_type": created_type.GetFullName(),
                "created_line": created_line.GetFullName(),
                "message": (
                    f"Created TypLne '{type_name}' and connected ElmLne "
                    f"'{line_name}'"
                ),
            })
            return result

        except Exception as exc:
            rolled_back = None
            remaining_type = False
            remaining_folder = False
            if created_type is not None:
                try:
                    created_type.Delete()
                except Exception:
                    pass
                try:
                    remaining_type = bool(cls._find_named_contents(
                        equipment_folder,
                        type_name,
                        "TypLne",
                    ))
                    rolled_back = not remaining_type
                except Exception:
                    remaining_type = True
            if created_type_folder is not None:
                try:
                    if not (created_type_folder.GetContents("*", 0) or []):
                        created_type_folder.Delete()
                except Exception:
                    pass
                try:
                    remaining_folder = bool(cls._find_named_contents(
                        equipment_folder,
                        "Line Types",
                        "IntPrjfolder",
                    ))
                except Exception:
                    remaining_folder = True
            if created_type is not None or created_type_folder is not None:
                rolled_back = not remaining_type and not remaining_folder
            return failure(
                str(exc),
                rolled_back=rolled_back,
                type_created=remaining_type,
                remaining_type=type_name if remaining_type else None,
                item=item,
            )

    @classmethod
    def create_evemtbench_cable(
        cls,
        nominal_frequency_hz: float,
        rated_current_ka: float,
        profile: str,
        length_km: float,
        cable_name: str,
        type_name: str,
        bus1_name: str,
        bus2_name: str,
        grid_name: str = "",
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a Table 6 cable sequence equivalent."""
        result = cls.create_evemtbench_line(
            20.0,
            nominal_frequency_hz,
            rated_current_ka,
            profile,
            length_km,
            cable_name,
            type_name,
            bus1_name,
            bus2_name,
            grid_name,
            out_of_service,
            confirmation,
            open_digsilent,
            _database_loader=cls._load_evemtbench_cable_database,
            _plan_builder=cls._evemtbench_cable_plan,
            _component_label="underground cables",
            _preview_message=(
                "Preview only; no cable type, grid element, cubicle, or "
                "switch was created. The TypLne uses the paper's published "
                "sequence-parameter percentile, not its geometric ULM model."
            ),
        )
        result["cable_created"] = result.pop("line_created", False)
        if "created_line" in result:
            result["created_cable"] = result.pop("created_line")
        target = result.get("target")
        if isinstance(target, dict) and "line_name" in target:
            target["cable_name"] = target.pop("line_name")
        if result.get("success") and result.get("applied"):
            result["message"] = (
                f"Created TypLne '{type_name}' and connected cable ElmLne "
                f"'{str(cable_name).strip()}'"
            )
        return result

    @classmethod
    def create_evemtbench_external_grid(
        cls,
        voltage_kv: float,
        external_grid_name: str,
        bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a new Table 4 ElmXnet on an existing bus."""
        external_grid_name = str(external_grid_name or "").strip()
        bus_name = str(bus_name or "").strip()

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "external_grid_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("external_grid_name", external_grid_name),
            ("bus_name", bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        if len(external_grid_name) > cls._max_loc_name_length:
            return failure(
                "external_grid_name must be at most "
                f"{cls._max_loc_name_length} characters"
            )
        if isinstance(voltage_kv, bool):
            return failure("voltage_kv must be a number")
        try:
            voltage = float(voltage_kv)
        except (TypeError, ValueError):
            return failure("voltage_kv must be a number")
        if not math.isfinite(voltage) or voltage <= 0:
            return failure("voltage_kv must be a finite positive number")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        try:
            database = cls._load_evemtbench_external_grid_database()
            voltage_class, item = cls._evemtbench_external_grid_plan(
                voltage,
                external_grid_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        confirmation_prefix = (
            f"CREATE {external_grid_name} AT {bus_name} "
            f"{voltage:g}kV seed={seed} grid={grid_name or '<active>'} "
            f"out_of_service={int(bool(out_of_service))}"
        )
        creating = False
        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")
            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(
                grid,
                external_grid_name,
                "ElmXnet",
            ):
                raise RuntimeError(
                    "External grid already exists in the selected grid: "
                    f"{external_grid_name}"
                )
            bus = cls._select_bus(grid, bus_name)
            actual_voltage = float(bus.GetAttribute("uknom"))
            if not math.isclose(
                actual_voltage,
                voltage,
                rel_tol=1e-9,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Bus nominal voltage is {actual_voltage:g} kV; "
                    f"expected {voltage:g} kV"
                )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "external_grid",
                    "voltage_kv": voltage,
                    "external_grid_name": external_grid_name,
                    "requested_bus_name": bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus": bus.GetFullName(),
                    "seed": seed,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "external_grid_created": False,
                "voltage_class": voltage_class,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "external_grid_name": external_grid_name,
                    "bus": bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no external grid, cubicle, or switch was "
                    "created. Table 4 intervals were sampled reproducibly."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: "
                    f"{required_confirmation}",
                    item=item,
                )

            creating = True
            attributes = {
                **item["powerfactory_attributes"],
                "outserv": int(bool(out_of_service)),
            }
            _, _, created, actual = cls._create_connected_element(
                app,
                "ElmXnet",
                "External grid",
                external_grid_name,
                (bus_name,),
                grid_name,
                attributes=attributes,
                connection_attributes=("bus1",),
            )
            result.update({
                "applied": True,
                "external_grid_created": True,
                "created_external_grid": created.GetFullName(),
                "retained_powerfactory_attributes": actual,
                "message": (
                    f"Created ElmXnet '{external_grid_name}' and connected "
                    f"it to '{bus_name}'"
                ),
            })
            return result
        except Exception as exc:
            message = str(exc)
            extra = {"item": item}
            if creating:
                extra["rolled_back"] = "rolled_back=True" in message
            return failure(message, **extra)

    @classmethod
    def create_evemtbench_load(
        cls,
        voltage_kv: float,
        load_name: str,
        bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a seeded Table 5 ElmLod."""
        load_name = str(load_name or "").strip()
        bus_name = str(bus_name or "").strip()

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "load_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("load_name", load_name),
            ("bus_name", bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        if len(load_name) > cls._max_loc_name_length:
            return failure(
                "load_name must be at most "
                f"{cls._max_loc_name_length} characters"
            )
        if isinstance(voltage_kv, bool):
            return failure("voltage_kv must be a number")
        try:
            voltage = float(voltage_kv)
        except (TypeError, ValueError):
            return failure("voltage_kv must be a number")
        if not math.isfinite(voltage) or voltage <= 0:
            return failure("voltage_kv must be a finite positive number")
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        try:
            database = cls._load_evemtbench_load_database()
            voltage_class, item = cls._evemtbench_load_plan(
                voltage,
                load_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        confirmation_prefix = (
            f"CREATE {load_name} AT {bus_name} "
            f"{voltage:g}kV seed={seed} grid={grid_name or '<active>'} "
            f"out_of_service={int(bool(out_of_service))}"
        )
        creating = False
        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")
            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(grid, load_name, "ElmLod"):
                raise RuntimeError(
                    "Load already exists in the selected grid: " + load_name
                )
            bus = cls._select_bus(grid, bus_name)
            actual_voltage = float(bus.GetAttribute("uknom"))
            if not math.isclose(
                actual_voltage,
                voltage,
                rel_tol=1e-9,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Bus nominal voltage is {actual_voltage:g} kV; "
                    f"expected {voltage:g} kV"
                )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "load",
                    "voltage_kv": voltage,
                    "load_name": load_name,
                    "requested_bus_name": bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus": bus.GetFullName(),
                    "seed": seed,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "load_created": False,
                "voltage_class": voltage_class,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "load_name": load_name,
                    "bus": bus.GetFullName(),
                    "out_of_service": bool(out_of_service),
                },
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no load, cubicle, or switch was created. "
                    "Table 5 power intervals were sampled reproducibly."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    "confirmation must exactly match: "
                    + required_confirmation,
                    item=item,
                )

            creating = True
            attributes = {
                **item["powerfactory_attributes"],
                "outserv": int(bool(out_of_service)),
            }
            _, _, created, actual = cls._create_connected_element(
                app,
                "ElmLod",
                "Load",
                load_name,
                (bus_name,),
                grid_name,
                attributes=attributes,
                connection_attributes=("bus1",),
            )
            result.update({
                "applied": True,
                "load_created": True,
                "created_load": created.GetFullName(),
                "retained_powerfactory_attributes": actual,
                "message": (
                    f"Created ElmLod '{load_name}' and connected it to "
                    f"'{bus_name}'"
                ),
            })
            return result
        except Exception as exc:
            message = str(exc)
            extra = {"item": item}
            if creating:
                extra["rolled_back"] = "rolled_back=True" in message
            return failure(message, **extra)

    @classmethod
    def create_evemtbench_synchronous_machine(
        cls,
        machine_type: str,
        rated_power_mva: float,
        machine_name: str,
        type_name: str,
        bus_name: str,
        grid_name: str = "",
        seed: int = 0,
        active_power_mw: float = 0.0,
        reactive_power_mvar: float = 0.0,
        out_of_service: bool = False,
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create a seeded round-rotor TypSym and ElmSym."""
        machine_type = str(machine_type or "").strip().lower()
        machine_name = str(machine_name or "").strip()
        type_name = str(type_name or "").strip()
        bus_name = str(bus_name or "").strip()
        created_type = None
        created_type_folder = None
        equipment_folder = None
        item = None

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "type_created": False,
                "machine_created": False,
                "message": message,
            }
            result.update(extra)
            return result

        for field_name, value in (
            ("machine_name", machine_name),
            ("type_name", type_name),
            ("bus_name", bus_name),
        ):
            if not value:
                return failure(f"{field_name} must not be empty")
        for field_name, value in (
            ("machine_name", machine_name),
            ("type_name", type_name),
        ):
            if len(value) > cls._max_loc_name_length:
                return failure(
                    f"{field_name} must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
        if isinstance(seed, bool) or not isinstance(seed, int):
            return failure("seed must be an integer")

        numbers = {}
        for field_name, value in (
            ("rated_power_mva", rated_power_mva),
            ("active_power_mw", active_power_mw),
            ("reactive_power_mvar", reactive_power_mvar),
        ):
            if isinstance(value, bool):
                return failure(f"{field_name} must be a number")
            try:
                number = float(value)
            except (TypeError, ValueError):
                return failure(f"{field_name} must be a number")
            if not math.isfinite(number):
                return failure(f"{field_name} must be finite")
            numbers[field_name] = number
        rated_power = numbers["rated_power_mva"]
        active_power = numbers["active_power_mw"]
        reactive_power = numbers["reactive_power_mvar"]
        if rated_power <= 0:
            return failure("rated_power_mva must be positive")
        if active_power < 0:
            return failure("active_power_mw must be non-negative")

        try:
            database = cls._load_evemtbench_synchronous_machine_database()
            item = cls._evemtbench_synchronous_machine_plan(
                machine_type,
                rated_power,
                type_name,
                seed,
            )
        except Exception as exc:
            return failure(str(exc))

        source_parameters = item["parameters"]
        if math.hypot(active_power, reactive_power) > rated_power + 1e-9:
            return failure(
                "The requested active/reactive operating point exceeds "
                "rated_power_mva",
                item=item,
            )
        reactive_min = (
            float(source_parameters["reactive_power_min_pu"])
            * rated_power
        )
        reactive_max = (
            float(source_parameters["reactive_power_max_pu"])
            * rated_power
        )
        if not reactive_min <= reactive_power <= reactive_max:
            return failure(
                "reactive_power_mvar must be between "
                f"{reactive_min:g} and {reactive_max:g} for this type",
                item=item,
            )

        rated_voltage = float(source_parameters["rated_voltage_kv"])
        confirmation_prefix = (
            f"CREATE {machine_name} WITH {type_name} {machine_type} "
            f"{rated_power:g}MVA {rated_voltage:g}kV seed={seed} "
            f"grid={grid_name or '<active>'} bus={bus_name} "
            f"p={active_power:g}MW q={reactive_power:g}Mvar "
            f"out_of_service={int(bool(out_of_service))}"
        )
        try:
            app = cls._get_application(open_digsilent)
            if app.GetActiveProject() is None:
                raise RuntimeError("No PowerFactory project is active")

            equipment_folder = app.GetProjectFolder("equip")
            if equipment_folder is None:
                raise RuntimeError(
                    "Equipment Type Library is unavailable: "
                    "GetProjectFolder('equip') returned None"
                )
            type_folders = cls._find_named_contents(
                equipment_folder,
                "Generator Types",
                "IntPrjfolder",
            )
            if len(type_folders) > 1:
                raise RuntimeError("Multiple Generator Types folders were found")
            type_folder = type_folders[0] if type_folders else None
            if cls._find_named_contents(
                equipment_folder,
                type_name,
                "TypSym",
            ):
                raise RuntimeError(
                    f"Synchronous-machine type already exists: {type_name}"
                )

            grid = cls._select_grid(app, grid_name)
            if cls._find_named_contents(grid, machine_name, "ElmSym"):
                raise RuntimeError(
                    "Synchronous machine already exists in the selected "
                    f"grid: {machine_name}"
                )
            bus = cls._select_bus(grid, bus_name)
            actual_voltage = float(bus.GetAttribute("uknom"))
            if not math.isclose(
                actual_voltage,
                rated_voltage,
                rel_tol=1e-9,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"Bus nominal voltage is {actual_voltage:g} kV; "
                    f"expected {rated_voltage:g} kV for a "
                    f"{rated_power:g} MVA {machine_type} machine"
                )

            required_confirmation = cls._creation_confirmation_token(
                confirmation_prefix,
                {
                    "component": "synchronous_machine",
                    "machine_type": machine_type,
                    "rated_power_mva": rated_power,
                    "rated_voltage_kv": rated_voltage,
                    "machine_name": machine_name,
                    "type_name": type_name,
                    "requested_bus_name": bus_name,
                    "requested_grid_name": str(grid_name or "").strip(),
                    "resolved_grid": grid.GetFullName(),
                    "resolved_bus": bus.GetFullName(),
                    "seed": seed,
                    "active_power_mw": active_power,
                    "reactive_power_mvar": reactive_power,
                    "out_of_service": bool(out_of_service),
                },
            )

            result = {
                "success": True,
                "applied": False,
                "type_created": False,
                "machine_created": False,
                "machine_type": machine_type,
                "seed": seed,
                "catalog_id": database["catalog_id"],
                "source": database["source"],
                "affiliation": database["affiliation"],
                "target": {
                    "grid": grid.GetFullName(),
                    "machine_name": machine_name,
                    "type_name": type_name,
                    "bus": bus.GetFullName(),
                    "active_power_mw": active_power,
                    "reactive_power_mvar": reactive_power,
                    "out_of_service": bool(out_of_service),
                },
                "equipment_folder": (
                    type_folder or equipment_folder
                ).GetFullName(),
                "item": item,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no synchronous-machine type, grid "
                    "element, cubicle, or switch was created. Table 13 "
                    "ranges were sampled reproducibly."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    "confirmation must exactly match: "
                    + required_confirmation,
                    item=item,
                )

            if type_folder is None:
                type_folder = equipment_folder.CreateObject(
                    "IntPrjfolder",
                    "Generator Types",
                )
                if type_folder is None:
                    raise RuntimeError("Could not create Generator Types folder")
                created_type_folder = type_folder

            created_type = type_folder.CreateObject("TypSym", type_name)
            if created_type is None:
                raise RuntimeError(
                    f"Could not create synchronous-machine type: {type_name}"
                )
            if created_type.GetClassName() != "TypSym":
                raise RuntimeError("PowerFactory created an unexpected type class")

            attributes = item["powerfactory_attributes"]
            structural = {"iturbo": attributes["iturbo"]}
            nameplate = {
                name: attributes[name]
                for name in ("sgn", "ugn", "cosn")
            }
            electrical = {
                name: value
                for name, value in attributes.items()
                if name not in structural and name not in nameplate
            }
            for values, stage in (
                (structural, "rotor-mode"),
                (nameplate, "nameplate"),
                (electrical, "electrical"),
            ):
                cls._set_and_verify_attributes(
                    created_type,
                    values,
                    "Synchronous-machine type",
                )
                created_type.WriteChangesToDb()
                cls._verify_attributes(
                    created_type,
                    values,
                    "Synchronous-machine type",
                    f"after committing {stage} attributes",
                )
            retained_type_attributes = cls._verify_attributes(
                created_type,
                attributes,
                "Synchronous-machine type",
                "after completing type initialization",
            )
            retained_derived_attributes = cls._verify_attributes(
                created_type,
                item["powerfactory_derived_attributes"],
                "Synchronous-machine type",
                "after deriving short-circuit time constants",
            )
            if str(created_type.GetAttribute("loc_name")) != type_name:
                raise RuntimeError(
                    f"PowerFactory did not retain type name: {type_name}"
                )
            item["full_name"] = created_type.GetFullName()

            _, _, created_machine, retained_element_attributes = (
                cls._create_connected_element(
                    app,
                    "ElmSym",
                    "Synchronous machine",
                    machine_name,
                    (bus_name,),
                    grid_name,
                    attributes={
                        "typ_id": created_type,
                        "pgini": active_power,
                        "qgini": reactive_power,
                        "outserv": int(bool(out_of_service)),
                    },
                    connection_attributes=("bus1",),
                )
            )
            result.update({
                "applied": True,
                "type_created": True,
                "machine_created": True,
                "created_type": created_type.GetFullName(),
                "created_machine": created_machine.GetFullName(),
                "retained_type_attributes": retained_type_attributes,
                "retained_derived_attributes": retained_derived_attributes,
                "retained_element_attributes": retained_element_attributes,
                "message": (
                    f"Created TypSym '{type_name}' and connected ElmSym "
                    f"'{machine_name}'"
                ),
            })
            return result

        except Exception as exc:
            rolled_back = None
            remaining_type = False
            remaining_folder = False
            if created_type is not None:
                try:
                    created_type.Delete()
                except Exception:
                    pass
                try:
                    remaining_type = bool(cls._find_named_contents(
                        equipment_folder,
                        type_name,
                        "TypSym",
                    ))
                    rolled_back = not remaining_type
                except Exception:
                    remaining_type = True
            if created_type_folder is not None:
                try:
                    if not (created_type_folder.GetContents("*", 0) or []):
                        created_type_folder.Delete()
                except Exception:
                    pass
                try:
                    remaining_folder = bool(cls._find_named_contents(
                        equipment_folder,
                        "Generator Types",
                        "IntPrjfolder",
                    ))
                except Exception:
                    remaining_folder = True
            if created_type is not None or created_type_folder is not None:
                rolled_back = not remaining_type and not remaining_folder
            return failure(
                str(exc),
                rolled_back=rolled_back,
                type_created=remaining_type,
                remaining_type=type_name if remaining_type else None,
                item=item,
            )

    @classmethod
    def create_grid_with_buses(
        cls,
        grid_name: str,
        nominal_frequency_hz: float,
        buses: list[dict[str, Any]],
        confirmation: str = "",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Preview or create one ElmNet and its initial ElmTerm objects."""
        grid_name = str(grid_name or "").strip()
        project = None
        grid = None
        created_grid = None
        created_buses = []
        created_folders = []
        activated_grid = False

        def failure(message, **extra):
            result = {
                "success": False,
                "applied": False,
                "grid_created": False,
                "grid_activated": False,
                "buses_created": 0,
                "message": message,
            }
            result.update(extra)
            return result

        if not grid_name:
            return failure("grid_name must not be empty")
        if len(grid_name) > cls._max_loc_name_length:
            return failure(
                "grid_name must be at most "
                f"{cls._max_loc_name_length} characters"
            )
        if isinstance(nominal_frequency_hz, bool):
            return failure("nominal_frequency_hz must be 50 or 60")
        try:
            frequency = float(nominal_frequency_hz)
        except (TypeError, ValueError):
            return failure("nominal_frequency_hz must be 50 or 60")
        if frequency not in (50.0, 60.0):
            return failure("nominal_frequency_hz must be 50 or 60")
        if not isinstance(buses, list) or not buses:
            return failure("buses must be a non-empty list")
        if len(buses) > 100:
            return failure("buses must contain at most 100 entries")

        definitions = []
        seen_names = set()
        allowed_fields = {
            "name",
            "nominal_voltage_kv",
            "out_of_service",
        }
        for index, bus in enumerate(buses):
            if not isinstance(bus, dict):
                return failure(f"buses[{index}] must be an object")
            missing = {"name", "nominal_voltage_kv"} - set(bus)
            unexpected = set(bus) - allowed_fields
            if missing:
                return failure(
                    f"buses[{index}] is missing: {', '.join(sorted(missing))}"
                )
            if unexpected:
                return failure(
                    f"buses[{index}] has unsupported fields: "
                    + ", ".join(sorted(unexpected))
                )
            name = str(bus["name"] or "").strip()
            if not name:
                return failure(f"buses[{index}].name must not be empty")
            if len(name) > cls._max_loc_name_length:
                return failure(
                    f"buses[{index}].name must be at most "
                    f"{cls._max_loc_name_length} characters"
                )
            key = name.casefold()
            if key in seen_names:
                return failure(f"Duplicate bus name: {name}")
            seen_names.add(key)
            raw_voltage = bus["nominal_voltage_kv"]
            if isinstance(raw_voltage, bool):
                return failure(
                    f"buses[{index}].nominal_voltage_kv must be a number"
                )
            try:
                voltage = float(raw_voltage)
            except (TypeError, ValueError):
                return failure(
                    f"buses[{index}].nominal_voltage_kv must be a number"
                )
            if not math.isfinite(voltage) or voltage <= 0:
                return failure(
                    f"buses[{index}].nominal_voltage_kv must be a finite "
                    "positive number"
                )
            out_of_service = bus.get("out_of_service", False)
            if not isinstance(out_of_service, bool):
                return failure(
                    f"buses[{index}].out_of_service must be a boolean"
                )
            definitions.append({
                "name": name,
                "nominal_voltage_kv": voltage,
                "out_of_service": out_of_service,
            })

        plan_digest = hashlib.sha256(json.dumps(
            definitions,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()[:12]
        required_confirmation = (
            f"CREATE GRID {grid_name} {frequency:g}Hz WITH "
            f"{len(definitions)} BUSES plan={plan_digest}"
        )

        try:
            app = cls._get_application(open_digsilent)
            project = app.GetActiveProject()
            if project is None:
                raise RuntimeError("No PowerFactory project is active")
            if app.GetActiveStudyCase() is None:
                raise RuntimeError("No PowerFactory study case is active")

            grid_matches = cls._find_named_contents(
                project,
                grid_name,
                "ElmNet",
            )
            if len(grid_matches) > 1:
                raise RuntimeError(f"Multiple grids matched: {grid_name}")
            grid = grid_matches[0] if grid_matches else None
            active_grid_names = {
                item.GetFullName()
                for item in (app.GetCalcRelevantObjects("*.ElmNet") or [])
            }
            grid_is_active = (
                grid is not None and grid.GetFullName() in active_grid_names
            )
            if grid is not None:
                actual_frequency = float(grid.GetAttribute("frnom"))
                if not math.isclose(
                    actual_frequency,
                    frequency,
                    rel_tol=1e-6,
                    abs_tol=1e-6,
                ):
                    raise RuntimeError(
                        f"Existing grid frequency is {actual_frequency:g} Hz; "
                        f"expected {frequency:g} Hz"
                    )

            reused_buses = []
            pending_buses = []
            if grid is None:
                pending_buses = list(definitions)
            else:
                for definition in definitions:
                    matches = cls._find_named_contents(
                        grid,
                        definition["name"],
                        "ElmTerm",
                    )
                    if len(matches) > 1:
                        raise RuntimeError(
                            "Multiple buses matched: " + definition["name"]
                        )
                    if not matches:
                        pending_buses.append(definition)
                        continue
                    existing = matches[0]
                    actual_voltage = float(existing.GetAttribute("uknom"))
                    actual_outserv = bool(int(existing.GetAttribute("outserv")))
                    if not math.isclose(
                        actual_voltage,
                        definition["nominal_voltage_kv"],
                        rel_tol=1e-6,
                        abs_tol=1e-6,
                    ):
                        raise RuntimeError(
                            f"Existing bus '{definition['name']}' is "
                            f"{actual_voltage:g} kV; expected "
                            f"{definition['nominal_voltage_kv']:g} kV"
                        )
                    if actual_outserv != definition["out_of_service"]:
                        raise RuntimeError(
                            f"Existing bus '{definition['name']}' has "
                            f"out_of_service={actual_outserv}; expected "
                            f"{definition['out_of_service']}"
                        )
                    reused_buses.append(existing.GetFullName())

            result = {
                "success": True,
                "applied": False,
                "grid_created": False,
                "grid_activated": False,
                "buses_created": 0,
                "grid_will_be_created": grid is None,
                "grid_will_be_activated": not grid_is_active,
                "grid_name": grid_name,
                "nominal_frequency_hz": frequency,
                "bus_count": len(definitions),
                "buses": definitions,
                "buses_to_create": [
                    definition["name"] for definition in pending_buses
                ],
                "reused_buses": reused_buses,
                "confirmation_required": required_confirmation,
                "message": (
                    "Preview only; no grid, folder, or bus was created."
                ),
            }
            if not confirmation:
                return result
            if confirmation != required_confirmation:
                return failure(
                    f"confirmation must exactly match: {required_confirmation}"
                )
            if grid is not None and not pending_buses and grid_is_active:
                result.update({
                    "message": "Grid and all requested buses already exist",
                    "grid": grid.GetFullName(),
                })
                return result

            if grid is None:
                data_folders = cls._find_named_contents(
                    project,
                    "Network Data",
                    "IntPrjfolder",
                )
                if len(data_folders) > 1:
                    raise RuntimeError("Multiple Network Data folders were found")
                data_folder = data_folders[0] if data_folders else None
                if data_folder is None:
                    model_folders = cls._find_named_contents(
                        project,
                        "Network Model",
                        "IntPrjfolder",
                    )
                    if len(model_folders) > 1:
                        raise RuntimeError(
                            "Multiple Network Model folders were found"
                        )
                    model_folder = (
                        model_folders[0] if model_folders else None
                    )
                    if model_folder is None:
                        model_folder = project.CreateObject(
                            "IntPrjfolder",
                            "Network Model",
                        )
                        if model_folder is None:
                            raise RuntimeError(
                                "Could not create Network Model folder"
                            )
                        created_folders.append((project, model_folder))
                    data_folder = model_folder.CreateObject(
                        "IntPrjfolder",
                        "Network Data",
                    )
                    if data_folder is None:
                        raise RuntimeError("Could not create Network Data folder")
                    created_folders.append((model_folder, data_folder))

                grid = data_folder.CreateObject("ElmNet", grid_name)
                if grid is None:
                    raise RuntimeError(f"Could not create grid: {grid_name}")
                created_grid = grid
                cls._set_and_verify_attributes(
                    grid,
                    {"frnom": frequency},
                    "Grid",
                )
                if str(grid.GetAttribute("loc_name")) != grid_name:
                    raise RuntimeError(
                        f"PowerFactory did not retain grid name: {grid_name}"
                    )

            if not grid_is_active:
                activation_code = grid.Activate()
                if activation_code not in (None, 0):
                    raise RuntimeError(
                        "Could not activate grid: "
                        f"{grid_name} (error code {activation_code})"
                    )
                activated_grid = True
                active_grid_names = {
                    item.GetFullName()
                    for item in (app.GetCalcRelevantObjects("*.ElmNet") or [])
                }
                if grid.GetFullName() not in active_grid_names:
                    raise RuntimeError(
                        "Grid activation did not make the grid "
                        f"calculation-relevant: {grid_name}"
                    )

            for definition in pending_buses:
                bus = grid.CreateObject("ElmTerm", definition["name"])
                if bus is None:
                    raise RuntimeError(
                        f"Could not create bus: {definition['name']}"
                    )
                created_buses.append(bus)
                cls._set_and_verify_attributes(
                    bus,
                    {
                        "uknom": definition["nominal_voltage_kv"],
                        "outserv": int(definition["out_of_service"]),
                    },
                    "Bus",
                )
                if str(bus.GetAttribute("loc_name")) != definition["name"]:
                    raise RuntimeError(
                        "PowerFactory did not retain bus name: "
                        + definition["name"]
                    )

            if created_grid is not None:
                message = (
                    f"Created and activated grid '{grid_name}' with "
                    f"{len(created_buses)} bus(es)"
                )
            elif activated_grid and not created_buses:
                message = f"Activated existing grid '{grid_name}'"
            else:
                message = (
                    f"Added {len(created_buses)} bus(es) to grid "
                    f"'{grid_name}'"
                )

            result.update({
                "applied": True,
                "grid_created": created_grid is not None,
                "grid_activated": activated_grid,
                "buses_created": len(created_buses),
                "grid": grid.GetFullName(),
                "created_buses": [
                    bus.GetFullName() for bus in created_buses
                ],
                "message": message,
            })
            return result

        except Exception as exc:
            for bus in reversed(created_buses):
                try:
                    bus.Delete()
                except Exception:
                    pass
            if activated_grid:
                try:
                    grid.Deactivate()
                except Exception:
                    pass
            if created_grid is not None:
                try:
                    created_grid.Delete()
                except Exception:
                    pass
            for parent, folder in reversed(created_folders):
                try:
                    if not (folder.GetContents("*", 0) or []):
                        folder.Delete()
                except Exception:
                    pass

            remaining = []
            try:
                if created_grid is not None and cls._find_named_contents(
                    project,
                    grid_name,
                    "ElmNet",
                ):
                    remaining.append(grid_name)
                elif grid is not None:
                    for bus in created_buses:
                        name = str(bus.GetAttribute("loc_name"))
                        if cls._find_named_contents(grid, name, "ElmTerm"):
                            remaining.append(name)
                for parent, folder in created_folders:
                    name = str(folder.GetAttribute("loc_name"))
                    if cls._find_named_contents(parent, name, "IntPrjfolder"):
                        remaining.append(name)
                if activated_grid and created_grid is None:
                    active_names = {
                        item.GetFullName()
                        for item in (
                            app.GetCalcRelevantObjects("*.ElmNet") or []
                        )
                    }
                    if grid.GetFullName() in active_names:
                        remaining.append(f"{grid_name} (active)")
            except Exception:
                remaining.append("rollback verification failed")
            return failure(
                str(exc),
                rolled_back=not remaining,
                remaining_objects=remaining,
            )

    @staticmethod
    def _select_grid(app, grid_name: str):
        grids = app.GetCalcRelevantObjects("*.ElmNet") or []
        if not grids:
            raise RuntimeError("No calculation-relevant grids were found")

        requested = str(grid_name or "").strip()
        if requested:
            matches = [
                grid
                for grid in grids
                if str(grid.GetAttribute("loc_name")).casefold()
                == requested.casefold()
            ]
            if matches:
                return matches[0]

            available = ", ".join(
                str(grid.GetAttribute("loc_name"))
                for grid in grids
            )
            raise RuntimeError(
                f"Grid not found: {requested}. Available grids: {available}"
            )

        if len(grids) == 1:
            return grids[0]

        available = ", ".join(
            str(grid.GetAttribute("loc_name"))
            for grid in grids
        )
        raise RuntimeError(
            "Multiple grids are active; provide grid_name. "
            f"Available grids: {available}"
        )

    @staticmethod
    def _select_bus(grid, bus_name: str):
        requested = str(bus_name or "").strip()
        matches = DIgSILENTAgent._find_named_contents(
            grid,
            requested,
            "ElmTerm",
        )

        if not matches:
            raise RuntimeError(
                f"Bus not found in the selected grid: {requested}"
            )
        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple buses matched: {requested}"
            )

        return matches[0]

    @classmethod
    def _get_application(cls, open_digsilent: bool = True):
        global pf
        if pf is None:
            _ensure_powerfactory_on_path()
            import powerfactory as pf

        if cls._shared_app is None:
            app = pf.GetApplicationExt()
            if app is None:
                raise RuntimeError("GetApplicationExt() returned None")
            cls._shared_app = app
        else:
            app = cls._shared_app

        cls._apply_show_preference(app, open_digsilent)
        return app

    @staticmethod
    def _get_template_type(
        app,
        template_query: str,
        class_name: str,
        label: str,
        type_label: str,
    ):
        templates = (
            app.GetCalcRelevantObjects(template_query) or []
        )
        if not templates:
            raise RuntimeError(
                f"Template {label} not found: {template_query}"
            )
        if len(templates) > 1:
            raise RuntimeError(
                f"Multiple template {label}s matched: {template_query}"
            )

        template = templates[0]
        if template.GetClassName() != class_name:
            raise RuntimeError(
                f"template_{label} must reference an {class_name}"
            )

        template_type = template.GetAttribute("typ_id")
        if template_type is None:
            raise RuntimeError(
                f"Template {label} has no {type_label}"
            )
        return template_type

    @staticmethod
    def _set_and_verify_attributes(element, expected, component_label):
        for attribute, value in expected.items():
            element.SetAttribute(attribute, value)
            DIgSILENTAgent._verify_attributes(
                element,
                {attribute: value},
                component_label,
                "immediately after assignment",
            )

        return DIgSILENTAgent._verify_attributes(
            element,
            expected,
            component_label,
            "after all assignments",
        )

    @staticmethod
    def _verify_attributes(
        element,
        expected,
        component_label,
        stage="",
    ):
        import math

        labels = {
            "uknom": "nominal voltage",
            "outserv": "service state",
            "plini": "active power",
            "qlini": "reactive power",
            "pgini": "active power",
            "qgini": "reactive power",
            "dline": "line length",
            "typ_id": f"{component_label.lower()} type",
        }

        actual = {}
        for attribute, expected_value in expected.items():
            actual_value = element.GetAttribute(attribute)
            actual[attribute] = actual_value

            try:
                if isinstance(expected_value, float):
                    matches = math.isclose(
                        float(actual_value),
                        expected_value,
                        rel_tol=1e-6,
                        abs_tol=1e-6,
                    )
                elif hasattr(expected_value, "GetFullName"):
                    matches = (
                        actual_value is not None
                        and actual_value.GetFullName()
                        == expected_value.GetFullName()
                    )
                else:
                    matches = actual_value == expected_value
            except Exception:
                matches = False

            if not matches:
                raise RuntimeError(
                    "PowerFactory did not retain the "
                    f"{labels.get(attribute, attribute)}: "
                    f"expected {expected_value!r}, got {actual_value!r}"
                    + (f" {stage}" if stage else "")
                )

        return actual

    @classmethod
    def _rollback_connected_element(
        cls,
        grid,
        buses,
        element,
        cubicles,
        class_name: str,
        element_name: str,
    ) -> bool:
        if not isinstance(buses, (list, tuple)):
            buses = (buses,)
        if not isinstance(cubicles, (list, tuple)):
            cubicles = (cubicles,)
        try:
            retained_element_name = (
                str(element.GetAttribute("loc_name"))
                if element is not None
                else element_name
            )
            retained_cubicle_names = tuple(
                str(cubicle.GetAttribute("loc_name"))
                for cubicle in cubicles
            )
        except Exception:
            return False

        for created_object in (element, *cubicles):
            if created_object is not None:
                try:
                    created_object.Delete()
                except Exception:
                    pass

        try:
            element_exists = bool(cls._find_named_contents(
                grid,
                retained_element_name,
                class_name,
            ))
            cubicle_exists = any(
                cls._find_named_contents(
                    bus,
                    cubicle_name,
                    "StaCubic",
                )
                for bus, cubicle_name in zip(
                    buses,
                    retained_cubicle_names,
                )
            )
            return not element_exists and not cubicle_exists
        except Exception:
            return False

    @classmethod
    def _generated_cubicle_names(cls, element_name: str, count: int):
        return tuple(
            (
                f"{element_name} Cubicle"
                + (f" {index}" if count > 1 else "")
            )[:cls._max_loc_name_length]
            for index in range(1, count + 1)
        )

    @classmethod
    def _is_generated_cubicle(cls, cubicle, expected_name: str) -> bool:
        try:
            if (
                str(cubicle.GetAttribute("loc_name")).strip()
                != expected_name.strip()
            ):
                return False
            contents = cubicle.GetContents("*", 0) or []
            if len(contents) != 1:
                return False
            switch = contents[0]
            return (
                switch.GetClassName() == "StaSwitch"
                and str(switch.GetAttribute("loc_name")) == "Switch"
                and switch.GetAttribute("aUsage") == "cbk"
            )
        except Exception:
            return False

    @classmethod
    def _create_connected_element(
        cls,
        app,
        class_name: str,
        element_label: str,
        element_name: str,
        bus_names,
        grid_name: str,
        attributes=None,
        connection_attributes=("bus1",),
    ):
        grid = cls._select_grid(app, grid_name)

        if cls._find_named_contents(grid, element_name, class_name):
            raise RuntimeError(
                f"{element_label} already exists in the selected grid: "
                f"{element_name}"
            )

        bus_names = tuple(bus_names)
        connection_attributes = tuple(connection_attributes)
        if len(bus_names) != len(connection_attributes):
            raise RuntimeError(
                "Bus names and connection attributes must have equal length"
            )

        buses = tuple(
            cls._select_bus(grid, bus_name)
            for bus_name in bus_names
        )
        if (
            len(buses) > 1
            and len({bus.GetFullName() for bus in buses}) != len(buses)
        ):
            raise RuntimeError(
                "The two terminals must use different buses"
            )

        cubicle_names = cls._generated_cubicle_names(
            element_name,
            len(buses),
        )

        for bus, cubicle_name in zip(buses, cubicle_names):
            if cls._find_named_contents(
                bus,
                cubicle_name,
                "StaCubic",
            ):
                raise RuntimeError(
                    f"Cubicle already exists on bus: {cubicle_name}"
                )

        cubicles = []
        element = None

        try:
            for bus, cubicle_name in zip(buses, cubicle_names):
                cubicle = bus.CreateObject(
                    "StaCubic",
                    cubicle_name,
                )
                if cubicle is None:
                    raise RuntimeError(
                        "Could not create cubicle on bus: "
                        f"{bus.GetAttribute('loc_name')}"
                    )
                cubicles.append(cubicle)

                switch = cubicle.CreateObject("StaSwitch", "Switch")
                if switch is None:
                    raise RuntimeError(
                        "Could not create circuit-breaker in cubicle: "
                        f"{cubicle_name}"
                    )

                switch.SetAttribute("aUsage", "cbk")
                switch.SetAttribute("on_off", 1)

                if (
                    switch.GetAttribute("aUsage") != "cbk"
                    or switch.GetAttribute("on_off") != 1
                ):
                    raise RuntimeError(
                        "PowerFactory did not retain the circuit-breaker settings"
                    )

            element = grid.CreateObject(class_name, element_name)
            if element is None:
                raise RuntimeError(
                    f"Could not create {element_label.lower()}: "
                    f"{element_name}"
                )

            for attribute, cubicle in zip(
                connection_attributes,
                cubicles,
            ):
                element.SetAttribute(attribute, cubicle)
                actual_cubicle = element.GetAttribute(attribute)
                if (
                    actual_cubicle is None
                    or actual_cubicle.GetFullName()
                    != cubicle.GetFullName()
                ):
                    raise RuntimeError(
                        "PowerFactory did not retain the bus connection"
                    )

            actual = cls._set_and_verify_attributes(
                element,
                attributes or {},
                element_label,
            )
            if str(element.GetAttribute("loc_name")) != element_name:
                raise RuntimeError(
                    "PowerFactory did not retain the "
                    f"{element_label.lower()} name"
                )

            return grid, buses, element, actual

        except Exception as exc:
            message = str(exc)

            if element is not None or cubicles:
                rolled_back = cls._rollback_connected_element(
                    grid,
                    buses,
                    element,
                    tuple(cubicles),
                    class_name,
                    element_name,
                )
                message += f" | rolled_back={rolled_back}"

            raise RuntimeError(message) from exc

    @classmethod
    def _update_active_diagram(cls, app, component) -> None:
        """Insert and verify a component in the active diagram."""
        desktop = app.GetDesktop()
        if desktop is None:
            raise RuntimeError("No active PowerFactory graphics desktop")

        layout = app.GetFromStudyCase("ComSgllayout")
        if layout is None:
            raise RuntimeError("Diagram Layout Tool is unavailable")

        def restore_state():
            desktop.Freeze()

        desktop.Unfreeze()
        try:
            layout.iAction = 1
            layout.insertionMode = 1

            result = layout.Execute()
            if result not in (0, None):
                raise RuntimeError(
                    f"Diagram Layout Tool failed with error code {result}"
                )
            app.Rebuild()
        except BaseException:
            try:
                restore_state()
            except Exception:
                pass
            raise
        else:
            restore_state()

        graphics = cls._find_component_graphics(app, component)
        if not graphics:
            raise RuntimeError(
                "Diagram Layout Tool did not insert the created component"
            )

    @staticmethod
    def _find_component_graphics(app, component):
        """Find every diagram object representing the component."""
        project = app.GetActiveProject()
        if project is None:
            raise RuntimeError("No active PowerFactory project")

        component_full_name = component.GetFullName()
        matches = []

        for diagram in project.GetContents("*.IntGrfnet", 1) or []:
            for graphic in diagram.GetContents("*.IntGrf", 1) or []:
                try:
                    data_object = graphic.GetAttribute("pDataObj")
                except Exception:
                    continue

                if data_object is None:
                    continue

                try:
                    is_match = (
                        data_object.GetFullName() == component_full_name
                    )
                except Exception:
                    is_match = False

                if is_match:
                    matches.append(graphic)

        return matches

    @classmethod
    def add_component(
        cls,
        component_type: str,
        component_name: str,
        parameters: dict,
        grid_name: str = "",
        out_of_service: bool = False,
        open_digsilent: bool = True,
        update_graphics: bool = False,
    ) -> tuple[bool, str]:
        """Create one supported component, verifying and rolling it back."""
        import math

        kind = str(component_type or "").strip().lower()
        name = str(component_name or "").strip()

        spec = cls._component_specs.get(kind)
        if spec is None:
            return (
                False,
                f"Unsupported component type: {component_type}. "
                f"Supported types: {', '.join(cls._component_specs)}",
            )

        if not isinstance(parameters, dict):
            return False, "parameters must be an object"
        if not name:
            return False, "component_name must not be empty"
        if len(name) > cls._max_loc_name_length:
            return (
                False,
                "component_name must be at most "
                f"{cls._max_loc_name_length} characters",
            )

        required = spec["required"]
        optional = spec["optional"]
        supplied = set(parameters)
        missing = sorted(required - supplied)
        unexpected = sorted(supplied - required - optional)

        if missing:
            return (
                False,
                f"Missing parameter(s) for {kind}: {', '.join(missing)}",
            )

        if unexpected:
            return (
                False,
                f"Unsupported parameter(s) for {kind}: "
                f"{', '.join(unexpected)}",
            )

        def required_text(key):
            raw_value = parameters[key]
            value = "" if raw_value is None else str(raw_value).strip()
            if not value:
                raise RuntimeError(f"{key} must not be empty")
            return value

        def number(
            key,
            *,
            positive=False,
            non_negative=False,
            default=None,
        ):
            raw_value = parameters.get(key)
            if raw_value is None and default is not None:
                raw_value = default
            if isinstance(raw_value, bool):
                raise RuntimeError(f"{key} must be a number")
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"{key} must be a number") from exc
            if positive and (not math.isfinite(value) or value <= 0):
                raise RuntimeError(f"{key} must be a finite positive number")
            if non_negative and (not math.isfinite(value) or value < 0):
                raise RuntimeError(f"{key} must be finite and non-negative")
            if not positive and not non_negative and not math.isfinite(value):
                raise RuntimeError(f"{key} must be finite")
            return value

        try:
            class_name = spec["class_name"]
            label = spec["label"]
            buses = tuple(
                required_text(parameter)
                for parameter in spec["bus_parameters"]
            )
            connections = spec["connections"]
            outserv = int(bool(out_of_service))
            attributes = {"outserv": outserv}
            for attribute, parameter, rule, default in spec["numbers"]:
                attributes[attribute] = number(
                    parameter,
                    positive=rule == "positive",
                    non_negative=rule == "non_negative",
                    default=default,
                )

            if len(buses) == 2 and buses[0].casefold() == buses[1].casefold():
                raise RuntimeError(f"{label} buses must be different")

            app = cls._get_application(open_digsilent)
            template_query = ""
            if spec["template"]:
                template_parameter, template_label, type_label = (
                    spec["template"]
                )
                template_query = required_text(template_parameter)
                attributes["typ_id"] = cls._get_template_type(
                    app,
                    template_query,
                    class_name,
                    template_label,
                    type_label,
                )

            grid, _, created, actual = cls._create_connected_element(
                app,
                class_name,
                label,
                name,
                buses,
                grid_name,
                attributes=attributes,
                connection_attributes=connections,
            )

            graphics_status = "not_requested"

            if update_graphics:
                try:
                    cls._update_active_diagram(app, created)
                    graphics_status = "updated"
                except Exception as exc:
                    message = (
                        f"{label} '{name}' was created, but graphical "
                        f"update failed: {exc}"
                    )
                    log.error(message)
                    return False, message

            full_name = created.GetFullName()
            service_state = bool(int(actual["outserv"]))
            if not buses:
                voltage = float(actual["uknom"])
                grid_label = str(grid.GetAttribute("loc_name"))
                log.ok(
                    f"Created bus '{name}' in grid '{grid_label}' "
                    f"at {voltage} kV"
                )
            elif len(buses) == 1:
                log.ok(
                    f"Created {kind} '{name}' on bus '{buses[0]}'"
                )
            else:
                log.ok(
                    f"Created {kind} '{name}' between "
                    f"'{buses[0]}' and '{buses[1]}'"
                )

            details = [
                f"{detail_name}={bus_name}"
                for detail_name, bus_name in zip(
                    spec["bus_details"],
                    buses,
                )
            ]
            if template_query:
                details.append(f"template={template_query}")
            details.extend(
                f"{parameter}={float(actual[attribute])}"
                for attribute, parameter, _, _ in spec["numbers"]
            )

            return (
                True,
                f"Created {kind}: {full_name} | {' | '.join(details)} | "
                f"out_of_service={service_state} | "
                f"graphics={graphics_status}",
            )

        except Exception as exc:
            message = str(exc)
            log.error(f"{kind.capitalize()} creation failed: {message}")
            return False, message

    @classmethod
    def delete_component(
        cls,
        component_type: str,
        component_name: str,
        grid_name: str = "",
        confirmation: str = "",
        open_digsilent: bool = True,
        update_graphics: bool = False,
    ) -> dict[str, Any]:
        """Preview or delete one exactly named supported grid component."""
        kind = str(component_type or "").strip().lower()
        name = str(component_name or "").strip()
        deleted = False
        graphics_status = {
            "requested": bool(update_graphics),
            "matched": 0,
            "deleted": 0,
            "remaining": [],
            "refresh": "not_requested",
        }

        def result(success: bool, message: str) -> dict[str, Any]:
            return {
                "success": success,
                "deleted": deleted,
                "graphics": graphics_status,
                "message": message,
            }

        spec = cls._component_specs.get(kind)
        if spec is None:
            return result(False, (
                "component_type must be one of: "
                + ", ".join(cls._component_specs)
            ))
        if not name:
            return result(False, "component_name must not be empty")

        try:
            app = cls._get_application(open_digsilent)
            grid = cls._select_grid(app, grid_name)
            class_name = spec["class_name"]
            connection_attributes = spec["connections"]

            matches = cls._find_named_contents(grid, name, class_name)
            if not matches:
                raise RuntimeError(
                    f"{kind.capitalize()} not found in the selected grid: "
                    f"{name}"
                )
            if len(matches) > 1:
                raise RuntimeError(
                    f"Multiple {kind}s matched the exact name: {name}"
                )

            component = matches[0]
            name = str(component.GetAttribute("loc_name"))
            cubicles = []

            if kind == "bus":
                connected = [
                    cubicle
                    for cubicle in (
                        component.GetContents("*.StaCubic", 1) or []
                    )
                    if cubicle.GetAttribute("obj_id") is not None
                ]
                if connected:
                    raise RuntimeError(
                        "Bus has connected cubicles; delete its connected "
                        "components first"
                    )
            else:
                for attribute in connection_attributes:
                    cubicle = component.GetAttribute(attribute)
                    if cubicle is not None and cubicle not in cubicles:
                        cubicles.append(cubicle)

            expected_cubicle_names = cls._generated_cubicle_names(
                name,
                len(connection_attributes),
            )
            generated_cubicles = [
                cubicle
                for cubicle, expected_name in zip(
                    cubicles,
                    expected_cubicle_names,
                )
                if cls._is_generated_cubicle(cubicle, expected_name)
            ]
            preserved_cubicles = [
                cubicle
                for cubicle in cubicles
                if cubicle not in generated_cubicles
            ]

            required = f"DELETE {kind} {component.GetFullName()}"

            if not confirmation:
                return result(True, (
                    f"Preview only: {component.GetFullName()} | "
                    f"confirmation_required={required}"
                ))

            if confirmation != required:
                raise RuntimeError(
                    f"confirmation must exactly match: {required}"
                )

            cubicle_locations = [
                (cubicle.GetParent(), cubicle.GetFullName())
                for cubicle in generated_cubicles
            ]

            graphics = (
                cls._find_component_graphics(app, component)
                if update_graphics
                else []
            )
            graphics_status["matched"] = len(graphics)

            graphic_locations = [
                (graphic.GetParent(), graphic.GetFullName())
                for graphic in graphics
            ]

            component.Delete()

            still_exists = bool(cls._find_named_contents(
                grid,
                name,
                class_name,
            ))
            if still_exists:
                raise RuntimeError(
                    "PowerFactory did not delete the component; "
                    "cubicles were left unchanged"
                )
            deleted = True

            for graphic in graphics:
                try:
                    graphic.Delete()
                except Exception:
                    pass

            for cubicle in generated_cubicles:
                try:
                    cubicle.Delete()
                except Exception:
                    pass

            remaining_graphics = [
                full_name
                for parent, full_name in graphic_locations
                if any(
                    obj.GetFullName() == full_name
                    for obj in (
                        parent.GetContents("*.IntGrf", 1) or []
                    )
                )
            ]

            remaining_cubicles = [
                full_name
                for parent, full_name in cubicle_locations
                if any(
                    obj.GetFullName() == full_name
                    for obj in (
                        parent.GetContents("*.StaCubic", 1) or []
                    )
                )
            ]

            graphics_status["deleted"] = (
                len(graphics) - len(remaining_graphics)
            )
            graphics_status["remaining"] = remaining_graphics
            cleanup_errors = []

            if remaining_graphics:
                cleanup_errors.append(
                    "graphical objects remain: "
                    + ", ".join(remaining_graphics)
                )

            if remaining_cubicles:
                cleanup_errors.append(
                    "connected cubicles remain: "
                    + ", ".join(remaining_cubicles)
                )

            if update_graphics:
                try:
                    app.Rebuild()
                    graphics_status["refresh"] = "rebuilt"
                except Exception as exc:
                    graphics_status["refresh"] = f"failed:{exc}"
                    cleanup_errors.append(
                        f"graphical refresh failed: {exc}"
                    )

            if cleanup_errors:
                message = "Component deleted, but " + "; ".join(
                    cleanup_errors
                )
                log.error(f"Component deletion incomplete: {message}")
                return result(False, message)

            message = f"Deleted {kind}: {name}"
            if preserved_cubicles:
                message += (
                    f" | preserved_cubicles={len(preserved_cubicles)}"
                )
            if update_graphics:
                message += (
                    f" | graphics_deleted={graphics_status['deleted']}"
                    f" | graphics_refresh={graphics_status['refresh']}"
                )
            log.ok(message)
            return result(True, message)

        except Exception as exc:
            message = str(exc)
            log.error(f"Component deletion failed: {message}")
            return result(False, message)

    # ──────────────────────────────────────────────────────────────
    # LOAD FLOW — run ComLdf on the currently active study case
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def _export_loadflow_snapshot_to_csv(
        cls,
        app,
        output_dir: str,
        run_label: str,
    ) -> tuple[bool, str]:
        """Export a point-in-time load-flow snapshot to CSV."""
        try:
            safe_label = _safe_path_label(run_label)
            base_dir = _ensure_output_directory(
                output_dir or r"C:\RMS_Results",
                purpose="configured output directory",
            )
            run_dir = checked_path(
                os.path.join(base_dir, safe_label),
                purpose="generated load flow directory",
                for_write=True,
            )
            os.makedirs(run_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = checked_path(
                os.path.join(run_dir, f"{safe_label}_loadflow_{timestamp}.csv"),
                purpose="generated load flow CSV path",
                for_write=True,
            )

            fieldnames = [
                "element_type",
                "e:loc_name",
                "m:u",
                "m:phiu",
                "m:P:bus1",
                "m:Q:bus1",
                "e:plini",
                "e:qlini",
                "c:loading",
                "n:Pflow:bus1",
            ]

            def _safe_get_attr(obj, attr_name: str):
                try:
                    return obj.GetAttribute(attr_name)
                except Exception:
                    return None

            def _name_of(obj) -> str:
                return str(getattr(obj, "loc_name", str(obj)))

            def _scalar(value):
                if value is None:
                    return ""
                if isinstance(value, (str, int, float, bool)):
                    return value
                return str(value)

            rows = []

            buses = app.GetCalcRelevantObjects("*.ElmTerm") or []
            for obj in sorted(buses, key=_name_of):
                rows.append({
                    "element_type": "ElmTerm",
                    "e:loc_name": _name_of(obj),
                    "m:u": _scalar(_safe_get_attr(obj, "m:u")),
                    "m:phiu": _scalar(_safe_get_attr(obj, "m:phiu")),
                    "m:P:bus1": "",
                    "m:Q:bus1": "",
                    "e:plini": "",
                    "e:qlini": "",
                    "c:loading": "",
                    "n:Pflow:bus1": "",
                })

            generators = app.GetCalcRelevantObjects("*.ElmSym") or []
            for obj in sorted(generators, key=_name_of):
                rows.append({
                    "element_type": "ElmSym",
                    "e:loc_name": _name_of(obj),
                    "m:u": "",
                    "m:phiu": "",
                    "m:P:bus1": _scalar(_safe_get_attr(obj, "m:P:bus1")),
                    "m:Q:bus1": _scalar(_safe_get_attr(obj, "m:Q:bus1")),
                    "e:plini": "",
                    "e:qlini": "",
                    "c:loading": "",
                    "n:Pflow:bus1": "",
                })

            loads = app.GetCalcRelevantObjects("*.ElmLod") or []
            for obj in sorted(loads, key=_name_of):
                rows.append({
                    "element_type": "ElmLod",
                    "e:loc_name": _name_of(obj),
                    "m:u": "",
                    "m:phiu": "",
                    "m:P:bus1": "",
                    "m:Q:bus1": "",
                    "e:plini": _scalar(_safe_get_attr(obj, "e:plini")),
                    "e:qlini": _scalar(_safe_get_attr(obj, "e:qlini")),
                    "c:loading": "",
                    "n:Pflow:bus1": "",
                })

            lines = app.GetCalcRelevantObjects("*.ElmLne") or []
            for obj in sorted(lines, key=_name_of):
                rows.append({
                    "element_type": "ElmLne",
                    "e:loc_name": _name_of(obj),
                    "m:u": "",
                    "m:phiu": "",
                    "m:P:bus1": "",
                    "m:Q:bus1": "",
                    "e:plini": "",
                    "e:qlini": "",
                    "c:loading": _scalar(_safe_get_attr(obj, "c:loading")),
                    "n:Pflow:bus1": _scalar(_safe_get_attr(obj, "n:Pflow:bus1")),
                })

            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            return True, csv_path
        except Exception as e:
            return False, str(e)

    @classmethod
    def load_flow(
        cls,
        open_digsilent: bool = True,
        save_csv: bool = False,
        output_dir: str = r"C:\RMS_Results",
        run_label: str = "run_001",
    ) -> tuple[bool, str]:
        """Run a load flow (ComLdf) on the currently active study case."""
        try:
            app = cls._get_application(open_digsilent)

            ldf = app.GetFromStudyCase('ComLdf')
            if ldf is None:
                raise RuntimeError("ComLdf not found in study case")
            err = ldf.Execute()
            if err:
                raise RuntimeError(f"ComLdf returned error code {err}")

            if save_csv:
                ok_csv, csv_msg = cls._export_loadflow_snapshot_to_csv(app, output_dir, run_label)
                if not ok_csv:
                    raise RuntimeError(f"Load flow OK, but CSV export failed: {csv_msg}")
                log.ok(f"Load flow CSV saved → {csv_msg}")
                return True, f"Load flow OK | CSV saved to {csv_msg}"

            log.ok("Load flow converged successfully")
            return True, "Load flow OK"
        except Exception as e:
            log.error(f"Load flow failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # SHORT CIRCUIT — run ComShc on the currently active study case
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def short_circuit(cls, open_digsilent: bool = True) -> tuple[bool, str]:
        """Run a short-circuit calculation (ComShc) on the currently active study case."""
        try:
            app = cls._get_application(open_digsilent)

            shc = app.GetFromStudyCase('ComShc')
            if shc is None:
                raise RuntimeError("ComShc not found in study case")
            err = shc.Execute()
            if err:
                raise RuntimeError(f"ComShc returned error code {err}")
            log.ok("Short-circuit calculation completed")
            return True, "Short-circuit calculation OK"
        except Exception as e:
            log.error(f"Short-circuit calculation failed: {e}")
            return False, str(e)

    @classmethod
    def create_contingency(
        cls,
        case_name: str,
        target_query: str,
        action: str = "open",
        time_s: float = 0.0,
        event_name: str = "Switch Event",
        folder_name: str = "Fault Cases",
        open_digsilent: bool = True,
    ) -> dict[str, Any]:
        """Create one idempotent switch-based contingency definition."""
        created_case = None
        created_event = None
        try:
            case_name = str(case_name or "").strip()
            target_query = str(target_query or "").strip()
            event_name = str(event_name or "").strip()
            folder_name = str(folder_name or "").strip()
            if not case_name or not target_query or not event_name or not folder_name:
                raise ValueError(
                    "case_name, target_query, event_name, and folder_name are required"
                )

            action_name = str(action or "").strip().casefold()
            actions = {"open": 0, "close": 1}
            if action_name not in actions:
                raise ValueError("action must be 'open' or 'close'")

            time_s = float(time_s)
            if not math.isfinite(time_s) or time_s < 0:
                raise ValueError("time_s must be a finite non-negative number")

            app = cls._get_application(open_digsilent)
            project = app.GetActiveProject()
            if project is None:
                raise RuntimeError("No PowerFactory project is active")

            folders = cls._find_named_contents(
                project,
                folder_name,
                "IntFltcases",
            )
            if len(folders) != 1:
                raise RuntimeError(
                    f"Expected one contingency folder named '{folder_name}', found {len(folders)}"
                )
            folder = folders[0]

            targets = app.GetCalcRelevantObjects(target_query) or []
            if len(targets) != 1:
                raise RuntimeError(
                    f"Expected one target matching '{target_query}', found {len(targets)}"
                )
            target = targets[0]

            cases = cls._find_named_contents(folder, case_name, "IntEvt")
            if len(cases) > 1:
                raise RuntimeError(f"Multiple contingency cases matched: {case_name}")
            if cases:
                fault_case = cases[0]
            else:
                fault_case = folder.CreateObject("IntEvt", case_name)
                if fault_case is None:
                    raise RuntimeError(f"Could not create contingency case: {case_name}")
                created_case = fault_case

            events = cls._find_named_contents(fault_case, event_name, "EvtSwitch")
            if len(events) > 1:
                raise RuntimeError(f"Multiple switch events matched: {event_name}")
            if events:
                event = events[0]
                matches = (
                    event.GetAttribute("p_target").GetFullName()
                    == target.GetFullName()
                    and int(event.GetAttribute("i_switch")) == actions[action_name]
                    and math.isclose(float(event.GetAttribute("time")), time_s)
                    and not bool(event.GetAttribute("outserv"))
                )
                if not matches:
                    raise RuntimeError(
                        f"Switch event already exists with different settings: {event_name}"
                    )
                created = False
            else:
                event = fault_case.CreateObject("EvtSwitch", event_name)
                if event is None:
                    raise RuntimeError(f"Could not create switch event: {event_name}")
                created_event = event
                cls._set_and_verify_attributes(
                    event,
                    {
                        "p_target": target,
                        "time": time_s,
                        "i_switch": actions[action_name],
                        "outserv": 0,
                    },
                    "Switch event",
                )
                created = True

            def identity(obj):
                return {
                    "name": obj.GetAttribute("loc_name"),
                    "class_name": obj.GetClassName(),
                    "full_name": obj.GetFullName(),
                }

            return {
                "success": True,
                "message": (
                    "Contingency switch event created"
                    if created
                    else "Contingency switch event already existed"
                ),
                "created": created,
                "case": identity(fault_case),
                "event": identity(event),
                "target": identity(target),
                "action": action_name,
                "time_s": time_s,
            }
        except Exception as e:
            for label, created_object in (
                ("switch event", created_event),
                ("contingency case", created_case),
            ):
                if created_object is None:
                    continue
                try:
                    created_object.Delete()
                except Exception as rollback_error:
                    log.error(
                        f"Could not roll back created {label}: {rollback_error}"
                    )
            log.error(f"Contingency creation failed: {e}")
            return {"success": False, "message": str(e)}

    @classmethod
    def run_contingency_analysis(
        cls,
        open_digsilent: bool = True,
        calculation_method: str = "configured",
    ) -> dict[str, Any]:
        """Execute ComSimoutage, optionally selecting its calculation method."""
        try:
            modes = {
                "configured": None,
                "ac": 0,
                "dc": 1,
                "ac_linearised": 2,
                "linearised_screening": 3,
            }
            mode = calculation_method.strip().casefold()
            if mode not in modes:
                raise ValueError(
                    "calculation_method must be one of: "
                    + ", ".join(modes)
                )

            app = cls._get_application(open_digsilent)
            if app.GetActiveStudyCase() is None:
                raise RuntimeError("No PowerFactory study case is active")

            command = app.GetFromStudyCase("ComSimoutage")
            if command is None:
                raise RuntimeError(
                    "ComSimoutage is unavailable in the active study case; "
                    "check the PowerFactory licence and command configuration"
                )

            def attribute(name: str):
                try:
                    value = command.GetAttribute(name)
                    if value is not None:
                        return value
                except Exception:
                    pass
                return getattr(command, name, None)

            selected_method = modes[mode]
            previous_method = None
            if selected_method is not None:
                previous_method = attribute("iopt_Linear")

            result = None
            try:
                if selected_method is not None:
                    cls._set_and_verify_attributes(
                        command,
                        {"iopt_Linear": selected_method},
                        "Contingency Analysis",
                    )
                error_code = command.Execute()
                succeeded = error_code in (0, None)

                if not succeeded:
                    log.error(
                        "Contingency analysis failed: ComSimoutage returned "
                        f"error code {error_code}"
                    )

                # Capture the settings used by this run before restoring an
                # explicit method selection below.
                result = {
                    "success": succeeded,
                    "message": (
                        "Configured contingency analysis completed"
                        if succeeded
                        else f"ComSimoutage returned error code {error_code}"
                    ),
                    "execution_code": error_code,
                    "command": {
                        "name": attribute("loc_name"),
                        "class_name": command.GetClassName(),
                        "full_name": command.GetFullName(),
                    },
                    "settings": {
                        "mode": mode,
                        "data_source": attribute("dat_src"),
                        "calculation_method": attribute("iopt_method"),
                        "linear_method": attribute("iopt_Linear"),
                        "linear_option": attribute("copt_Linear"),
                        "combine_ac_dc": attribute("iACDCCombine"),
                        "dynamic_contingencies": attribute("dynamicCase"),
                        "mode_restored": True,
                    },
                }
            finally:
                if selected_method is not None:
                    try:
                        cls._set_and_verify_attributes(
                            command,
                            {"iopt_Linear": previous_method},
                            "Contingency Analysis",
                        )
                    except Exception as restore_error:
                        # The run already happened, and its verdict is what the
                        # caller asked for -- losing it to report a restore
                        # failure would hide both the outcome and the
                        # execution code. Keep the result and say the study
                        # case was left on the explicit mode. Swallowing the
                        # error here also stops it replacing an exception the
                        # try block is already propagating.
                        log.error(
                            "Could not restore iopt_Linear to "
                            f"{previous_method!r}: {restore_error}"
                        )
                        if result is not None:
                            result["settings"]["mode_restored"] = False

            # A native failure keeps the same shape as a success, so a caller
            # can read execution_code instead of parsing the message text.
            return result
        except Exception as e:
            log.error(f"Contingency analysis failed: {e}")
            return {
                "success": False,
                "message": str(e),
            }

    # ──────────────────────────────────────────────────────────────
    # CREATE STUDY CASE — create/activate case without simulation
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def create_study_case(
        cls,
        project_path: str,
        case_name: str,
        base_study_case: str = "0. Base",
        open_digsilent: bool = True,
        request_id: str = "",
    ) -> tuple[bool, str]:
        """
        Create and activate a study case by name, without running simulations.

        If case_name already exists, it is activated as-is.
        Otherwise, the case is copied from base_study_case.

        If request_id is provided and repeated, the cached result is returned
        without executing creation/activation logic again.
        """
        try:
            case_name = (case_name or "").strip()
            base_study_case = (base_study_case or "").strip() or "0. Base"
            request_id = (request_id or "").strip()
            if not case_name:
                raise RuntimeError("case_name cannot be empty")

            def _done(ok: bool, msg: str) -> tuple[bool, str]:
                if request_id:
                    cls._create_case_request_cache[request_id] = (ok, msg, time.time())
                return ok, msg

            if request_id:
                cls._prune_create_case_request_cache()
                cached = cls._create_case_request_cache.get(request_id)
                if cached is not None:
                    ok, msg, _ = cached
                    replay_msg = f"[idempotent replay] {msg}"
                    log.warn(f"create_study_case replay ignored for request_id='{request_id}'")
                    return ok, replay_msg

            app = cls._get_application(open_digsilent)

            if cls._shared_project_path != project_path:
                project = app.ActivateProject(project_path)
                if project is None:
                    raise RuntimeError(f"Project not found: {project_path}")
                cls._shared_project = project
                cls._shared_project_path = project_path

            folder = app.GetProjectFolder("study")
            if folder is None:
                raise RuntimeError("Study folder not found: GetProjectFolder('study') returned None")

            before_names = cls._list_study_case_names(folder)

            target_case = cls._find_study_case_exact(folder, case_name)
            if target_case is not None:
                target_case.Activate()
                return _done(True, f"Study case already existed and was activated: {case_name}")

            base_case = cls._find_study_case_exact(folder, base_study_case)
            if base_case is None:
                raise RuntimeError(f"Base study case not found: {base_study_case}")

            new_case = folder.AddCopy(base_case, case_name)
            if new_case is None:
                target_case = cls._find_study_case_exact(folder, case_name)
                if target_case is None:
                    raise RuntimeError(f"Study case copy failed: {case_name}")
                new_case = target_case

            after_names = cls._list_study_case_names(folder)
            created_names = sorted(after_names - before_names)
            if len(created_names) > 1:
                raise RuntimeError(
                    "Unexpected multiple study-case creations detected in one call: "
                    + ", ".join(created_names)
                )
            if case_name not in after_names:
                raise RuntimeError(f"Target case not found after creation: {case_name}")

            new_case.Activate()
            log.ok(f"Study case copied from '{base_study_case}' to '{case_name}'")
            return _done(True, f"Study case created and activated: {case_name}")

        except Exception as e:
            log.error(f"Create study case failed: {e}")
            return False, str(e)

    # ──────────────────────────────────────────────────────────────
    # PIPELINE — run all steps in sequence
    # ──────────────────────────────────────────────────────────────

    def run_pipeline(self) -> dict:
        """
        Execute the full pipeline and return a status report dict.
        Each step is guarded: a failure stops the pipeline early.
        """
        report = {
            "connect":          None,
            "activate_case":    None,
            "load_flow":        None,
            "rms_simulation":   None,
            "csv_export":       None,
            "standard_plots":   None,
            "pfd_export":       None,
            "csv_path":         None,
            "pfd_path":         None,
            "success":          False,
        }

        steps = [
            ("connect",        self.connect),
            ("activate_case",  self.activate_study_case),
            ("load_flow",      self.run_loadflow),
            ("rms_simulation", self.run_rms_simulation),
            ("csv_export",     self.export_results_to_csv),
        ]

        for key, fn in steps:
            ok, msg = fn()
            report[key] = {"ok": ok, "msg": msg}
            if not ok:
                log.error(f"Pipeline stopped at step '{key}': {msg}")
                return report

        # -- Standard plots (always enabled by default) ----------------
        csv_path = report["csv_export"]["msg"]
        if report["csv_export"]["ok"] and csv_path:
            ok, msg = self.generate_standard_plots(csv_path)
            report["standard_plots"] = {"ok": ok, "msg": msg}
            if not ok:
                log.warn(f"Standard plots generation failed, continuing anyway: {msg}")
        else:
            report["standard_plots"] = {"ok": True, "msg": "Skipped (no CSV available)"}

        do_export_pfd = bool(getattr(self.cfg, "export_pfd", 0))
        if do_export_pfd:
            ok, msg = self.export_project_to_pfd()
            report["pfd_export"] = {"ok": ok, "msg": msg}
            if not ok:
                log.error(f"Pipeline stopped at step 'pfd_export': {msg}")
                return report
            report["pfd_path"] = msg
        else:
            report["pfd_export"] = {"ok": True, "msg": "Skipped (export_pfd=0)"}

        report["csv_path"] = report["csv_export"]["msg"]
        report["success"]  = True
        log.section("PIPELINE COMPLETE")
        log.ok(f"All steps passed. Results → {report['csv_path']}")
        return report


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── Load config from JSON (edit simulation_config.json, not this file)
    _cfg_path = os.path.join(os.path.dirname(__file__), "simulation_config.json")
    cfg = SimulationConfig.from_json(_cfg_path)

    agent  = DIgSILENTAgent(cfg)
    report = agent.run_pipeline()

    # ── Print final summary ────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  PIPELINE REPORT")
    print("═" * 60)
    for step, result in report.items():
        if isinstance(result, dict):
            status = "✅" if result["ok"] else "❌"
            print(f"  {status}  {step:<20} {result['msg']}")
    print(f"\n  Overall success: {'✅ YES' if report['success'] else '❌ NO'}")
    if report["csv_path"]:
        print(f"  CSV output:      {report['csv_path']}")
    print("═" * 60)
