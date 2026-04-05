"""Single py_dss_interface DSS instance and dss_tools wiring."""

from py_dss_interface import DSS
from py_dss_toolkit import dss_tools

dss = DSS()
dss_tools.update_dss(dss)
