# Final Walkthrough Script

## Story

Persona: Nomic internal scientist.

Question: Compare IL-10 against matched no-cytokine control under LPS 2000 ng/mL in the
approved public Perturb-PBMC subset.

Interpretation stance: conservative donor-consistent readout, not a mechanistic claim.

## Recording Beats

1. Open the Railway web app on the project dashboard.
2. Show the seeded project state: public Perturb-PBMC subset, six matched donors, 21 proteins,
   and validated dataset status.
3. In web chat, ask for project status. Point out that the chat turn calls the shared
   `get_project_status` tool and records a web-chat trace.
4. Show the agent handoff panel: the selected comparison is IL-10 vs matched control under LPS,
   paired by donor.
5. Show the ranked protein table and effect plot. State that effect size and donor consistency
   are primary, while p/q values are exploratory.
6. Open the report page. Highlight the claim types: data-derived, source-derived, and
   interpretive. State that all biological context comes from the deterministic approved corpus.
7. Open the trace page. Show web and eval traces, trace IDs, input/output replay, and absence of
   secret values.
8. Open the eval page. Show the deterministic smoke score and retrieval/evidence checks.
9. End on the dashboard with the signature message: the same shared tool registry backs web
   chat, MCP, eval replay, and the demo artifacts.

## Desktop And Mobile Screenshot Checklist

- Desktop dashboard with chat trace visible.
- Desktop report page with claim list and citations visible.
- Desktop trace page with trace log and details visible.
- Mobile dashboard showing responsive project metrics.
- Mobile report page showing readable claims without overlap.

## Reset Before Recording

```bash
make demo-reset
make demo-replay
make eval-smoke
APP_BASE_URL=https://your-api-service.up.railway.app make deploy-smoke
```
