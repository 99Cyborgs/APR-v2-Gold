# External Paper Fixtures

These files are synthetic normalized manuscript packages used for the external-paper calibration lane.

## Provenance and Legal Position

- They are not copied full-text papers.
- They are legally safer derived fixtures authored for deterministic benchmark use.
- They are intended to approximate common referee, committee, and board pressure patterns rather than reproduce copyrighted publications.
- This repository does not require live paper retrieval at runtime or in tests.

## Current Fixture Classes

- strong clear paper
- polished but overclaimed paper
- sound narrow specialist paper
- null or replication-like paper
- methodology-weak paper
- defense-vulnerable paper
- holdout narrow specialist paper
- holdout overclaimed paper

## Rules for New Fixtures

- Prefer synthetic normalized packages, public-domain text, or clearly licensed author-provided material.
- Record provenance and licensing assumptions in this file or an adjacent note when adding new cases.
- Keep the text minimal and structured enough for deterministic offline evaluation.
- Avoid hidden dependence on proprietary PDFs, OCR pipelines, or runtime internet access.
