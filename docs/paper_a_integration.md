# Integrating the repository into Paper A

## Role of the repository

Paper A remains a theory-building paper. The repository should enter it as a **computational instantiation**, not as a full system-evaluation section.

The appropriate claim is:

> The framework can be represented in an executable data model and pipeline that preserves the distinctions among evidence traces, asset hypotheses, asset-level assessment, opportunity-specific amplification, calibration, and outcomes.

The inappropriate claim is:

> The prototype validates the theory or proves that the proposed assets and opportunities are correct.

## Recommended insertion

Add one section of approximately three to five manuscript pages after the theoretical framework or illustrative case:

### Computational instantiation of the KDAA framework

Suggested subsections:

1. **Design requirements derived from theory**
   - trace–asset separation;
   - provenance;
   - bounded/falsifiable claims;
   - asset-level assessment;
   - opportunity-specific baselines;
   - no automatic confirmation.
2. **Prototype architecture**
   - one compact architecture figure;
   - data model and six-stage mapping.
3. **Illustrative synthetic execution**
   - one clearly synthetic focal unit;
   - input trace count;
   - example asset record with evidence/exclusions;
   - example opportunity with baseline/tasks/gates;
   - zero confirmed assets.
4. **What the instantiation demonstrates**
   - operationalizability and internal coherence.
5. **What it does not demonstrate**
   - construct validity, human acceptance, causal value, or generalizability.

## Candidate figure

Use a simplified version of:

![Theory to artifact](assets/theory_to_artifact.png)

The full software architecture belongs in Paper B or an appendix/repository.

## Candidate table

| Theoretical construct | Prototype object | Demonstrated property | Unresolved empirical question |
|---|---|---|---|
| Knowledge trace | `EvidenceTrace` | observations remain separately addressable | are the traces complete and correctly attributed? |
| Asset hypothesis | `AssetRecord` | active claims require provenance and boundaries | do humans confirm the asset? |
| Asset credibility | `AssetAssessment` | dimensions are explicit and inspectable | are they valid measures? |
| Asset–opportunity fit | `AmplificationOpportunity` | beneficiary/problem/channel are represented | is the opportunity useful and timely? |
| AI amplifiability | baseline/tasks/gates/gain vector | construct is opportunity-specific | does AI create counterfactual gain? |
| Closed-loop learning | calibration/outcome records | data structures support revision | does repeated use improve precision and value? |

## Writing boundary

Paper A should not inherit every implementation detail. Avoid:

- endpoint lists;
- code listings;
- UI screenshots unless one is theoretically necessary;
- synthetic benchmark claims as theory evidence;
- extensive scoring formulas;
- product-roadmap language.

## Authorship and AI-use concern

Because the theory draft was developed with substantial AI assistance, the computational instantiation should be used as a forcing function for intellectual ownership. Before submission, the author should be able to reconstruct and defend:

- why each core construct is necessary;
- why existing knowledge audit, expert finding, dynamic capability, and AI-augmentation theories do not already explain the full phenomenon;
- what implementation revealed to be redundant or underspecified;
- why the theory is not merely a software pipeline described in conceptual language.

The final Paper A should be rewritten and owned at a level appropriate to the target journal's AI-use policy.
