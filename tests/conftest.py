import builtins
import inspect
from unittest import mock


# Cached properties are useful at runtime for efficiency, but make unit
# testing harder. This simply replaces @cached_property with @property.
mock.patch("functools.cached_property", property).start()

if not hasattr(builtins, "breakpoint"):
    # Shim breakpoint() builtin from PEP-0553 prior to 3.7
    def _breakpoint():
        import ipdb

        ipdb.set_trace(inspect.currentframe().f_back)

    builtins.breakpoint = _breakpoint
