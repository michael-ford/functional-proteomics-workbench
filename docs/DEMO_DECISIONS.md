# Demo Decisions

Interview decisions captured on 2026-06-23. This file records product and demo-scope
decisions that implementation agents should treat as current unless a later issue comment or
PR explicitly changes them.

## Product Story

- Primary persona: **Nomic internal scientist**.
- Secondary audience: field application scientist as an implied beneficiary, not the main
  walkthrough voice.
- Demo shape: **hybrid**. The biological analysis is the story; traces, evals, and the
  multi-agent repo harness are the proof that the system is reliable.
- Top demo signals:
  1. agent-native MCP/web shared project state,
  2. multi-agent engineering harness,
  3. domain understanding.
- Walkthrough narrative: a scientist asks an agent to create and run an analysis project.
- Signature interaction: agent creates project state, returns dashboard/selection URL, and
  resumes work after the public dataset subset is selected in the app.

## Data Flow

- v0.1 uses a **selected_public** curated subset of the public Perturb-PBMC data inside the
  app.
- Do not prioritize a generic upload workflow for v0.1.
- Candidate hero comparisons should favor what a Nomic internal scientist would plausibly
  care about, with visually clear results when the biology is credible.

## Biological Claim Level

- Keep claims conservative.
- Preferred report language: donor-consistent protein changes plus source-grounded evidence.
- Do not claim a biological mechanism unless the data, analysis method, and retrieved sources
  directly support it.

## Analysis Direction

- v0.1 should include p-values if STAT-001 identifies a defensible test for the selected
  public Perturb-PBMC subset.
- Starting analysis shape:
  - compare perturbagen versus matched no-cytokine control,
  - compute per-protein effect size,
  - summarize donor consistency,
  - compute/report p-values where assumptions are documented,
  - rank proteins,
  - generate a compact plot/report.
- The AnalysisPlan artifact must record method choice, donor handling, p-value method,
  multiple-testing status, and limitations.

## Corpus Direction

- Runtime retrieval should use a deterministic indexed corpus, not live web search.
- Source scope: Nomic/Perturb-PBMC materials plus a small curated set of public biology
  references.
- Source gathering can be agent-assisted. The final corpus manifest must be explicit and
  reproducible.
- Use the planned modified Docling pipeline for paper extraction. Main text is sufficient for
  v0.1 unless figure/caption material is clearly useful for the selected hero workflow.
- Required topic buckets:
  - Perturb-PBMC dataset provenance,
  - nELISA assay context,
  - PBMC perturbation design,
  - selected stimulation biology,
  - selected perturbagen biology,
  - selected top-protein biology,
  - donor/stimulation interpretation,
  - analysis limitations.

## Eval Direction

- v0.1 evals primarily prove **agent workflow correctness**, not biological correctness.
- Hero workflow assertions should cover: create project, select curated public dataset,
  validate dataset, define/run approved comparison, retrieve evidence, export report, and
  record inspectable traces.
- CI uses deterministic fixtures/mocks by default.
- Real model evals run when changes touch agent behavior: code, tools, prompts, model adapter,
  retrieval policy, report generation, or related eval cases.
- `eval-smoke` becomes required only after the full hero path works end-to-end on the seeded
  demo project.
- Initial failure classes:
  - unsupported tool call,
  - missing trace,
  - unsupported statistical claim,
  - source-derived claim without citation,
  - wrong or missing artifact,
  - report claims more than the data supports.

## DATA-001 Candidate Comparisons

Research agent output is recorded on GitHub issue #12:
https://github.com/michael-ford/functional-proteomics-workbench/issues/12#issuecomment-4783622980

These were the reviewed candidates before final selection. The selected comparison is recorded
below.

### Candidate 1: IL-10 under LPS

- Stimulation: `LPS`, `stimulus_concentration = 2000 ng/mL`.
- Perturbagen: `IL-10`, `cytokine_concentration = 50 ng/mL`.
- Control: matched no-cytokine controls for same donor, stimulus, and concentration.
- Donors: all 6 donors, with 1 IL-10 row per donor and 18 matched controls per donor in the
  quick screen.
- Signal summary: broad donor-consistent decreases in TNF alpha, IL-1 beta, IL-1 alpha,
  CCL1, IL-12 p40, IFN gamma, CCL22, CCL24, G-CSF, IL-6, and GM-CSF.
- Strength: clearest visual demo; easy conservative interpretation as IL-10-associated
  dampening of an LPS inflammatory secretome response.
- Caveat: may be almost too obvious; final report should avoid mechanism claims.

### Candidate 2: IL-15 under PolyIC

- Stimulation: `PolyIC`, `stimulus_concentration = 400 ng/mL`.
- Perturbagen: `IL-15`, `cytokine_concentration = 50 ng/mL`.
- Control: matched no-cytokine controls for same donor, stimulus, and concentration.
- Donors: all 6 donors, with 1 IL-15 row per donor and 17-18 matched controls per donor in
  the quick screen.
- Signal summary: IFN gamma dominates, with supporting increases in CCL8, CCL5, CXCL9,
  IL-22, CXCL10, TNF alpha, CCL7, IL-1 beta, IL-12 p40, and IL-1 alpha.
- Strength: good cytokine-induction module with recognizable T/NK/interferon-adjacent
  biology.
- Caveat: secondary effects are smaller than Candidate 1, so the plot needs donor points and
  careful ranking to read well.

### Candidate 3: IFN beta under PolyIC

- Stimulation: `PolyIC`, `stimulus_concentration = 400 ng/mL`.
- Perturbagen: `IFN beta`, `cytokine_concentration = 50 ng/mL`.
- Control: matched no-cytokine controls for same donor, stimulus, and concentration.
- Donors: all 6 donors, with 1 IFN beta row per donor and 17-18 matched controls per donor in
  the quick screen.
- Signal summary: bidirectional fingerprint, with increases in CCL8, CXCL10, IFN gamma,
  CCL7, and IL-1 RA RN, and decreases in CCL24, CCL1, CXCL5, IL-12 p40, CCL22, CXCL1,
  TNF alpha, MMP-1, G-CSF, and IL-1 beta.
- Strength: best multiplex-fingerprint narrative for a Nomic internal scientist; showcases
  why ranked tables, evidence, and traces matter.
- Caveat: biology is more nuanced than Candidate 1 and must stay descriptive.

## DATA-001 Selected Hero Comparison (DECIDED 2026-06-23)

**SELECTED: Candidate 1 — IL-10 vs matched no-cytokine control under LPS 2000 ng/mL.**

Chosen for the strongest visual clarity and fastest demo comprehension: broad,
donor-consistent decreases across an LPS inflammatory secretome (TNF alpha, IL-1 beta,
IL-1 alpha, CCL1, IL-12 p40, IFN gamma, CCL22, CCL24, G-CSF, IL-6, GM-CSF). The report must
stay conservative — describe IL-10-associated dampening of the LPS inflammatory response, and
avoid any mechanistic claim.

This selection is now the input for:
- SPEC-006 demo dataset fixture contract (issue #15),
- IMPL-009 bounded analysis package (issue #24),
- CORPUS-001 source list — selected-stimulation (LPS), selected-perturbagen (IL-10), and
  selected-top-protein biology buckets resolve against this comparison (issue #14, #25).

Runner-up order retained for reference: (2) IFN beta under PolyIC, (3) IL-15 under PolyIC.

Use the public H5AD as the source for SPEC-006 fixture design and extract a long-format direct
subset with explicit metadata columns plus 20-30 selected proteins. Preserve provenance back
to the public source and citation.
