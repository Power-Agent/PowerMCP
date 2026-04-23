"""
╔══════════════════════════════════════════════════════════════════╗
║           DIGSILENT AGENT — Standalone RMS Simulation            ║
╚══════════════════════════════════════════════════════════════════╝

Author
------
  Andrea Pomarico
  
"""


import sys
import os
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── PowerFactory Python path ──────────────────────────────────────
sys.path.append(r"C:\Program Files\DIgSILENT\PowerFactory 2025 SP1\Python\3.13")

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
    study_case:   str = ""
    base_study_case: str = r"0. Base"

    def __post_init__(self):
        """Fail fast when required environment-specific configuration is missing."""
        if not self.project_path.strip():
            raise ValueError(
                "Missing required 'project_path' in SimulationConfig. "
                "Please set it in simulation_config.json."
            )
        if not self.study_case.strip():
            raise ValueError(
                "Missing required 'study_case' in SimulationConfig. "
                "Please set it in simulation_config.json."
            )
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
    output_dir:   str = r"C:\RMS_Results"
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
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    # ── Signals to export ─────────────────────────────────────────
    # Each entry: (object_name, variable_name, friendly_label)
    # Adjust names to match elements in your network model.
    signals: list = field(default_factory=lambda: [
        # Bus voltages
        ("Bus 01.ElmTerm",    "m:u",    "V_Troia_pu"),
        ("Bus 02.ElmTerm",   "m:u",    "V_Ariano_pu"),
        ("Bus 03.ElmTerm",   "m:u",    "V_Latina_pu"),

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
            safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.cfg.run_label)
            self.run_output_dir = os.path.join(self.cfg.output_dir, safe_label)
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
            global pf
            open_digsilent = bool(getattr(self.cfg, "open_digsilent", 1))
            if pf is None:
                import powerfactory as pf
            if DIgSILENTAgent._shared_app is None:
                self.app = pf.GetApplicationExt()
                if self.app is None:
                    raise RuntimeError("GetApplicationExt() returned None")
                self._apply_show_preference(self.app, open_digsilent)
                DIgSILENTAgent._shared_app = self.app
                log.ok("PowerFactory application obtained and shown")
            else:
                self.app = DIgSILENTAgent._shared_app
                self._apply_show_preference(self.app, open_digsilent)
                log.ok("Reusing existing PowerFactory application in this process")
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
            return True, "Study case activated"
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
                f"{self.cfg.run_label}_RMS.csv"
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
            safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.cfg.run_label)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pfd_path = os.path.join(run_dir, f"{safe_label}_{timestamp}.pfd")

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
            if not os.path.exists(csv_path):
                raise RuntimeError(f"CSV file not found: {csv_path}")

            import pandas as pd
            run_dir = self._ensure_run_output_dir()

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
                ax.legend(loc='best', fontsize=9)
                fig.tight_layout()
                voltage_plot = os.path.join(run_dir, f"{self.cfg.run_label}_voltages.png")
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
                speed_plot = os.path.join(run_dir, f"{self.cfg.run_label}_gen_speeds.png")
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
        global pf
        if pf is None:
            import powerfactory as pf

        if not os.path.isfile(file_path):
            return False, f"File not found: {file_path}"

        try:
            if cls._shared_app is None:
                app = pf.GetApplicationExt()
                if app is None:
                    raise RuntimeError("GetApplicationExt() returned None")
                cls._apply_show_preference(app, open_digsilent)
                cls._shared_app = app
            else:
                app = cls._shared_app
                cls._apply_show_preference(app, open_digsilent)

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
        global pf
        if pf is None:
            import powerfactory as pf

        try:
            if cls._shared_app is None:
                app = pf.GetApplicationExt()
                if app is None:
                    raise RuntimeError("GetApplicationExt() returned None")
                cls._apply_show_preference(app, open_digsilent)
                cls._shared_app = app
            else:
                app = cls._shared_app
                cls._apply_show_preference(app, open_digsilent)

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
    # LOAD FLOW — run ComLdf on the currently active study case
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def load_flow(cls, open_digsilent: bool = True) -> tuple[bool, str]:
        """Run a load flow (ComLdf) on the currently active study case."""
        global pf
        if pf is None:
            import powerfactory as pf
        try:
            if cls._shared_app is None:
                app = pf.GetApplicationExt()
                if app is None:
                    raise RuntimeError("GetApplicationExt() returned None")
                cls._apply_show_preference(app, open_digsilent)
                cls._shared_app = app
            else:
                app = cls._shared_app
                cls._apply_show_preference(app, open_digsilent)

            ldf = app.GetFromStudyCase('ComLdf')
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
    # SHORT CIRCUIT — run ComShc on the currently active study case
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def short_circuit(cls, open_digsilent: bool = True) -> tuple[bool, str]:
        """Run a short-circuit calculation (ComShc) on the currently active study case."""
        global pf
        if pf is None:
            import powerfactory as pf
        try:
            if cls._shared_app is None:
                app = pf.GetApplicationExt()
                if app is None:
                    raise RuntimeError("GetApplicationExt() returned None")
                cls._apply_show_preference(app, open_digsilent)
                cls._shared_app = app
            else:
                app = cls._shared_app
                cls._apply_show_preference(app, open_digsilent)

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
        global pf
        if pf is None:
            import powerfactory as pf

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

            if cls._shared_app is None:
                app = pf.GetApplicationExt()
                if app is None:
                    raise RuntimeError("GetApplicationExt() returned None")
                cls._apply_show_preference(app, open_digsilent)
                cls._shared_app = app
            else:
                app = cls._shared_app
                cls._apply_show_preference(app, open_digsilent)

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

