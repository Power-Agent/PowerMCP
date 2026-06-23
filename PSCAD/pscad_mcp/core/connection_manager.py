from __future__ import annotations

import os
import psutil
import logging
from typing import Optional, TYPE_CHECKING
from pscad_mcp.core.executor import robust_executor

if TYPE_CHECKING:
    import mhi.pscad

logger = logging.getLogger("pscad-mcp.connection")

class PSCADConnectionManager:
    """
    Singleton Manager for PSCAD lifecycle and connection health.
    """
    _instance: Optional['PSCADConnectionManager'] = None
    _pscad: Optional[mhi.pscad.PSCAD] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PSCADConnectionManager, cls).__new__(cls)
        return cls._instance

    @property
    def pscad(self) -> mhi.pscad.PSCAD:
        """Get a safe, verified PSCAD instance."""
        if self._pscad is None:
            raise RuntimeError("PSCAD not connected. Use get_local_pscad or launch_pscad first.")
        
        # OS-level check
        if not self.is_process_running():
            self._pscad = None
            raise RuntimeError("PSCAD process (PSCAD.exe) is not running on the system.")
            
        # Heartbeat check
        try:
            if not self._pscad.is_alive():
                self._pscad = None
                raise RuntimeError("Connection to PSCAD lost.")
            self._pscad.is_busy() # RMI check
        except Exception as e:
            self._pscad = None
            raise RuntimeError(f"PSCAD is unresponsive: {str(e)}")
            
        return self._pscad

    def is_process_running(self) -> bool:
        """Check if PSCAD.exe is in the system process table."""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'pscad' in proc.info['name'].lower():
                return True
        return False

    async def attach_local(self) -> str:
        """Robustly attach to any local PSCAD instance or launch a new one."""
        # PSCAD's generated EMTDC run batch launches the compiled solver by a
        # bare name from the build directory (``pushd <dir>`` then
        # ``<project>.exe``). If ``NoDefaultCurrentDirectoryInExePath`` is set in
        # our environment (some launchers set it), PSCAD inherits it and Windows
        # refuses to find the exe in the current directory -- the run dies
        # immediately with "'<project>.exe' is not recognized as an internal or
        # external command". Scrub it so the PSCAD instance we launch, and the
        # EMTDC processes it spawns, can run normally.
        os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
        try:
            import mhi.pscad
        except ImportError as e:
            raise RuntimeError(
                "PSCAD support requires Windows, a PSCAD installation, and "
                "`pip install powermcp[pscad-windows]` (provides mhi-pscad/mhi-psout). "
                "Original import error: " + repr(e)
            )
        try:
            # Cold-launching PSCAD can take well over the default 30 s watchdog;
            # give the attach/launch a generous timeout.
            try:
                self._pscad = await robust_executor.run_safe(mhi.pscad.application, _timeout=120)
            except Exception as attach_err:
                # application() only catches ConnectionRefusedError before
                # launching; a stale PSCAD process with no automation listener
                # raises ProcessLookupError instead, so it never falls back to
                # launching. Start a fresh instance explicitly in that case.
                logger.info("Could not attach to a running PSCAD (%s); launching a new instance.", attach_err)
                self._pscad = await robust_executor.run_safe(mhi.pscad.launch, _timeout=180)
            return f"Successfully attached to PSCAD {self._pscad.version} (Local)."
        except Exception as e:
            logger.error(f"Attach failed: {str(e)}")
            raise RuntimeError(f"Failed to attach to PSCAD: {str(e)}")

    def disconnect(self):
        """Reset the internal handle."""
        self._pscad = None

# Global singleton
pscad_manager = PSCADConnectionManager()
