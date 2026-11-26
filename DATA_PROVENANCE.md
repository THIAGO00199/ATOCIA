# Data provenance and redistribution policy

ATOCIA combines locally collected hardware telemetry with analyses of third-party research datasets.

## Third-party datasets

- **PM100 v1** — DOI: [10.5281/zenodo.8129258](https://doi.org/10.5281/zenodo.8129258). The source record was checked for CC BY 4.0. Attribution and the source DOI must accompany reuse.
- **AcmeTrace** — [official project repository](https://github.com/InternLM/AcmeTrace) and [Hugging Face dataset](https://huggingface.co/datasets/HuggingAGree/AcmeTrace). The upstream repository provides a CC BY 4.0 license. Consult the upstream source for the dataset version and attribution before reuse.
- Other datasets discussed in the research notes may have different or unresolved terms. In particular, do not assume that a metadata/API license field overrides conflicting terms in an associated paper or repository.

This repository does not redistribute complete third-party datasets, raw third-party trace files, or source metadata dumps. Obtain datasets from their official sources and review their current terms.

## Local measurements

Raw CSV captures, collector logs, and user-mode demonstration files from local hardware experiments are intentionally excluded from this public repository. Reports may summarize selected observations; those summaries are not a substitute for the underlying raw data and should not be treated as independently reproducible without access to the original captures.

## Scope

The scripts and documentation here are provided for research and reproducibility. Results are exploratory and do not establish production readiness, commercial suitability, or a validated connection between TDT and ATOCIA.
