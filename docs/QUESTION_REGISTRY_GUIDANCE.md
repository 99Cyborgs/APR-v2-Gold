# Question Registry Guidance Seed

This note records the public guidance used to seed the offline question registry and its context typing. The runtime registry in `contracts/active/question_registry.yaml` remains generic, deterministic, and self-contained; APR does not fetch these sources at runtime.

## Seed Sources

- Sacramento State, Dissertation Handbook:
  - [https://www.csus.edu/college/education/doctorate-educational-leadership/_internal/_documents/dissertation-handbook.pdf](https://www.csus.edu/college/education/doctorate-educational-leadership/_internal/_documents/dissertation-handbook.pdf)
  - Informed dissertation-defense question families around literature positioning, methodological rationale, statistics, sampling, limitations, and defendable contribution.

- University of Arizona, Neuroscience Graduate Interdisciplinary Program Student Handbook:
  - [https://nsgidp.arizona.edu/sites/default/files/2021-11/Student%20Handbook.pdf](https://nsgidp.arizona.edu/sites/default/files/2021-11/Student%20Handbook.pdf)
  - Informed dissertation-proposal and oral-exam categories around hypothesis framing, proposal defense, strengths and weaknesses, broader questions, alternatives, and pitfalls.

- University of Maryland, MEES Doctoral Requirements Foundations:
  - [https://www.mees.umd.edu/doctoral-requirements-foundations](https://www.mees.umd.edu/doctoral-requirements-foundations)
  - Informed committee-exam structure and the expectation that a formal dissertation defense includes direct committee questioning tied to the defended work.

- University of Maryland, Department of English doctoral milestone guidance:
  - [https://english.umd.edu/academic-programs/graduate/doctoral/doctoral-degree-requirements](https://english.umd.edu/academic-programs/graduate/doctoral/doctoral-degree-requirements)
  - Informed research-review style expectations around defining the research question, relating it to existing scholarship, and defending project framing before broader departmental scrutiny.

- Committee on Publication Ethics, Ethical Guidelines for Peer Reviewers:
  - [https://publicationethics.org/sites/default/files/ethical-guidelines-peer-reviewers-cope.pdf](https://publicationethics.org/sites/default/files/ethical-guidelines-peer-reviewers-cope.pdf)
  - Informed journal-referee categories around originality, literature awareness, expertise boundaries, unsupported conclusions, missing citations, ethical concerns, and confidentiality.

- U.S. HHS Office for Human Research Protections, §46.111 criteria for IRB approval:
  - [https://www.hhs.gov/sites/default/files/unlocking-mysteries-section-46.111-criteria-irb-approval-research.pdf](https://www.hhs.gov/sites/default/files/unlocking-mysteries-section-46.111-criteria-irb-approval-research.pdf)
  - Informed ethics/compliance-board categories around risk minimization, benefit-risk proportionality, equitable selection, privacy/confidentiality, and additional safeguards.

## Use Boundary

- These sources informed the seed question families and context boundaries.
- They did not introduce runtime network dependencies.
- They do not supersede APR's canonical audit semantics.
- Future registry enrichment should keep citations local in docs and keep the executable registry generic enough to remain offline and deterministic.
