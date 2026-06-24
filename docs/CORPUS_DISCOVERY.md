# Corpus Discovery Tooling

`scripts/discover_candidate_papers.py` is research-time tooling for proposing a small,
reviewable set of candidate sources before CORPUS-001 freezes the final corpus manifest. It
does not expose live search through the app or MCP runtime.

## Usage

Deterministic offline run from the committed cache:

```bash
uv run --project packages/shared-schemas python scripts/discover_candidate_papers.py \
  --offline \
  --output corpus_discovery/il10_lps_candidate_manifest.json
```

Live refresh through the local `paper-search` package:

```bash
uv run --project packages/shared-schemas python scripts/discover_candidate_papers.py \
  --refresh-cache \
  --output corpus_discovery/il10_lps_candidate_manifest.json
```

The live path wraps:

```bash
uv run --directory ~/paper-search-mcp paper-search search "<query>" -n 5 \
  -s pubmed,europepmc,semantic,openalex,crossref,biorxiv -y 1990-2026
```

## Inputs

- `corpus_discovery/il10_lps_config.json` defines the selected hero comparison, topic
  buckets, paper-search sources, search queries, bucket caps, and scoring weights.
- `corpus_discovery/cache/il10_lps/*.json` stores raw `paper-search`-shaped metadata for
  deterministic CI and reproducible review.

The default buckets are aligned to `docs/DEMO_DECISIONS.md`: nELISA assay context, selected
perturbagen biology, and PBMC perturbation design for IL-10 under LPS.

## Scoring Policy

Candidates are deduplicated by DOI, then PMID, then normalized title. The tool then computes:

- Impact score: citation count, citation velocity, venue tier, publication type, and recency.
- Relevance score: configured hero-entity matches, bucket semantic-term matches, required
  bucket-term coverage, and title matches.
- Total score: `0.45 * impact + 0.55 * relevance`.

A candidate must pass all configured thresholds to be surfaced:

- `min_impact_score`: `0.45`
- `min_relevance_score`: `0.42`
- `min_citations`: `10`
- `require_doi`: `true`

This defines "high-impact mainstay" operationally for this repo: the paper must have enough
citation support to clear the impact threshold, have DOI-backed metadata, and directly match
the IL-10/LPS/PBMC topic configuration. The cap is applied per bucket after sorting by total
score.

## Output

The manifest includes source provenance, raw-cache hashes, DOI, PMID, year, citation count,
citation velocity, venue, source IDs, matched entities, matched topic terms, scores, and a
short derived relevance note. The tool proposes candidates only; Mike approves the short list
that CORPUS-001 turns into the final corpus source manifest.
