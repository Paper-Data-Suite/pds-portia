"""Setuptools build hooks for the Portia runtime contract bundle."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent
BUNDLE_BUILDER = ROOT / "portia" / "_bundle_builder.py"


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("portia_bundle_builder", BUNDLE_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Portia runtime bundle builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class build_py(_build_py):
    """Compile the selected public-contract closure into the built package."""

    def _bundle_output(self) -> Path:
        return Path(self.build_lib) / "portia" / "_runtime_contract_bundle.json"

    def run(self) -> None:
        super().run()
        builder = _load_builder()
        writer: Any = getattr(builder, "write_runtime_bundle")
        writer(ROOT, self._bundle_output())

    def get_outputs(self, include_bytecode: int = 1) -> list[str]:
        outputs = list(super().get_outputs(include_bytecode=include_bytecode))
        bundle = str(self._bundle_output())
        if bundle not in outputs:
            outputs.append(bundle)
        return outputs


setup(cmdclass={"build_py": build_py})
