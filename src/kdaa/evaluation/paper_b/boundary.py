"""Static import-boundary enforcement between Paper B truth-side and inference-side code.

This makes truth leakage hard *by construction* rather than by convention: instead of
trusting that inference code never imports ``kdaa.evaluation.paper_b.truth``, this module
statically parses (via ``ast``, not a real import) every source file under each inference
boundary namespace and reports any that import the truth module.

Using ``ast`` rather than importing the target modules means the check works even for a
namespace that does not exist yet -- ``kdaa.evaluation.paper_b.adapters`` is not created
until WP4, so today it simply contributes zero files and passes trivially. Extend
``INFERENCE_BOUNDARY_PREFIXES`` as later work packages add new comparator/adapter
namespaces; no other change is required for the boundary check to start covering them.
"""

from __future__ import annotations

import ast
from pathlib import Path

TRUTH_MODULE = "kdaa.evaluation.paper_b.truth"

INFERENCE_BOUNDARY_PREFIXES: tuple[str, ...] = (
    "kdaa.discovery",
    "kdaa.providers",
    "kdaa.pipeline",
    "kdaa.evaluation.paper_b.adapters",
)

SRC_ROOT = Path(__file__).resolve().parents[3]


def _iter_source_files(prefix: str) -> list[Path]:
    package_dir = SRC_ROOT.joinpath(*prefix.split("."))
    if package_dir.is_dir():
        return sorted(package_dir.rglob("*.py"))
    module_file = SRC_ROOT.joinpath(*prefix.split(".")).with_suffix(".py")
    return [module_file] if module_file.is_file() else []


def _module_name_for(path: Path) -> str:
    return ".".join(path.relative_to(SRC_ROOT).with_suffix("").parts)


def _imports_truth_module(source_path: Path) -> bool:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == TRUTH_MODULE or alias.name.startswith(TRUTH_MODULE + "."):
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == TRUTH_MODULE or node.module.startswith(TRUTH_MODULE + "."):
                return True
            if node.module == "kdaa.evaluation.paper_b" and any(
                alias.name == "truth" for alias in node.names
            ):
                return True
    return False


def find_truth_leakage(
    prefixes: tuple[str, ...] = INFERENCE_BOUNDARY_PREFIXES,
) -> dict[str, list[str]]:
    """Return ``{prefix: [violating module names]}`` for every boundary namespace that
    contains at least one module statically importing the truth-side module."""
    violations: dict[str, list[str]] = {}
    for prefix in prefixes:
        offenders = [
            _module_name_for(source_path)
            for source_path in _iter_source_files(prefix)
            if _imports_truth_module(source_path)
        ]
        if offenders:
            violations[prefix] = offenders
    return violations
