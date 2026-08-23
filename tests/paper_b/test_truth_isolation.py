"""Critical scientific isolation requirement: inference-side code must never import the
truth-side module (see kdaa/evaluation/paper_b/truth.py and boundary.py).

These tests exercise the static AST-based detector directly (proving it actually detects a
real violation, not just returning an empty result trivially), including relative-import
forms resolved via ``ImportFrom.level`` exactly as Python's import system would, and then
run it against the real, current inference-boundary namespaces.

Note (correction 3): this is *direct* import-boundary enforcement only -- a boundary module
that imports some other, non-boundary module which itself imports ``truth`` is not caught.
That is intentionally out of scope here; see the module docstrings in ``boundary.py`` and
``truth.py`` for the accurate scope statement, and ``test_wording_does_not_overclaim_*``
below for a guard against that claim silently drifting back into the docstrings.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from kdaa.evaluation.paper_b.boundary import (
    INFERENCE_BOUNDARY_PREFIXES,
    TRUTH_MODULE,
    _imports_truth_module,
    _package_for,
    find_truth_leakage,
)


def _build_synthetic_paper_b_tree(tmp_path: Path) -> Path:
    """A throwaway ``src/kdaa/evaluation/paper_b/`` skeleton, so relative-import tests can
    place a file at a realistic depth (e.g. ``adapters/`` one level below ``truth.py``) and
    have ``.truth``/``..truth`` resolve exactly as they would in the real package layout.
    Files are empty stubs; only their presence/location and the planted offender's own
    source matter, since detection is static (``ast``), not a real import.
    """
    src_root = tmp_path / "src"
    paper_b_dir = src_root / "kdaa" / "evaluation" / "paper_b"
    adapters_dir = paper_b_dir / "adapters"
    adapters_dir.mkdir(parents=True)
    (src_root / "kdaa" / "__init__.py").write_text("", encoding="utf-8")
    (src_root / "kdaa" / "evaluation" / "__init__.py").parent.mkdir(exist_ok=True)
    (src_root / "kdaa" / "evaluation" / "__init__.py").write_text("", encoding="utf-8")
    (paper_b_dir / "__init__.py").write_text("", encoding="utf-8")
    (paper_b_dir / "truth.py").write_text("", encoding="utf-8")
    (paper_b_dir / "schemas.py").write_text("", encoding="utf-8")
    (adapters_dir / "__init__.py").write_text("", encoding="utf-8")
    return src_root


@pytest.mark.parametrize(
    "source",
    [
        "import kdaa.evaluation.paper_b.truth\n",
        "import kdaa.evaluation.paper_b.truth as truth\n",
        "from kdaa.evaluation.paper_b.truth import TruthBundle\n",
        "from kdaa.evaluation.paper_b import truth\n",
    ],
)
def test_detector_flags_every_form_of_absolute_truth_import(tmp_path: Path, source: str) -> None:
    offending = tmp_path / "offender.py"
    offending.write_text(source, encoding="utf-8")
    assert _imports_truth_module(offending) is True


@pytest.mark.parametrize(
    "source",
    [
        "from kdaa.evaluation.paper_b import schemas\n",
        "from kdaa.evaluation.paper_b.schemas import PredictionBundle\n",
        "import kdaa.evaluation.paper_b.config\n",
        "# no imports at all\n",
    ],
)
def test_detector_does_not_flag_safe_absolute_imports(tmp_path: Path, source: str) -> None:
    safe = tmp_path / "safe.py"
    safe.write_text(source, encoding="utf-8")
    assert _imports_truth_module(safe) is False


def test_relative_single_dot_from_truth_import_is_flagged(tmp_path: Path, monkeypatch) -> None:
    # A hypothetical sibling of truth.py inside kdaa.evaluation.paper_b itself:
    # `from .truth import TruthBundle` at level=1 resolves to exactly TRUTH_MODULE.
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    offender = src_root / "kdaa" / "evaluation" / "paper_b" / "sibling_of_truth.py"
    offender.write_text("from .truth import TruthBundle\n", encoding="utf-8")
    assert _imports_truth_module(offender) is True


def test_relative_double_dot_from_truth_import_is_flagged(tmp_path: Path, monkeypatch) -> None:
    # The realistic WP4 shape: an adapter one level below paper_b writing
    # `from ..truth import TruthBundle` (level=2) resolves up to paper_b.truth.
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    offender = src_root / "kdaa" / "evaluation" / "paper_b" / "adapters" / "bad_adapter.py"
    offender.write_text("from ..truth import TruthBundle\n", encoding="utf-8")
    assert _imports_truth_module(offender) is True


def test_relative_dot_import_truth_submodule_is_flagged(tmp_path: Path, monkeypatch) -> None:
    # `from . import truth` (module=None, level=1) -- the ImportFrom.module is absent, so
    # this exercises the alias-name fallback path in _imports_truth_module.
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    offender = src_root / "kdaa" / "evaluation" / "paper_b" / "sibling_of_truth.py"
    offender.write_text("from . import truth\n", encoding="utf-8")
    assert _imports_truth_module(offender) is True


def test_relative_dotdot_import_truth_submodule_is_flagged(tmp_path: Path, monkeypatch) -> None:
    # `from .. import truth` (module=None, level=2) from one level below paper_b.
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    offender = src_root / "kdaa" / "evaluation" / "paper_b" / "adapters" / "bad_adapter.py"
    offender.write_text("from .. import truth\n", encoding="utf-8")
    assert _imports_truth_module(offender) is True


def test_relative_import_of_unrelated_sibling_is_not_flagged(tmp_path: Path, monkeypatch) -> None:
    # `from ..schemas import PredictionBundle` at the same depth/shape as the flagged
    # `from ..truth import TruthBundle` case above must NOT be flagged: proves the
    # resolver distinguishes modules by their resolved path, not just "is relative".
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    safe = src_root / "kdaa" / "evaluation" / "paper_b" / "adapters" / "good_adapter.py"
    safe.write_text("from ..schemas import PredictionBundle\n", encoding="utf-8")
    assert _imports_truth_module(safe) is False


def test_relative_import_escaping_the_source_tree_does_not_raise(tmp_path: Path, monkeypatch) -> None:
    # A relative import with more leading dots than the package has depth (e.g. `from
    # ....x import y` at the source root) must degrade to "not resolvable / not flagged"
    # rather than raising, since it cannot possibly resolve to the truth module.
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    offender = src_root / "kdaa" / "evaluation" / "paper_b" / "sibling_of_truth.py"
    offender.write_text("from ........truth import TruthBundle\n", encoding="utf-8")
    assert _imports_truth_module(offender) is False


def test_package_for_handles_init_and_regular_modules(tmp_path: Path, monkeypatch) -> None:
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    paper_b_dir = src_root / "kdaa" / "evaluation" / "paper_b"
    assert _package_for(paper_b_dir / "schemas.py") == "kdaa.evaluation.paper_b"
    assert _package_for(paper_b_dir / "adapters" / "__init__.py") == "kdaa.evaluation.paper_b.adapters"


def test_package_for_outside_src_root_degrades_gracefully() -> None:
    # A file that isn't under the real SRC_ROOT at all (e.g. a bare tmp_path snippet used
    # by the absolute-import tests above) must not raise; it simply cannot resolve any
    # relative import, which is the correct conservative behavior.
    assert _package_for(Path("/definitely/not/under/src_root/module.py")) == ""


def test_detector_reports_violating_module_name_and_prefix(tmp_path: Path, monkeypatch) -> None:
    # Simulate a future WP4 adapters/ package that violates isolation, using a throwaway
    # source tree so this test does not depend on WP4 having been implemented yet.
    import kdaa.evaluation.paper_b.boundary as boundary_module

    src_root = _build_synthetic_paper_b_tree(tmp_path)
    adapters_dir = src_root / "kdaa" / "evaluation" / "paper_b" / "adapters"
    (adapters_dir / "bad_adapter.py").write_text(
        "from kdaa.evaluation.paper_b.truth import TruthBundle\n", encoding="utf-8"
    )
    (adapters_dir / "good_adapter.py").write_text(
        "from kdaa.evaluation.paper_b.schemas import PredictionBundle\n", encoding="utf-8"
    )

    monkeypatch.setattr(boundary_module, "SRC_ROOT", src_root)
    violations = find_truth_leakage(prefixes=("kdaa.evaluation.paper_b.adapters",))
    assert "kdaa.evaluation.paper_b.adapters" in violations
    offenders = violations["kdaa.evaluation.paper_b.adapters"]
    assert any("bad_adapter" in name for name in offenders)
    assert not any("good_adapter" in name for name in offenders)


def test_no_current_inference_boundary_module_imports_truth() -> None:
    violations = find_truth_leakage()
    assert violations == {}


def test_inference_boundary_prefixes_cover_existing_inference_namespaces() -> None:
    # Guards against silently narrowing the boundary list in a future edit: today's
    # production inference namespaces must remain covered.
    assert "kdaa.discovery" in INFERENCE_BOUNDARY_PREFIXES
    assert "kdaa.providers" in INFERENCE_BOUNDARY_PREFIXES
    assert "kdaa.pipeline" in INFERENCE_BOUNDARY_PREFIXES
    # The WP4 adapter namespace does not exist yet; it is listed so the check starts
    # covering it automatically once WP4 creates it, with no further code change.
    assert "kdaa.evaluation.paper_b.adapters" in INFERENCE_BOUNDARY_PREFIXES


def test_paper_b_package_does_not_reexport_truth_module() -> None:
    import kdaa.evaluation.paper_b as paper_b_pkg

    assert "TruthBundle" not in dir(paper_b_pkg)
    assert "truth" not in paper_b_pkg.__all__


def test_truth_module_constant_matches_real_module_path() -> None:
    from kdaa.evaluation.paper_b import truth as truth_module

    assert truth_module.__name__ == TRUTH_MODULE


def test_ast_can_actually_parse_every_current_boundary_source_file() -> None:
    # Sanity check that the detector's file discovery is not silently finding zero files
    # for namespaces that do exist today (kdaa.discovery, kdaa.pipeline, kdaa.providers).
    from kdaa.evaluation.paper_b.boundary import _iter_source_files

    existing_prefixes = ["kdaa.discovery", "kdaa.providers", "kdaa.pipeline"]
    for prefix in existing_prefixes:
        files = _iter_source_files(prefix)
        assert files, f"expected at least one source file under {prefix}"
        for source_path in files:
            ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))


def test_wording_does_not_overclaim_transitive_enforcement() -> None:
    # Correction 3: the module docstrings must not claim "directly or indirectly" (i.e.
    # transitive dependency-graph) enforcement, since only direct imports are detected.
    import kdaa.evaluation.paper_b.boundary as boundary_module
    import kdaa.evaluation.paper_b.truth as truth_module

    for module in (boundary_module, truth_module):
        docstring = module.__doc__ or ""
        assert "directly or indirectly" not in docstring
