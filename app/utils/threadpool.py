import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)


class ThreadPoolExecutorDumpStacktrace(ThreadPoolExecutor):
    def submit(self, fn, *args, **kwargs):
        """Submits the wrapped function instead of `fn`"""
        return super().submit(self._function_wrapper, fn, *args, **kwargs)

    def _function_wrapper(self, fn, *args, **kwargs):
        """
        Wraps `fn` in order to dump the traceback on any exception
        """
        try:
            return fn(*args, **kwargs)
        except Exception as ex:
            log.exception(ex)
            raise
