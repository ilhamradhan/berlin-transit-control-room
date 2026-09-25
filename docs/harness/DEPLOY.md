# Deployment strategy

**Status:** Stage 4 static delivery is planned; no TransitOps service has been deployed.

## Runtime target

The collection and transformation stack remains private and finite. Stage 4
does not turn the VPS into a continuously running public application.

Existing/private components:

- Cron production path and Dockerized synthetic Airflow learning artifact
- Filesystem Parquet and versioned DuckDB releases

Stage 4 delivery components:

- Build-time exporter for compact sanitized aggregates
- Static Transit Reliability and System Documentation pages
- Local or CLI/demo-bound read-only RAG evaluation
- Optional Cloudflare feasibility spike using synthetic artifacts only

Existing unrelated containers remain outside this project’s lifecycle.

## Startup safety

The planned preflight will report resource and port conflicts and refuse unsafe startup. It will never stop other containers. Stage 1 measurements will set the memory limits.

## Application access

No operational application or writable public endpoint is deployed in Stage 4.
The private verified release remains outside the static site.

## Public presentation

The required public artifact is a static branded case study at the user’s preferred portfolio route:

```text
https://ilrama.com/p/transitops-berlin
```

It will contain architecture, screenshots, a recorded demo, methodology, limitations, harness evidence, and a link to the public repository. A public live Streamlit deployment is optional and not required for project acceptance.

## Data and secret exclusions

Do not deploy or publish:

- Airflow credentials or metadata database
- `.env` values
- Unfiltered logs
- Real transit archives through GitHub or the public site
- Local embedding-model files or retrieval index
- Writable operational endpoints on the public internet

## Recovery and rollback

- Failed dbt candidates leave the current DuckDB release active.
- Current and previous verified releases are retained.
- No recovery controls are deployed in Stage 4.
- If Cloudflare adoption is later approved, rollback/unpublish procedures must
  be recorded before external publication.

## Future cloud option

Cloudflare Pages/R2/Workers may be evaluated with synthetic artifacts only if
measurements justify them. Adoption is optional and reversible. The private
archive is not uploaded; Supabase, MotherDuck, and BigQuery are not part of
version one.
