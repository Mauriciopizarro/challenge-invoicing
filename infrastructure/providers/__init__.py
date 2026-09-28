import importlib
import pkgutil

# Auto-discovery: every sibling module in this package gets imported once, which
# runs its @register_provider(...) decorator and populates the registry. Adding a
# new country is therefore just "add a file here" — no import list to maintain.
_EXCLUDED_MODULES = {"registry", "factory"}


def _discover() -> None:
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name not in _EXCLUDED_MODULES:
            importlib.import_module(f"{__name__}.{module_name}")


_discover()
