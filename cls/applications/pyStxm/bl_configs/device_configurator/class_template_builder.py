import importlib.util
from pathlib import Path
from typing import Any


def load_dev_dct_from_file(devs_py_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Load and return dev_dct from a devs.py file path."""
    devs_py_path = Path(devs_py_path)
    spec = importlib.util.spec_from_file_location("_dynamic_devs_module", devs_py_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {devs_py_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    dev_dct = getattr(module, "dev_dct", None)
    if not isinstance(dev_dct, dict):
        raise ValueError(f"No valid dev_dct found in {devs_py_path}")
    return dev_dct


def get_keys_for_class(dev_dct: dict[str, list[Any]], class_name: str) -> list[str]:
    """Return ordered unique keys used by all entries with the given class."""
    ordered_keys: list[str] = []
    seen: set[str] = set()

    for entries in dev_dct.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("class") != class_name:
                continue
            for key in entry.keys():
                if key not in seen:
                    seen.add(key)
                    ordered_keys.append(key)

    return ordered_keys


def build_template_for_class(
    dev_dct: dict[str, list[Any]], class_name: str, default_value: Any = ""
) -> dict[str, Any]:
    """Build a dict template containing all keys used by a class in dev_dct."""
    keys = get_keys_for_class(dev_dct, class_name)
    if not keys:
        raise KeyError(f"No entries found for class '{class_name}'")

    template = {key: default_value for key in keys}
    if "class" in template:
        template["class"] = class_name
    return template


def build_template_from_file(
    devs_py_path: str | Path, class_name: str, default_value: Any = ""
) -> dict[str, Any]:
    """Convenience wrapper: load dev_dct from file and build class template."""
    dev_dct = load_dev_dct_from_file(devs_py_path)
    return build_template_for_class(dev_dct, class_name, default_value=default_value)


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Build a key template for a class from devs.py")
    parser.add_argument("devs_py_path", help="Absolute path to devs.py")
    parser.add_argument("class_name", help="Class name to build template for")
    args = parser.parse_args()

    result = build_template_from_file(args.devs_py_path, args.class_name)
    pprint.pprint(result)

