# Data governance and responsible use

KDAA-AI can produce sensitive inferences even from public records. A public paper, repository, grant, or profile was created for one purpose; aggregating those traces into a capability or opportunity map creates a different informational object.

## Governing principles

### Purpose limitation

Define why the focal unit is being analyzed and who benefits. Do not repurpose the system for covert monitoring, ranking, or high-stakes employment decisions.

### Boundary clarity

Record who and what belongs to the focal unit. Team and laboratory assets may be collective, member-specific, institution-dependent, or temporary.

### Trace–claim separation

Preserve the distinction between an observed trace and an inferred asset claim. A title, coauthorship, or repository presence is not conclusive evidence of capability or ownership.

### Data minimization

Ingest the minimum evidence needed for the stated research purpose. More data can increase surveillance, identity errors, and false confidence.

### Attribution and collective ownership

Retain contribution roles, collaborators, dependencies, and uncertainty. Do not appropriate collaborators' knowledge into the focal unit's asset portfolio.

### Human correction and appeal

Any real focal unit should be able to inspect supporting evidence, reject or narrow claims, identify missing context, and challenge downstream use.

### Negative evidence retention

Rejected hypotheses and contradicting traces should not disappear simply because they reduce apparent performance. Closed-loop learning requires error retention.

### Value capture transparency

An amplification workflow can create public or organizational value while shifting credit, IP, bargaining power, data, or platform advantage away from the focal unit. Outcome studies must distinguish realized and captured value.

## Sensitive traces

`EvidenceTrace.sensitive` flags records that should receive stricter handling. In hybrid/LLM mode, sensitive traces are excluded unless `allow_sensitive_traces` is explicitly enabled.

This flag is a control point, not a complete privacy classification system.

## Public versus private deployment

The public research repository is suitable for:

- synthetic data;
- licensed public records;
- manually constructed non-sensitive examples;
- reproducible benchmark artifacts.

Production use with CVs, institutional files, emails, interviews, internal grants, HR records, or confidential projects requires access control, encryption, retention rules, incident response, and institutional review not implemented in v0.1.

## Prohibited or inappropriate uses

- covert employee or faculty surveillance;
- automated hiring, promotion, tenure, funding, admission, or compensation decisions;
- unsupported reputation or expertise ranking;
- de-anonymization or inference about protected/private traits;
- scraping contrary to source terms or law;
- sending confidential records to an external model without authorization;
- publishing provisional claims about real individuals without review;
- claiming that a high score predicts future performance or economic value.

## Release checklist for real cases

Before sharing a result:

1. verify focal-unit identity and boundaries;
2. verify source terms and redistribution rights;
3. remove secrets, confidential records, and sensitive personal data;
4. inspect every asset claim and its evidence links;
5. check contribution attribution and collaborator dependencies;
6. label all scores as proxies;
7. retain caveats and warnings in the report;
8. document any model/provider and AI assistance;
9. obtain required consent or institutional approval;
10. decide whether the result should remain private.
