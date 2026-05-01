import psutil
import logging
import time
from typing import Optional
import mhi.pscad
from pscad_mcp.core.executor import robust_executor

logger = logging.getLogger("pscad-mcp.connection")

class PSCADConnectionManager:
    """
    Singleton Manager for PSCAD lifecycle and connection health.
    """
    _instance: Optional['PSCADConnectionManager'] = None
    _pscad: Optional[mhi.pscad.PSCAD] = None

    HEARTBEAT_TTL_S = 1.5

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PSCADConnectionManager, cls).__new__(cls)
            cls._instance._last_heartbeat_at = 0.0
        return cls._instance

    def invalidate_heartbeat(self) -> None:
        """Force the next `pscad` access to re-run the full health check."""
        self._last_heartbeat_at = 0.0

    @property
    def pscad(self) -> mhi.pscad.PSCAD:
        """Get a safe, verified PSCAD instance."""
        if self._pscad is None:
            raise RuntimeError("PSCAD not connected. Use get_local_pscad or launch_pscad first.")

        now = time.monotonic()
        if now - self._last_heartbeat_at < self.HEARTBEAT_TTL_S:
            return self._pscad

        # OS-level check
        if not self.is_process_running():
            self._pscad = None
            self._last_heartbeat_at = 0.0
            raise RuntimeError("PSCAD process (PSCAD.exe) is not running on the system.")

        # Heartbeat check
        try:
            if not self._pscad.is_alive():
                self._pscad = None
                self._last_heartbeat_at = 0.0
                raise RuntimeError("Connection to PSCAD lost.")
            self._pscad.is_busy()  # RMI check
        except Exception as e:
            self._pscad = None
            self._last_heartbeat_at = 0.0
            raise RuntimeError(f"PSCAD is unresponsive: {str(e)}")

        self._last_heartbeat_at = now
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
            self._pscad = await robust_executor.run_safe(mhi.pscad.application)
            self._last_heartbeat_at = time.monotonic()
            return f"Successfully attached to PSCAD {self._pscad.version} (Local)."
        except Exception as e:
            logger.error(f"Attach failed: {str(e)}")
            raise RuntimeError(f"Failed to attach to PSCAD: {str(e)}")

    def disconnect(self):
        """Reset the internal handle."""
        self._pscad = None
        self._last_heartbeat_at = 0.0

# Global singleton
pscad_manager = PSCADConnectionManager()
