import asyncio
import threading
import logging
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("pscad-mcp.executor")


def _init_worker_com():
    """Initialize COM once for the single executor worker thread.

    PSCAD's automation discovery uses WMI (SWbemServices), which caches a COM
    object on first use. Initializing and uninitializing COM around every call
    tears that cached object down, so the next WMI-using call fails with
    "object invoked has disconnected from its clients". Because the executor
    uses a single long-lived worker, COM is initialized exactly once here (when
    the thread starts) and left initialized for the thread's lifetime.
    """
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass


class RobustExecutor:
    """
    Implements the Command/Proxy pattern to wrap PSCAD calls
    with timeouts and locks to prevent hangs and deadlocks.
    """
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.lock = threading.Lock()
        # PSCAD is single-threaded via COM; use a single worker whose COM
        # apartment is initialized once for its lifetime (see _init_worker_com).
        self.executor = ThreadPoolExecutor(max_workers=1, initializer=_init_worker_com)

    async def run_safe(self, func: Callable, *args, _timeout: float | None = None, **kwargs) -> Any:
        """Execute a PSCAD call in a separate thread with a watchdog timeout.

        The watchdog defaults to ``self.timeout`` (30 s) so a frozen PSCAD or a
        modal dialog cannot hang the server. Long-running calls (loading a large
        project, a clean build) can override it via the ``_timeout`` keyword:
        a larger value extends the watchdog, while ``0``/``None`` disables it
        entirely. The leading underscore keeps the name from colliding with any
        keyword argument forwarded to ``func``.
        """
        loop = asyncio.get_running_loop()
        func_name = getattr(func, "__name__", str(func))
        effective_timeout = self.timeout if _timeout is None else _timeout
        wait_timeout = None if not effective_timeout or effective_timeout <= 0 else effective_timeout

        def wrapped_call():
            # COM is initialized once for the worker thread (see _init_worker_com);
            # do not re-init/uninit per call, or cached WMI/COM objects break.
            with self.lock:
                return func(*args, **kwargs)

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self.executor, wrapped_call),
                timeout=wait_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"PSCAD Command {func_name} timed out after {wait_timeout}s.")
            raise RuntimeError(f"PSCAD timed out during {func_name}. It might be frozen or showing a dialog.")
        except Exception as e:
            logger.error(f"Error in {func_name}: {str(e)}")
            raise


# Global shared executor instance
robust_executor = RobustExecutor()
