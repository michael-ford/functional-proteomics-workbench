# Corpus

This document records the CORPUS-001 decision for the v0.1 evidence corpus. Runtime retrieval is
deterministic over an indexed, approved corpus. The app and MCP tools must not perform live web
search during the demo.

## Scope

The v0.1 corpus supports source-grounded report claims for the selected hero comparison:
IL-10 vs matched no-cytokine control under LPS 2000 ng/mL in the public Perturb-PBMC fixture.

The corpus is intentionally small:

- Nomic/Perturb-PBMC provenance and assay context.
- Public biology references for IL-10, LPS/PBMC stimulation, and selected inflammatory proteins.
- No private sources.
- No Sci-Hub, SciDB, or other unapproved full-text routes.
- No broad live literature search at runtime.

Research-time candidate discovery is documented in `docs/CORPUS_DISCOVERY.md` and configured by
`corpus_discovery/il10_lps_config.json`. The approved manifest below is the input for IMPL-010.

## Approved source manifest

Implementers should encode these sources into a reproducible machine-readable manifest before
building the index, preserving the IDs below.

| source_id | type | topic buckets | title | locator |
|---|---|---|---|---|
| `src_nomic_perturb_pbmc` | webpage | dataset provenance, PBMC perturbation design | Nomic Perturb-PBMC page | https://info.nomic.bio/perturb-pbmc |
| `src_nelisa_pbmc_repo` | github | dataset provenance, fixture provenance | nELISA-PBMC public repo | https://github.com/nplexbio/nELISA-PBMC |
| `src_dagher_2025_nelisa` | paper | nELISA assay context, dataset provenance | nELISA: a high-throughput, high-plex platform enables quantitative profiling of the inflammatory secretome | DOI `10.1038/s41592-025-02861-6` |
| `src_dandrea_1993_il10` | paper | selected perturbagen biology | Interleukin 10 inhibits human lymphocyte interferon gamma-production by suppressing natural killer cell stimulatory factor/IL-12 synthesis in accessory cells | DOI `10.1084/jem.178.3.1041` |
| `src_wang_1995_il10_nfkb` | paper | selected perturbagen biology | Interleukin (IL)-10 Inhibits Nuclear Factor kB (NFkB) Activation in Human Monocytes | DOI `10.1074/jbc.270.16.9558` |
| `src_degroote_1992_pbmc` | paper | PBMC perturbation design, LPS cytokine response | Direct stimulation of cytokines in whole blood. I. Comparison with isolated PBMC stimulation | DOI `10.1016/1043-4666(92)90062-v` |
| `src_eggesbo_1994_lps_pbmc` | paper | PBMC perturbation design, LPS cytokine response | LPS-induced release of IL-1 beta, IL-6, IL-8, TNF-alpha and sCD14 in whole blood and PBMC | DOI `10.1016/1043-4666(94)90080-9` |

The last five paper entries are the DOI-backed candidates from
`corpus_discovery/il10_lps_candidate_manifest.json`. The first two provenance sources are added
explicitly because runtime reports need to cite the public dataset page and source repository even
though they are not paper-search candidates.

## Inclusion and exclusion rules

Include a source only if it satisfies at least one approved topic bucket and has stable provenance:

- dataset or fixture provenance for Perturb-PBMC/nELISA-PBMC;
- nELISA assay context;
- IL-10 perturbagen biology relevant to human immune cells, monocytes, PBMCs, LPS, or cytokine
  production;
- LPS-stimulated PBMC or whole-blood cytokine response context;
- selected top-protein biology when directly needed for a report claim.

Exclude:

- sources without stable URL, DOI, or repository locator;
- private, paywalled-only, or license-unclear full text when no compliant metadata/snippet route is
  available;
- papers discovered only through Sci-Hub/SciDB-like routes;
- broad review papers that do not directly support a v0.1 report claim;
- sources that encourage mechanistic claims beyond the fixture and retrieved evidence.

## Source metadata

Each source should map cleanly onto `EvidenceSource` plus ingestion metadata. Minimum fields:

- `source_id`
- `source_type`
- `title`
- `url`
- `doi`
- `license_note`
- `topic_buckets`
- `approved_for_claims`
- `retrieval_priority`
- `source_locator`
- `access_route`
- `ingested_at`
- `content_sha256`

For papers, retain DOI, year, authors, venue, candidate rank, citation count if available, and
the research-time candidate score from `corpus_discovery/il10_lps_candidate_manifest.json`.

## Chunking policy

Chunking must be deterministic for the same source bytes.

- Main text chunks target 800 to 1,200 words with up to 150 words of overlap.
- Preserve section headings in `EvidenceChunk.section`.
- Keep title, abstract, and figure/table captions as separate chunks when available.
- Include references only if a report explicitly needs citation-chain context; otherwise skip.
- For GitHub/provenance files, chunk by logical document section or JSON object path.
- Each chunk must carry a citation object with URL or DOI, paper title, authors, and year when
  available.

Figure and caption extraction is optional in v0.1. Include captions only when the caption text
directly supports a source-grounded report claim. Do not require image extraction for IMPL-010.

## Entity tagging

Use deterministic dictionary tagging in v0.1. Do not add an LLM extraction dependency to corpus
builds.

The initial dictionary must include:

- comparison entities: `IL-10`, `interleukin 10`, `LPS`, `lipopolysaccharide`, `PBMC`,
  `peripheral blood mononuclear cells`, `nELISA`;
- top proteins: `TNF alpha`, `TNF-alpha`, `IL-1 beta`, `IL-1 alpha`, `IL-6`, `IL-12 p40`,
  `IFN gamma`, `CCL1`, `CCL22`, `CCL24`, `G-CSF`, `GM-CSF`;
- assay/context tags: `secretome`, `cytokine`, `monocyte`, `macrophage`, `whole blood`,
  `donor`, `perturbation`.

Normalize aliases in metadata, but preserve original text in chunks.

## Retrieval policy

`search_corpus` must query only the indexed corpus.

Ranking should combine lexical match, entity overlap, topic-bucket match, and source priority.
Embedding search can be added if it is deterministic in tests and optional in CI, but the v0.1
smoke test must pass without paid external model calls.

Required output behavior:

- Return scored `EvidenceChunk` records with source IDs and citation metadata.
- Prefer chunks that match both the query terms and the selected comparison entities.
- Never invent citations.
- Fail closed with `corpus_unindexed` if the corpus has not been built.

## Retrieval eval

IMPL-010 should add a deterministic smoke fixture with at least these queries:

| query | expected evidence |
|---|---|
| `What public dataset and assay does this demo use?` | `src_nomic_perturb_pbmc`, `src_nelisa_pbmc_repo`, or `src_dagher_2025_nelisa` |
| `What evidence supports IL-10 dampening cytokine production in LPS or human immune-cell contexts?` | `src_dandrea_1993_il10` or `src_wang_1995_il10_nfkb` |
| `What context supports LPS-stimulated PBMC cytokine response interpretation?` | `src_degroote_1992_pbmc` or `src_eggesbo_1994_lps_pbmc` |

The eval should assert source IDs, citation fields, and at least one matched entity. It should not
assert fragile exact text snippets unless the fixture content is frozen.
