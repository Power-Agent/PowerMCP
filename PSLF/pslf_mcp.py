import sys
import os
import pandas as pd
import subprocess
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional, Tuple, Any, Union

# Initialize MCP server
mcp = FastMCP("PSLF Positive Sequence Load Flow Program")

# ---------------------------------------------------------------------------
# Lazy, memoized PSLF engine initialization.
#
# `from PSLF_PYTHON import *` and init_pslf() used to run at import time, which
# crashed this module on any machine without PSLF and blocked packaging. The
# PSLF_PYTHON module is vendor-supplied (not on PyPI); its directory comes from
# ~/.powermcp/config.toml (key pslf.python_lib) when powermcp is installed and
# is added to sys.path before the import. The wildcard names (Pslf,
# CaseParameters, Bus, Flox, ...) are published into this module's globals on
# first use, so the tool functions below keep referencing them unchanged.
# ---------------------------------------------------------------------------
_pslf_ready = False


def _resolve_pslf_lib():
    try:
        from powermcp.config import get_path
        return get_path("pslf", "python_lib", must_exist=False)
    except Exception:
        return None


def _ensure_pslf():
    """Inject the PSLF_PYTHON dir, import it, and call init_pslf() exactly once."""
    global _pslf_ready
    if _pslf_ready:
        return
    lib = _resolve_pslf_lib()
    if lib and lib not in sys.path:
        sys.path.insert(0, lib)
    try:
        import PSLF_PYTHON
    except Exception as e:
        raise RuntimeError(
            "Could not import PSLF_PYTHON. Install PSLF and configure its path: "
            "`powermcp config set pslf.python_lib <dir containing PSLF_PYTHON>`. "
            "Original error: " + repr(e)
        )
    # Publish the wildcard names (Pslf, CaseParameters, Bus, Flox, init_pslf, ...).
    globals().update({k: getattr(PSLF_PYTHON, k) for k in dir(PSLF_PYTHON) if not k.startswith("_")})
    PSLF_PYTHON.init_pslf(silent=False, working_directory=os.getcwd())
    _pslf_ready = True

@mcp.tool()
def open_case(case: str) -> Dict[str, Any]:
    """
    Open a PSLF case file.
    
    Args:
        case: Filename with .sav extension.
    
    Returns:
        Dict with status and case information
    """
    try:
        
        _ensure_pslf()
        iret = Pslf.load_case(os.getcwd() + "\\" + case)
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec + cp.Ntran
        gen_data = cp.Ngen
        load_data = cp.Nload
        shunt_data = cp.Nshunt + cp.Nsvd
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'path': os.getcwd() + "\\" + case,
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error unknown'
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
        
@mcp.tool()
def save_case() -> Dict[str, Any]:
    """
    Save a PSLF case file to temp.sav
    
    Returns:
        Dict with status and case information
    """
    try:
        
        _ensure_pslf()
        iret = Pslf.save_case(os.getcwd() + "\\temp.sav")
        
        if (iret == 0):
            return {
                'status': 'success'
            }
        else:
            return {
                'status': 'error failed to save case'
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }

@mcp.tool()
def solve_case() -> Dict[str, Any]:
    """
    Solves a powerflow case using PSLF.
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        iret = Pslf.solve_case()
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'result_code': iret
                }
            }
        elif (iret == -1):
            return {
                'status': 'error case diverged',
                'case_info': {
                    'result_code': iret
                }
            }
        elif (iret == -2):
            return {
                'status': 'error exceeded maximum iterations',
                'case_info': {
                    'result_code': iret
                }
            }
        elif (iret < -2):
            return {
                'status': 'error no swing bus or HVDC error',
                'case_info': {
                    'result_code': iret
                }
            }
        else:
            return {
                'status': 'error unknown',
                'case_info': {
                    'result_code': iret
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }

@mcp.tool()
def add_bus(busnum: int, busname: str, nominalkv: float, type: int = 1) -> Dict[str, Any]:
    """
    Add a new bus to the power system model
    
    Args:
        busnum: A unique identifying integer used as the primary key in the bus database. Is not necessarily consecutive and could be larger than the number of buses in the case.
        busname: A human readable name of the bus no longer than 12 characters in length.
        nominalkv: The nominal voltage of the bus in kilovolts.
        type: An integer flag where 0 = system slack bus, 1 = a load bus, and 2 = a generator bus. (default 1)
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        iret = Pslf.add_record(1, 0, busnum, 'type basekv busnam', str(type) + " " + str(nominalkv) + " " + busname)
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec + cp.Ntran
        gen_data = cp.Ngen
        load_data = cp.Nload
        shunt_data = cp.Nshunt + cp.Nsvd
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error bus number not found when using combination of bus name and voltage',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 3):
            return {
                'status': 'error bus number must be positive',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == -2):
            return {
                'status': 'error bus voltage must be positive',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error bus type is out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }

@mcp.tool()
def add_branch(frombus: int, tobus: int, reactance: float, circuit: str = "1 ", resistance: float = 0.0, susceptance: float = 0.0, rating: float = 9999.0, section: int = 1) -> Dict[str, Any]:
    """
    Add a new branch (transmission line, transformer, series capacitor, or series reactor) to the power system model
    
    Args:
        frombus: Integer identifier of the starting terminal Is not necessarily consecutive and could be larger than the number of buses in the case.
        tobus: Integer identifier of the ending terminal Is not necessarily consecutive and could be larger than the number of buses in the case.
        reactance: A float representing the imaginary component of impedance of the transmission line in per unit. Positive is inductive and negative is capacitive. If the user gives a value in Ohms, ask to get a value in per unit.
        circuit: 2 character identifer uniquely identifying the circuit in the case there are multiple circuits. (default "1 ")
        resistance: A float representing the real component of impedance of the transmission line in per unit. (default 0.0)
        susceptance: A float representing the per unit susceptance of the transmission line. (default 0.0)
        rating: The maximum safe rating of the transmission line in MVA (default 9999.0)
        section: An integer that identifies a series element. A series capacitor or series reactor would be an additional section for example a series component with section=2
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        # determine if it is a transformer or transmission line
        index = Pslf.bus_internal_index(frombus)
        if (index < 0):
            return {
                'status': 'error from bus does not exist'
            }
        else:
            from_volt = Bus[index].Basekv
        index = Pslf.bus_internal_index(tobus)
        if (index < 0):
            return {
                'status': 'error to bus does not exist'
            }
        else:
            to_volt = Bus[index].Basekv
        
        if (from_volt == to_volt):
            # transmission line
            iret = Pslf.add_record(1, 1, str(frombus) + " " + str(tobus) + " " + circuit + " 1", "st zsecr zsecx bsec rate[0]", "1 " + str(resistance) + " " + str(reactance) + " " + str(susceptance) + " " + str(rating))
        else:
            # 2 winding transformer (tertiary kbus is -1 in the identifier)
            iret = Pslf.add_record(1, 2, str(frombus) + " " + str(tobus) + " " + circuit + " -1", "tbase st zpsr zpsx rate[0]", "100 1 " + str(resistance) + " " + str(reactance) + " " + str(rating))
        
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec + cp.Ntran
        gen_data = cp.Ngen
        load_data = cp.Nload
        shunt_data = cp.Nshunt + cp.Nsvd
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error branch bus out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 3):
            return {
                'status': 'error branch bus does not exist',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 4):
            return {
                'status': 'error branch from and to bus are identical',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error unknown',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }

@mcp.tool()
def add_generator(bus: int, power_scheduled_mw: float, genid: str = "1 ", power_max: float = 9999.0, reactive_power_max: float = 9999.0, reactive_power_min: float = -9999.0) -> Dict[str, Any]:
    """
    Add a new generator to the case.
    
    Args:
        bus: Integer identifier of the terminal bus of the generator
        power_scheduled_mw: Amount of real power output (in megawatts) scheduled to be generated by the unit.
        genid: 2 character string that uniquely identifies generators when there are multiple units attached to the same bus. (default "1 ")
        power_max: Maximum real power that the generator can output in megawatts. (default 9999.0)
        reactive_power_max: Maximum reactive power that the generator can output in megavars. (default 9999.0)
        reactive_power_min: Minimum reactive power that the generator can output in megavars. Should be a negative number. If positive, change the input to be negative. (default -9999.0)
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        iret = Pslf.add_record(1, 3, str(bus) + " " + str(genid), "st mbase pgen pmax qmax qmin", "1 100 " + str(power_scheduled_mw) + " " + str(power_max) + " " + str(reactive_power_max) + " " + str(reactive_power_min))
        
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec + cp.Ntran
        gen_data = cp.Ngen
        load_data = cp.Nload
        shunt_data = cp.Nshunt + cp.Nsvd
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error generator bus out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error generator bus does not exist',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
        
@mcp.tool()
def add_load(bus: int, real_power: float, reactive_power: float, loadid: str = "1 ") -> Dict[str, Any]:
    """
    Add a new load to the case.
    
    Args:
        bus: Integer identifier of the bus the load is located at
        real_power: Amount of real power consumed by the load in megawatts. If user gives a per unit value, multiply by the system base MVA of 100 to get the quantity in megawatts.
        reactive_power: Amount of reactive power consumed by the load in megawatts. Inductive loads are positive and capacitive loads are negative. If the user does not specify inductive, capacitive, or provide the sign explicitly, assume the load is inductive.  If user gives a per unit value, multiply by the system base MVA of 100 to get the quantity in megavars.
        loadid: 2 character string that uniquely identifies the load when there are multiple loads attached to the same bus. (default "1 ")
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        iret = Pslf.add_record(1, 4, str(bus) + " " + loadid, "st p q", "1 " + str(real_power) + " " + str(reactive_power))
        
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec + cp.Ntran
        gen_data = cp.Ngen
        load_data = cp.Nload
        shunt_data = cp.Nshunt + cp.Nsvd
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error load bus out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error load bus does not exist',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
        
@mcp.tool()
def add_shunt(bus: int, reactive_power: float, variable_flag: int = 0, reactive_max: float = 0.0, reactive_min: float = 0.0, shuntid: str = "1 ") -> Dict[str, Any]:
    """
    Add a new fixed or variable shunt to the case.
    
    Args:
        bus: Integer identifier of the bus the shunt is located at        
        reactive_power: Amount of reactive power (in per unit) injected or absorbed by the shunt. Injections (capacitive) is positive and absorptions (inductive) is negative. If the user does not specify inductive, capacitive, or provide the sign explicitly, assume the shunt is an injection (capacitive). If the user specifies MVAR, divide by the system base MVA of 100 to get the value in per unit.
        variable_flag: 0 if shunt is fixed output and cannot change. 1 if shunt is continuously variable (SVC/STATCOM). (default 0)
        reactive_max: Only used when variable_flag = 1. Numeric value representing the maximum injection of a variable shunt in MVAR. (default 0.0)
        reactive_min: Only used when variable_flag = 1. Numeric value representing the minimum output (maximum absorbtion) of a variable shunt in MVAR. (default 0.0)
        shuntid: 2 character string that uniquely identifies the shunt when there are multiple shunts attached to the same bus. (default "1 ")
    
    Returns:
        Dict with status
    """
    try:
        _ensure_pslf()
        if (variable_flag == 0):
            # Fixed shunt
            iret = Pslf.add_record(1, 5, str(bus) + " " + shuntid, "st b", "1 " + str(reactive_power / 100.0)) # Divide by system base MVA to get in per unit
        else:
            # SVD
            iret = Pslf.add_record(1, 6, str(bus) + " " + shuntid, "type st b bmax bmin", "2 1 " + str(reactive_power / 100.0) + " " + str(reactive_max / 100.0) + " " + str(reactive_min / 100.0)) # Divide by system base MVA to get in per unit
        
        cp = CaseParameters()
        
        # Get basic case information
        bus_data = cp.Nbus
        branch_data = cp.Nbrsec + cp.Ntran
        gen_data = cp.Ngen
        load_data = cp.Nload
        shunt_data = cp.Nshunt + cp.Nsvd
        
        if (iret == 0):
            return {
                'status': 'success',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 1):
            return {
                'status': 'error insufficient input',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        elif (iret == 2):
            return {
                'status': 'error load bus out of range',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
        else:
            return {
                'status': 'error load bus does not exist',
                'case_info': {
                    'num_buses': bus_data if bus_data is not None else 0,
                    'num_branches': branch_data if branch_data is not None else 0,
                    'num_generators': gen_data if gen_data is not None else 0,
                    'num_loads': load_data if load_data is not None else 0,
                    'num_shunts': shunt_data if shunt_data is not None else 0
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }


@mcp.tool()
def get_voltage(bus: int) -> Dict[str, Any]:
    """
    Queries the voltage of a single bus and reports in per unit. If checking multiple buses with thresholds, use get_voltage_violations function instead.
    
    Args:
        bus: Integer identifier of the desired bus to query voltage for.  Is not necessarily consecutive and could be larger than the number of buses in the case.
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        index = Pslf.bus_internal_index(bus)

        if (index < 0):
            return {
                'status': 'error bus not found'
            }
        else:
            return {
                'status': 'success',
                'case_info': {
                    'bus_id': str(bus),
                    'bus_name': str(Bus[index].Busnam),
                    'base_kv': str(Bus[index].Basekv),
                    'voltage_perunit_kv': str(Bus[index].Vm),
                    'voltage_kv': str(Bus[index].Vm * Bus[index].Basekv),
                    'voltage_angle_degrees': str(Bus[index].Va)
                }
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
        
@mcp.tool()
def get_voltage_violations(overvoltage_threshold: float = 1.05, undervoltage_threshold: float = 0.95) -> Dict[str, Any]:
    """
    Queries all bus voltages, compares against a threshold (default +/- 5%), and reports buses with voltage violations. For querying a single bus without thresholds, use get_voltage instead.
    
    Args:
        overvoltage_threshold: A float value representing the maximum tolerable voltage to check for in per unit. If the user provides percent, divide their input by 100 first. (default 1.05)
        undervoltage_threshold: A float value representing the lowest tolerable voltage to check for in per unit. If the user provides percent, divide their input by 100 first. (default 0.95)
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        bus_count = CaseParameters().Nbus
        
        overvoltage = {}
        undervoltage = {}
        for i in range(bus_count):
            if Bus[i].Vm > overvoltage_threshold:
                overvoltage.update({
                    'bus_id': str(Bus[i].Extnum),
                    'bus_name': Bus[i].Busnam,
                    'base_kv': str(Bus[i].Basekv),
                    'voltage_perunit_kv': str(Bus[i].Vm),
                    'voltage_kv': str(Bus[i].Vm * Bus[i].Basekv),
                    'voltage_angle_degrees': str(Bus[i].Va)})
            elif Bus[i].Vm < undervoltage_threshold:
                undervoltage.update({
                    'bus_id': str(Bus[i].Extnum),
                    'bus_name': Bus[i].Busnam,
                    'base_kv': str(Bus[i].Basekv),
                    'voltage_perunit_kv': str(Bus[i].Vm),
                    'voltage_kv': str(Bus[i].Vm * Bus[i].Basekv),
                    'voltage_angle_degrees': str(Bus[i].Va)})
        
        if (bus_count <= 0):
            return {
                'status': 'error case not loaded into memory'
            }
        else:
            return {
                'status': 'success',
                'overvoltage': overvoltage,
                'undervoltage': undervoltage
            }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
        
@mcp.tool()
def get_overload_violations(overload_threshold: float = 1.0) -> Dict[str, Any]:
    """
    Queries a list of branches (transmission lines and transformers) with loading above a threshold (default 100%).
    
    Args:
        overload_threshold: A float value representing the maximum tolerable loading in per unit. (default 1.0) If user gives in percent, divide their input by 100 first.
    
    Returns:
        Dict with status
    """
    try:
        
        _ensure_pslf()
        branch_count = CaseParameters().Nbrsec
        if (branch_count <= 0):
            return {
                'status': 'error case not loaded into memory'
            }
            
        iret = Pslf.calculate_ac_flow(1)
        if (iret != 0) :
            return {
                'status': 'error calculating flox table'
            }
        
        overload = {}
        for i in range(branch_count):
            if Flox[i].Pul > overload_threshold:
                overload.update({
                    'type' : 'transmission_line' if Flox[i].Flag == 0 else 'transformer',
                    'from_bus': Flox[i].From,
                    'to_bus': Flox[i].To,
                    'circuit_id': Flox[i].Ck,
                    'percent_loading': Flox[i].Pul * 100})        
        
        return {
            'status': 'success',
            'overload': overload
        }
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
        
@mcp.tool()
def run_contingency_analysis() -> Dict[str, Any]:
    """
    Generates N-1 contingencies, uses SSTOOLS to run all contingencies, and generates a cross tabulated table of results.
    
    Returns:
        Dict with status
    """
    
    # Save the case into a temporary file
    try:
        _ensure_pslf()
        iret = Pslf.save_case(os.getcwd() + "\\sstools.sav")
    except Exception as e:
        return {
            'status': 'error unknown',
            'message': str(e)
        }
    
    # Generate a list of N-1 contingencies based on the case stored in the temporary file
    try:
        iret = Pslf.run_epcl(os.getcwd() + "\\PSLF\generate-otg.p")
    except Exception as e:
        return {"status": "error generate-otg.p not found", "message": str(e)}
    
    # Generate a list of default criteria to evaluate the case with.
    try:
        with open("control.cntl", 'w') as f:
            f.write("rating  1 2\n")
            f.write("monitor voltage   area      1   999    1  999  0.95 1.05    0.90  1.10   0.07  0.0     0.0\n")
            f.write("monitor flows     area      1   999    1  999   0.0	   30.0		100.0		1	2\n")
            f.write("monitor interface           1   999	100.0		1	2\n")
            f.write("monitor svd       area      1   999    1   999\n")
            f.write("monitor load      area      1   999\n")
            f.write("monitor gens      area      1   999    1\n")
            f.write("monitor           area      1   999\n")
            f.write("LTC      1 0\n")
            f.write("SVD      1 0\n")
            f.write("PAR      1 0\n")
            f.write("dctap    1 0\n")
            f.write("area     0 0\n")
        
        
    except Exception as e:
        return {"status": "error creating control.cntl", "message": str(e)}
    
    # Generate the batch contingency run.
    try:
        with open("runs.cases", 'w') as f:
            f.write('CASE "output" 0\n')
            f.write('{\n')
            f.write('SAV "sstools.sav"\n')
            f.write('OTG "cont.otg"\n')
            f.write('CNTL "control.cntl"\n')
            f.write('OUTPUT "output.crf"\n')
            f.write('}\n')
        
        
    except Exception as e:
        return {"status": "error creating runs.cases", "message": str(e)}
        
    # Run the batch of contingencies
    try:
        iret = Pslf.run_sstools("runs.cases")
        
    except Exception as e:
        return {"status": "error running SSTOOLS", "message": str(e)}
        
    # Generate the ProvisoHD batch data file
    try:
        with open("template.ctab", 'w') as f:
            f.write('runtype "cont-process"\n')
            f.write('report 1\n')
            f.write('postproc 2\n')
            f.write('ratingunits 0\n')
            f.write('"' + os.getcwd() + '\\output.crf" "' + os.getcwd() + '\\output.xlsx"\n')
            f.write('end\n')
        
    except Exception as e:
        return {"status": "error creating template.ctab", "message": str(e)}
        
        
    # Generate a ProvisoHD call
    try:
        with open(os.getcwd()+"\\run.bat", 'w') as f:
            f.write('@SET ctab=%cd%\\template.ctab\n')
            f.write('cd "C:\\Program Files (x86)\\ProvisoHD\\Release"\n')
            f.write('@SET CURRENTDIR=C:\\Program Files (x86)\\ProvisoHD\\Release\n')
            f.write('@SET CLAZZPATH=%CURRENTDIR%\\dist\\ProvisioPlotting.jar;%CURRENTDIR%\\dist\\ProvisoHD.jar\n')
            f.write('"%CURRENTDIR%\\jre\\bin\\java.exe" -classpath "%CLAZZPATH%" gui.Face1 -batch "%ctab%"\n')
            f.write('exit\n')
        
    except Exception as e:
        return {"status": "error creating run.bat", "message": str(e)}
        
    # Generate a system call to run ProvisoHD
    try:
        iret = subprocess.run(os.getcwd()+"\\run.bat", capture_output=True, text=True, check=True, shell=True)
    except Exception as e:
        return {"status": "error running ProvisoHD", "message": str(e)}
        
    # Return the contingency analysis results.
    VoltageViolations = pd.read_excel("Output.xlsx", sheet_name="VoltageViolations").to_dict(orient='dict')
    PerUnitFlowViolations = pd.read_excel("Output.xlsx", sheet_name="PerUnitFlowViolations").to_dict(orient='dict')
    UnsolvedContingencies = pd.read_excel("Output.xlsx", sheet_name="UnsolvedDescriptor").to_dict(orient='dict')
    return {
        'status': 'success',
        'VoltageViolations': VoltageViolations,
        'PerUnitFlowViolations': PerUnitFlowViolations,
        'UnsolvedContingencies': UnsolvedContingencies
    }    
    

if __name__ == "__main__":
    mcp.run(transport="stdio")