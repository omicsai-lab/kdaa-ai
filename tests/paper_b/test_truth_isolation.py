"""Critical scientific isolation requirement: inference-side code must never import the
truth-side module (see kdaa/evaluation/paper_b/truth.py and boundary.py).

These tests exercise the static AST-based detector directly (proving it actually detects a
real violation, not just returning an empty result trivially) and then run it against the
real, current inference-boundary namespaces.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from kdaa.evaluation.paper_b.boundary import (
    INFERENCE_BOUNDARY_PREFIXES,
    TRUTH_MODULE,
    _imports_truth_module,
    find_truth_leakage,
)


@pytest.mark.parametrize(
    "source",
    [
        "import kdaa.evaluation.paper_b.truth\n",
        "import kdaa.evaluation.paper_b.truth as truth\n",
        "from kdaa.evaluation.paper_b.truth import TruthBundle\n",
        "from kdaa.evaluation.paper_b import truth\n",
    ],
)
def test_detector_flags_every_form_of_truth_import(tmp_path: Path, source: str) -> None:
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
def test_detector_does_not_flag_safe_imports(tmp_path: Path, source: str) -> None:
    safe = tmp_path / "safe.py"
    safe.write_text(source, encoding="utf-8")
    assert _imports_truth_module(safe) is False


def test_detector_reports_violating_module_name_and_prefix(tmp_path: Path, monkeypatch) -> None:
    # Simulate a future WP4 adapters/ package that violates isolation, using a throwaway
    # source tree so this test does not depend on WP4 having been implemented yet.
    src_root = tmp_path / "src"
    package_dir = src_root / "kdaa" / "evaluation" / "paper_b" / "adapters"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "bad_adapter.py").write_text(
        "from kdaa.evaluation.paper_b.truth import TruthBundle\n", encoding="utf-8"
    )
    (package_dir / "good_adapter.py").write_text(
        "from kdaa.evaluation.paper_b.schemas import PredictionBundle\n", encoding="utf-8"
    )

    import kdaa.evaluation.paper_b.boundary as boundary_module

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
