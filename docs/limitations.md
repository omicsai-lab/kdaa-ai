# Limitations

## Conceptual limitations

- The KDAA theory is a working framework, not an established theory with validated constructs.
- Discovery, assessment, and amplification may not always be empirically separable stages.
- A “latent asset” may be discovered, newly created through AI interaction, or socially constructed through labeling; v0.1 does not resolve this ontological issue.
- The boundary between knowledge assets, resources, capabilities, expertise, routines, and human capital remains open to refinement.
- Opportunity templates can impose the framework's preferred forms of value rather than reveal all legitimate value pathways.

## Evidence limitations

- Public traces are incomplete and unevenly distributed.
- Names can be ambiguous; affiliations and identities change.
- Coauthorship and repository membership do not resolve contribution.
- Tacit and relational assets are difficult to infer from public evidence.
- Absence of evidence is not evidence of absence.
- Exact/source-record-equivalent duplicates are de-weighted, but semantic near-duplicates, derivative outputs, and dependent sources can still create false confidence.
- Source recency does not guarantee current capability.

## Algorithmic limitations

- The ontology is manually declared and domain-skewed toward AI, research, biomedicine, and knowledge work.
- Lexical matching misses synonyms and context and can overmatch acronyms.
- Rule-based combinative assets rely on co-occurrence rather than demonstrated integration.
- Relational assets use repeated co-participation, not actual trust, access, or current availability.
- End-to-end execution assets infer workflow span from heterogeneous traces rather than process observations.
- Proxy formulas are heuristic and not statistically calibrated.
- Opportunity scoring reflects the catalog and strategic-goal text.
- Conservative trace identity keys can miss semantic duplicates or merge records whose source identifiers are incorrectly reused.
- LLM mode can still produce plausible but conceptually weak hypotheses despite trace-ID validation.

## Benchmark limitations

- Synthetic ground truth is generated from the same ontology used by the pipeline.
- The baseline is intentionally simple.
- Concept recovery is not asset validity.
- Provenance completeness can be mechanically high even when supporting traces are weak or misattributed.
- Determinism is evaluated on deterministic mode only.
- Runtime results are environment-specific.
- Perturbation checks encode expected engineering directions; they do not validate the underlying constructs.

## Interface and deployment limitations

- Streamlit is a research interface, not an enterprise application.
- Authentication, role-based access, encryption, audit administration, and deletion workflows are not production-ready.
- PDF/CV parsing is conservative and format-sensitive.
- OpenAlex/GitHub connectors depend on external schemas and terms.
- No direct ORCID, Crossref, grants, patents, institutional repository, or private document connector is included.

## Human and causal limitations

- Human confirmation is not present in the committed benchmark.
- Usefulness, novelty, fairness, legitimacy, and correction burden are unknown.
- No counterfactual human-only study has estimated AI amplification.
- Realized and captured value are not observed.
- Longitudinal closed-loop learning is represented in the schema but not validated.

## Reputational limitation

The polished form of an AI-generated theory or report can exceed its underlying intellectual maturity. Users should treat completeness of prose, figures, or software as distinct from depth of thought, empirical support, and defensibility.
