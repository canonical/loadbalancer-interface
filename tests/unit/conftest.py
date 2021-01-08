import pytest


# Cached properties are useful at runtime for efficiency, but make unit
# testing harder. This simply replaces @cached_property with @property.
pytest.MonkeyPatch().setattr('cached_property.cached_property', property)
