# TODO.md — Active work

**Version:** 0.1.1
**Updated:** 2026-09-18
**Reason:** Path A repository hygiene, CI hardening, PEP 621 metadata, and contract test expansion
**Purpose:** Track only work that remains open.

## STATUS

| Category | Status | Evidence / next gate |
|---|---|---|
| Neutral carrier | DONE | Python API, JSON CLI, integrity and conservative mutation tests are green (28/28 passing). |
| Packaging and security | DONE | Bounded inputs, pinned private CI, PEP 621 classifiers, llms.txt, and clean package inspection evidenced. |
| Application adapter | BLOCKED | Requires a current open-ocean K9 contract pin and later BACH equivalence work. |
| Public release | USER | MIT is selected; explicit visibility approval is still required. |

- [ ] Run old/new anonymized equivalence after the BACH judging hold.
- [ ] Add the later thin application adapter without adding application tables to this package.
- [x] Record the owner's MIT licence decision in the package and repository metadata.
- [x] Add AI discoverability contract (`llms.txt`) and PEP 621 classifiers.
- [ ] Obtain a separate public-release approval before publication.
- [ ] Register and bundle only after the open-ocean K9 carrier gate is green.
- [ ] Define an optional, versioned `continuity.v1` payload profile for
  application-provided data: settled decisions, open branches, evidence/source
  anchors, contradictions, drift risks and next action. The carrier validates
  the envelope but does not infer or collect any field.
- [ ] Add deterministic export/replay fixtures for that profile, including
  unknown fields, stale source versions, hash mismatch and partial evidence.
- [ ] Document compaction semantics: structured decisions, tool results, errors
  and open actions may be carried; restoration and application mutation remain
  outside this package.
- [ ] Add optional payload-level sensitivity/retention metadata without adding a
  background pruner, network sync or application-specific policy engine.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
