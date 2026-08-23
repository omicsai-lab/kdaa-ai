"""Direct import-boundary enforcement between Paper B truth-side and inference-side code.

This makes truth leakage hard *by construction* rather than by convention: instead of
trusting that inference code never imports ``kdaa.evaluation.paper_b.truth``, this module
statically parses (via ``ast``, not a real import) every source file under each inference
boundary namespace and reports any that directly import the truth module -- as an absolute
import, an aliased import, a ``from ... import ...``, or a relative import (``from .truth``,
``from ..truth``, ``from . import truth``, etc.), resolved against the importing file's own
package using ``ImportFrom.level`` exactly as Python's import system would.

This is **direct** import-boundary enforcement only: it detects when a boundary-namespace
file itself imports the truth module. It does not walk the dependency graph, so a boundary
module that imports some other, non-boundary module which in turn imports ``truth`` would
not be flagged by this check. Extending this to transitive (whole dependency graph)
enforcement is explicitly left to a later work package; nothing here should be read as
already providing it.

Using ``ast`` rather than importing the target modules means the check works even for a
namespace that does not exist yet -- ``kdaa.evaluation.paper_b.adapters`` is not created
until WP4, so today it simply contributes zero files and passes trivially. Extend
``INFERENCE_BOUNDARY_PREFIXES`` as later work packages add new comparator/adapter
namespaces; no other change is required for the direct-import check to start covering them.
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
    """The dotted module name Python would assign to ``path`` (``__init__.py`` maps to its
    containing package's own name, not to a trailing ``.__init__``)."""
    rel = path.relative_to(SRC_ROOT)
    if rel.name == "__init__.py":
        return ".".join(rel.parent.parts)
    return ".".join(rel.with_suffix("").parts)


def _package_for(path: Path) -> str:
    """The dotted package name Python would use as ``__package__`` when resolving a
    relative import inside ``path`` -- itself for a package's ``__init__.py``, otherwise
    its containing directory. Returns ``""`` for a path outside ``SRC_ROOT`` (e.g. a bare
    snippet file used to test absolute-import detection in isolation); such a path cannot
    have a real relative import resolved against it, so this degrades safely rather than
    raising, and any relative import inside it will simply fail to match ``TRUTH_MODULE``.
    """
    try:
        rel = path.relative_to(SRC_ROOT)
    except ValueError:
        return ""
    parts = rel.parent.parts if rel.name == "__init__.py" else rel.with_suffix("").parent.parts
    return ".".join(parts)


def _resolve_relative_import(*, package: str, level: int, module: str | None) -> str | None:
    """Resolve an ``ImportFrom`` node's ``(level, module)`` to an absolute dotted module
    path, given the importing file's own package (``level=0`` means already absolute).

    Mirrors Python's own relative-import resolution: ``level=1`` (``from .x``) refers to
    the current package; ``level=2`` (``from ..x``) to its parent; and so on. Returns
    ``None`` only when ``module`` is absent and the resolved base package is empty (e.g.
    ``from . import x`` at the source root), which cannot resolve to any real module.
    """
    if level == 0:
        return module
    package_parts = package.split(".") if package else []
    drop = level - 1
    base_parts = package_parts[: max(0, len(package_parts) - drop)]
    base = ".".join(base_parts)
    if module:
        return f"{base}.{module}" if base else module
    return base or None


def _imports_truth_module(source_path: Path) -> bool:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    package = _package_for(source_path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == TRUTH_MODULE or alias.name.startswith(TRUTH_MODULE + "."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            resolved_module = _resolve_relative_import(
                package=package, level=node.level, module=node.module
            )
            if resolved_module is None:
                continue
            if resolved_module == TRUTH_MODULE or resolved_module.startswith(TRUTH_MODULE + "."):
                return True
            if any(alias.name == "truth" for alias in node.names):
                candidate = f"{resolved_module}.truth" if resolved_module else "truth"
                if candidate == TRUTH_MODULE:
                    return True
    return False


def find_truth_leakage(
    prefixes: tuple[str, ...] = INFERENCE_BOUNDARY_PREFIXES,
) -> dict[str, list[str]]:
    """Return ``{prefix: [violating module names]}`` for every boundary namespace that
    contains at least one module directly importing the truth-side module (see module
    docstring: direct-import detection only, not a dependency-graph traversal)."""
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
