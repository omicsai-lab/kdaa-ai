# Public data sources

## OpenAlex connector

File: `src/kdaa/ingestion/openalex.py`.

The connector can resolve:

- an OpenAlex author ID;
- an ORCID identifier;
- an author name.

It then retrieves up to the requested number of works and maps them to publication traces, including title, abstract when reconstructable, date, source identifiers, authorship information, and concepts/topics available in the response.

### Environment

```bash
export OPENALEX_API_KEY="..."
export OPENALEX_EMAIL="you@example.edu"
```

Production use should provide a free OpenAlex API key; limited keyless demo access may still be available. Identity resolution from a name can return the wrong person and must be reviewed. ORCID is preferable when available but still does not prove contribution to every work.

Official documentation:

- <https://developers.openalex.org/api-reference/authentication>
- <https://developers.openalex.org/api-reference/authors>
- <https://developers.openalex.org/api-reference/works>

## GitHub connector

File: `src/kdaa/ingestion/github.py`.

The connector retrieves a public user/organization profile and repositories and maps repository metadata to software traces. Forks are excluded by default.

### Environment

```bash
export GITHUB_TOKEN="..."
```

A token is strongly recommended. Public repository metadata do not establish authorship of all code, scientific validity, maintenance quality, or license compatibility.

Official documentation:

- <https://docs.github.com/en/rest/users/users>
- <https://docs.github.com/en/rest/repos/repos>
- <https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api>

## Local files

Files: `src/kdaa/ingestion/local.py`.

Supported paths include:

- canonical JSON/YAML `UnitBundle` files;
- PDF or text CV-like documents parsed into document/publication-like traces;
- multiple bundles merged with trace-ID collision handling and conservative exact/source-record-equivalent de-duplication.

Use:

```bash
kdaa ingest-cv researcher_cv.pdf \
  --unit-id unit:researcher \
  --unit-name "Researcher Name" \
  --institution "Georgetown University" \
  --output data/cv_bundle.json
```

The CV-like parser is intentionally conservative and cannot reliably infer authorship, dates, sections, or contribution from every document format. Imported traces are marked sensitive. Convert high-stakes records to the canonical schema manually.

## Synthetic data

File: `src/kdaa/ingestion/synthetic.py`.

Synthetic scenarios are clearly marked `is_synthetic=true`, use `synthetic://` source URIs, and declare `CC0-1.0` on traces. They are suitable for:

- demos;
- tests;
- software regression;
- controlled benchmark development.

They are not evidence for real-world construct validity or user value.

## ORCID

A direct ORCID API connector is not included in v0.1. OpenAlex can resolve an ORCID-linked author record. A future direct connector should use ORCID's authenticated public/member API rather than scraping profile pages.
