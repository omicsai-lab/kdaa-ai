# Paper B KBS audit baseline

**Document status:** WP0 record, documentation/config only.
**Backlog reference:** `KDAA-PB-KBS-IMPL-001` v1.0 (`paper_b_kbs_specs/KDAA_Paper_B_KBS_Implementation_Backlog_v1.0.yaml`).

## Frozen audit baseline

- **Branch:** `main`
- **Commit:** `80df46c`
- **Package version:** `0.1.0`

This is the exact repository state the Paper B KBS scientific freeze, protocol clarifications, and experiment lock were authored against. Work packages WP1 and later build forward from this commit. It does not move retroactively; if a defect is found later, the correction is layered on top per the change-control rules in the freeze (Section 23) and recorded in [Protocol deviations](protocol_deviations.md), not by editing this baseline.

## Authoritative source documents and hashes

The following documents are the scientific and protocol authority for Paper B (KBS-track). They were supplied out-of-band in `paper_b_kbs_specs/` and are reproduced verbatim below without paraphrase. SHA-256 hashes are given for both the original source file and the in-repo copy; WP0 acceptance requires them to match exactly.

| Source document | In-repo copy | SHA-256 |
|---|---|---|
| `paper_b_kbs_specs/KDAA_Paper_B_KBS_Step1_Step2_Freeze_v1.0.md` | [`paper_b_kbs_claims_evaluation_freeze.md`](paper_b_kbs_claims_evaluation_freeze.md) | `e62b27b06b024aa3eb5463b38630ea7ce69f90e4a6211bc4c67ab03a586c7f40` |
| `paper_b_kbs_specs/KDAA_Paper_B_KBS_Protocol_Clarifications_v1.0.1.md` | [`paper_b_protocol_clarifications_v1.0.1.md`](paper_b_protocol_clarifications_v1.0.1.md) | `1867d0868881217c2041968311907da80b45cce0633892ef60b226a7fec7170c` |
| `paper_b_kbs_specs/KDAA_Paper_B_KBS_Experiment_Lock_v1.0.yaml` | [`../configs/paper_b/experiment_lock.yaml`](../configs/paper_b/experiment_lock.yaml) | `411668256fbfe080a278495ba3a8dad1f0f201ff6c8b870bd34824c60858d5df` |

Hashes were computed with `shasum -a 256` and verified against the manifest shipped alongside the source package (`KDAA_Paper_B_KBS_Repo_Gap_Audit_Package_v1.0.1.sha256`) before copying. The in-repo copies above were produced with a byte-for-byte file copy, not retyped or reformatted, so the hashes match.

## Journal positioning (frozen)

- **First-submission target:** Knowledge-Based Systems (KBS)
- **Fallback:** Expert Systems with Applications (ESWA)

This supersedes the exploratory journal-positioning discussion in [Paper B scope](paper_b_scope.md); see that document for the cross-link.

## Scope of this record

WP0 is documentation/config integration only. It does not modify runtime code, tests, committed legacy benchmark or robustness results, or the package version. Later work packages (WP1 onward) implement the code referenced by the frozen protocol; see [`KDAA_Paper_B_KBS_Claude_Code_Execution_Plan_v1.0.1.md`](../paper_b_kbs_specs/KDAA_Paper_B_KBS_Claude_Code_Execution_Plan_v1.0.1.md) for the work-package sequence.
