from unittest import mock


# Cached properties are useful at runtime for efficiency, but make unit
# testing harder. This simply replaces @cached_property with @property.
mock.patch('cached_property.cached_property', property).start()
