from __future__ import annotations

import importlib
import pkgutil

import ebrag


def test_all_ebrag_modules_import() -> None:
    failures: list[str] = []
    for module_info in pkgutil.walk_packages(ebrag.__path__, prefix="ebrag."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:  # pragma: no cover - failure details are asserted below
            failures.append(f"{module_info.name}: {exc}")

    assert not failures
