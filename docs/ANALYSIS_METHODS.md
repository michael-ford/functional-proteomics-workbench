# Analysis Methods

This document records the STAT-001 decision for the v0.1 Perturb-PBMC demo. It is intentionally
narrow: the supported path is designed to be auditable, deterministic, and conservative for the
selected IL-10/LPS fixture, not to be the final statistical ceiling for the project.

## Selected comparison

The v0.1 analysis is fixed to the SPEC-006 fixture:

- group A: `perturbagen = "IL-10"`
- group B: `perturbagen = "control"` matched no-cytokine controls
- stimulation context: `LPS`, `stimulus_concentration_ng_ml = 2000.0`
- treatment concentration: `cytokine_concentration_ng_ml = 50.0`
- paired unit: donor
- value column: `response_value`
- value type: `normalized_response`

`response_value` is carried verbatim from the public H5AD source. v0.1 does not renormalize,
impute, remove outliers, synthesize rows, or convert values to pg/mL or fold change.

## Method menu

### `donor_aware_paired_difference` - default

This is the default and executable v0.1 method.

For each protein:

1. Select all IL-10 and control rows under the fixed LPS context.
2. Treat donor as the biological replicate unit.
3. Collapse matched control rows within each donor/protein by median.
4. Compute donor-level paired differences:
   `IL-10 response_value - median matched control response_value`.
5. Report the mean paired difference as `effect_size`.
6. Rank proteins by absolute effect size, with deterministic protein-name tie breaking.
7. Compute donor consistency and exploratory p/q values.

The median control collapse is part of the approved method. Matched controls must not be treated
as independent biological replicates.

### `effect_size_summary` - fallback interpretation

This is the same donor-level paired-difference summary without inferential emphasis. Use this
interpretation when UI/report copy needs to de-emphasize p/q values or when later fixtures do not
meet the exploratory p-value assumptions.

For the v0.1 IL-10/LPS fixture, the implementation may produce p/q values and still present the
report primarily around effect size and donor consistency.

### `donor_consistency_score` - support metric

This is a displayed support metric, not a standalone statistical test.

For each protein, determine the consensus direction from the sign of the mean paired difference.
Then compute:

`donor_consistency = agreeing_donors / nonzero_donors`

Display language should use counts where possible, for example `6/6 down` or `5/6 down`.

## Exploratory p/q values

P-values are allowed only as exploratory donor-level paired p-values.

- Test: exact paired sign-flip test over donor-level differences.
- Enumeration: all sign assignments across the donor differences. For the v0.1 fixture with
  six donors, this is `2^6 = 64` assignments.
- Statistic: absolute mean paired difference.
- Two-sided p-value: fraction of sign flips where
  `abs(mean(delta_flipped)) >= abs(mean(delta_observed))`.
- Multiple testing: Benjamini-Hochberg q-values across the frozen tested protein panel.

Ranking and report language must prioritize effect size and donor consistency. The UI/report must
label p/q values as exploratory and must not show hard significance badges in v0.1.

## AnalysisPlan requirements

Every plan/result path for this comparison must record:

- `method_id`
- comparison groups
- stimulation context
- `paired_by = "donor"`
- included donor IDs and expected donor count
- frozen protein panel
- value column and value type
- normalization note
- control replicate collapse rule
- control replicate counts where available
- p-value method
- multiple-testing method
- assumptions
- limitations
- unsupported assumptions

## Limitations

- The donor count is small, so p/q values have limited inferential power.
- The method summarizes donor-matched response differences and does not establish mechanism.
- The fixture is a direct public-data subset; it is appropriate for a transparent demo, not a
  generalizable statistical claim about all PBMC systems.
- Unpaired row-level tests are out of scope because they would treat repeated controls as
  independent biological replicates.
- Wilcoxon signed-rank, limma, mixed models, and richer blocked models are deferred. They are
  reasonable future additions, but they are intentionally outside the v0.1 implementation.

## References

- Dagher et al., *nELISA: a high-throughput, high-plex platform enables quantitative profiling of
  the inflammatory secretome.* DOI `10.1038/s41592-025-02861-6`.
- Nomic Perturb-PBMC page: https://info.nomic.bio/perturb-pbmc
- nELISA-PBMC public repo: https://github.com/nplexbio/nELISA-PBMC
- Benjamini and Hochberg, *Controlling the False Discovery Rate.* DOI
  `10.1111/j.2517-6161.1995.tb02031.x`.
- Nichols and Holmes, *Nonparametric permutation tests for functional neuroimaging: A primer with
  examples.* DOI `10.1002/hbm.1058`.
- Ritchie et al., *limma powers differential expression analyses for RNA-sequencing and microarray
  studies.* DOI `10.1093/nar/gkv007`.
- Hoffman and Roussos, *dream: powerful differential expression analysis for repeated measures
  designs.* DOI `10.1093/bioinformatics/btaa687`.
