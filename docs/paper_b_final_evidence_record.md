# KDAA Paper B — Final Evidence Record

**Status:** Frozen final empirical record
**Archive date:** 2026-08-23
**Repository branch:** `paper-b/evaluation`

## Execution provenance

Final evaluation execution commit:

```text
90b560c58486fb36ee4153cdd9a57e6c5fec59ec
```

Commit message:

```text
Add frozen Paper B final execution pipeline
```

The final dataset was generated exactly once from this committed and frozen evaluation pipeline. No case replacement, result-dependent tuning, selective rerun, prompt change, scorer change, model change, or protocol deviation occurred after final data generation.

## Final dataset

Total cases:

```text
240
```

Composition:

* 180 core factorial cases
* 60 challenge cases
* 10 visible candidate opportunities per case

Final LLM subset:

* 30 core cases
* 30 challenge cases
* 60 total cases
* 3 intended repeats
* C1, C2, and C4
* 540 intended live LLM attempts
* 540 completed attempts

## Dataset hashes

Evidence dataset SHA-256:

```text
05ab777f178833aea4a2fd75e5c4f2140ed153352049622834a27d9520e5724e
```

Truth dataset SHA-256:

```text
744a0887853b1579382f9c51082c622ff065a748f665b871757645bfa9e009ac
```

Per-file hashes for all final evidence and truth files are recorded in:

```text
results/paper_b/final/manifests/final_dataset_manifest.json
```

## Archived final evidence package

Private off-repository archive:

```text
kdaa-paper-b-final-evidence-20260823.tar.gz
```

Archive SHA-256:

```text
618db455217bae86083e9eaa0cf92c7f2915c68a565f006f7ed25dd74c195769
```

Checksum verification:

```text
OK
```

The archive contains:

* 240 final evidence files
* 240 final truth files
* final result artifacts
* final model, experiment, and scorer locks
* final evaluation freeze documentation
* execution commit record
* Python version
* frozen Python environment record
* archive contents manifest

The archive does **not** contain `.env`, API credentials, or other secrets.

## Final empirical record

Final result artifacts are stored under:

```text
results/paper_b/final/
```

including:

```text
manifests/
raw/
metrics/
ablations/
robustness/
summary/
```

The final empirical record was produced under the frozen protocol and model configuration:

```text
Model: gpt-5.4-2026-03-05
Temperature: 0.1
Provider: OpenAI
```

No protocol deviations were recorded during final execution.

## Preservation rule

The archived final dataset and results constitute the authoritative empirical record for KDAA Paper B.

The final dataset must not be regenerated, replaced, edited, or selectively rerun in response to observed results.

Any future re-analysis should operate on the preserved frozen evidence and result artifacts and should be clearly labeled as secondary, sensitivity, or post hoc analysis where applicable.
