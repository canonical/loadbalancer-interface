from importlib import import_module
from pathlib import Path

versions = {}
for subpath in Path(__file__).parent.glob("*.py"):
    name = subpath.stem
    if name == __name__:
        continue
    submod = import_module(__package__ + "." + name)
    if hasattr(submod, "version"):
        versions[submod.version] = submod

max_version = max(versions.keys())
