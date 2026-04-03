# Spec Implementation Matrix

This matrix marks what APR v2 Gold actually implements and what the benchmark harness currently exercises.

## Implemented And Benchmarked

| Surface | Status | Evidence |
| --- | --- | --- |
| Central-claim recovery | Implemented and benchmarked | `parsing.central_claim` is asserted in every active goldset case. |
| Article type, claim type, domain module, outlet profile classification | Implemented and benchmarked | Exact expectations exist in `benchmarks/goldset/manifest.yaml`. |
| Reviewability gate | Implemented and benchmarked | Core and stress cases assert `reviewability.status`. |
| Scientific-record gate | Implemented and benchmarked | Core and stress cases assert `scientific_record.status`. |
| Venue routing after scientific-record gating | Implemented and benchmarked | `venue.routing_state` is asserted across viable, blocked, and retarget cases. |
| Human-escalation requirement | Implemented and benchmarked | `decision.human_escalation_required` is asserted in every active case. |
| Integrity escalation | Implemented and benchmarked | `integrity_escalation` is a hard core case. |
| Advisory-pack execution visibility | Implemented and benchmarked | `theory_pack_case` asserts pack result presence without allowing pack semantic override. |

## Implemented But Not Directly Benchmarked

| Surface | Status | Notes |
| --- | --- | --- |
| Transparency sub-assessment object | Implemented but not directly benchmarked | It affects scientific-record outcomes, but the goldset does not currently assert standalone transparency fields. |
| Rehabilitation plan ranking | Implemented but not directly benchmarked | The plan is emitted by runtime, but benchmark cases do not yet freeze ranking details. |
| Markdown rendering details | Implemented but not directly benchmarked by goldset | Covered only by smoke tests, not the goldset harness. |

## Specified Elsewhere But Not Implemented Here

| Surface | Status | Notes |
| --- | --- | --- |
| Prompt-driven contract execution | Specified elsewhere but not implemented here | `contracts/active/system_prompt.md` and `user_prompt_template.md` are contract artifacts, not active runtime drivers in this local deterministic engine. |
| Real public holdout benchmark set | Specified elsewhere but not implemented here | The `holdout` stratum exists, but there are no active untuned public holdout fixtures in the repo yet. |

## Intentionally Out Of Scope For v2

| Surface | Status | Notes |
| --- | --- | --- |
| Journal submission workflows | Out of scope | Declared outside core in `docs/SYSTEM_BOUNDARY.md`. |
| Reviewer assignment or editorial queueing | Out of scope | APR v2 is not a reviewer-management system. |
| Autonomous misconduct adjudication | Out of scope | Integrity signals can escalate; they do not finalize misconduct findings. |
| Advisory-pack redefinition of core semantics | Out of scope | Packs remain advisory-only by doctrine and by benchmark contract. |
