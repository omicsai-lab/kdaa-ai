"""C1/C2 prompts must contain no KDAA design knowledge (Freeze Section 10, C1/C2)."""

from __future__ import annotations

from kdaa.evaluation.paper_b.adapters import c1_generic_llm, c2_evidence_linked

# Terms that would leak KDAA-specific design knowledge into a baseline prompt. Checked
# case-insensitively against both the fixed system prompt and a representative user
# prompt built from real case data.
_FORBIDDEN_KDAA_TERMS = [
    "kdaa",
    "epistemic state",
    "bounded claim",
    "provenance",
    "hypothesis",
    "provisional",
    "confirmed asset",
    "attribution confidence",
    "credibility",
    "verification gate",
    "amplification",
    "focal unit boundary",
    "trace-hypothesis separation",
]


def _sample_prompts():
    opportunities = [("opp-1", "Title one", "Description one"), ("opp-2", "Title two", "Description two")]
    c1_user = c1_generic_llm.build_user_prompt(
        "Test Unit", "A test description.", ["Some evidence text about software."], opportunities
    )
    c2_user = c2_evidence_linked.build_user_prompt(
        "Test Unit", "A test description.", [("t1", "Some evidence text about software.")], opportunities
    )
    return c1_user, c2_user


def test_c1_system_and_user_prompt_contain_no_kdaa_terms() -> None:
    c1_user, _ = _sample_prompts()
    combined = (c1_generic_llm.SYSTEM_PROMPT + "\n" + c1_user).lower()
    for term in _FORBIDDEN_KDAA_TERMS:
        assert term not in combined, f"C1 prompt leaks KDAA term: {term!r}"


def test_c2_system_and_user_prompt_contain_no_kdaa_terms() -> None:
    _, c2_user = _sample_prompts()
    combined = (c2_evidence_linked.SYSTEM_PROMPT + "\n" + c2_user).lower()
    for term in _FORBIDDEN_KDAA_TERMS:
        assert term not in combined, f"C2 prompt leaks KDAA term: {term!r}"


def test_c1_prompt_does_not_mention_evidence_ids() -> None:
    c1_user, _ = _sample_prompts()
    assert "evidence_ids" not in c1_user
    assert "evidence id" not in c1_user.lower()


def test_c2_prompt_requests_evidence_ids_and_shows_stable_ids() -> None:
    _, c2_user = _sample_prompts()
    assert "evidence_ids" in c2_user
    assert "[t1]" in c2_user


def test_c1_and_c2_prompts_request_the_same_neutral_ownership_vocabulary() -> None:
    c1_user, c2_user = _sample_prompts()
    vocabulary = "focal_unit|shared|organizational|external|unresolved"
    assert vocabulary in c1_user
    assert vocabulary in c2_user


def test_c1_and_c2_prompts_present_all_opportunity_ids_for_ranking() -> None:
    c1_user, c2_user = _sample_prompts()
    for opportunity_id in ("opp-1", "opp-2"):
        assert opportunity_id in c1_user
        assert opportunity_id in c2_user
