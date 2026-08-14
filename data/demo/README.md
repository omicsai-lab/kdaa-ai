# Demonstration data

All records in this directory are fully synthetic and describe no real person, team, laboratory, institution, publication, grant, or repository.

| File | Focal unit | Purpose |
|---|---|---|
| `synthetic_researcher.json` | researcher | richest end-to-end demo and committed report |
| `synthetic_lab.json` | laboratory | collective asset boundaries and dependencies |
| `synthetic_team.json` | project team | temporary cross-functional unit |
| `calibration_records.example.json` | optional lifecycle input | illustrates confirm/narrow/reject records; IDs must be replaced with a real run's IDs |
| `outcome_records.example.json` | optional lifecycle input | illustrates realized/captured value records; IDs must be replaced |

The synthetic traces carry `source_kind="synthetic"`, `synthetic://` URIs, `license="CC0-1.0"`, and `is_synthetic=true` on the focal unit.

Run:

```bash
kdaa analyze data/demo/synthetic_researcher.json --output results/demo-from-file
```
