# arXiv submission package (v2, final 2026-09-15; readability/rhythm revision, terminology pass, reference additions)

Main document: `main.tex` (pdflatex + natbib; bibliography precompiled in `main.bbl`).
The Supplementary Information is appended after the references (sections S1–S11 (S1 is a glossary of terms),
Figure S1, captioned Tables S1–S3 and 20 inline tabulars), so a single compilation produces main text + SI (38 pages).

Contents to upload (arxiv_v2_upload.zip: these files at the zip root, no PDF):
- main.tex, main.bbl (required; arXiv does not run BibTeX), refs.bib (optional)
- figs/ : fig1_framework … fig7_calibration, figS1_perk_identified (PDF)
- tables/ : 22 table fragments included by \input

Metadata:
- Title: Message capacity and claim wording set the transition points of collective truth-finding in language-model networks
- Abstract: abstract_arxiv.txt (1,856 characters, 300 words, ASCII with TeX math; within the 1,920 limit)
- Comments: 22 pages main text + 16 pages supplementary information (single 38-page PDF), 7 figures + 1 SI figure. Submitted to IEEE Access
- Primary category: physics.soc-ph (Physics and Society); cross-list: cs.MA (Multiagent Systems), cs.CL (Computation and Language), nlin.AO (Adaptation and Self-Organizing Systems)
- License: choose at submission (arXiv non-exclusive license is sufficient for a journal submission)

Compile check: pdflatex main; bibtex main; pdflatex main; pdflatex main → 38 pages, 0 errors.

Status (2026-09-15): this text is identical to the version submitted to IEEE Access on 2026-09-15 (the journal version
differs only in layout: two-column IEEE template, Methods as Appendix A, SI split into Appendices B–D plus a
supplementary PDF, and a conflict-of-interest sentence in the Acknowledgment). If a version is already on arXiv,
upload this package as a replacement (new version); otherwise as a new submission.
