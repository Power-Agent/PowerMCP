from __future__ import annotations

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
        try:
            import mhi.pscad
        except ImportError as e:
            raise RuntimeError(
                "PSCAD support requires Windows, a PSCAD installation, and "
                "`pip install powermcp[pscad-windows]` (provides mhi-pscad/mhi-psout). "
                "Original import error: " + repr(e)
            )
        try:
            self._pscad = await robust_executor.run_safe(mhi.pscad.application)
            return f"Successfully attached to PSCAD {self._pscad.version} (Local)."
        except Exception as e:
            logger.error(f"Attach failed: {str(e)}")
            raise RuntimeError(f"Failed to attach to PSCAD: {str(e)}")

    def disconnect(self):
        """Reset the internal handle."""
        self._pscad = None

# Global singleton
pscad_manager = PSCADConnectionManager()
