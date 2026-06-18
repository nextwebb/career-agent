# Issue 72 Quality Gate Evidence

These PDFs are synthetic, non-PII review artifacts for issue 72. They do not represent a real
person, employer, LinkedIn profile, portfolio, or job post.

Source fixtures:

- `tests/fixtures/non_pii/profile.synthetic.json`
- `tests/fixtures/non_pii/roles/synthetic_quality_gate_pass.json`

Generation method:

- `before/`: generated with `origin/main`
- `after/`: generated with `codex/issue-72-cv-quality-gates`

## Evidence Summary

| File | Pages | Extracted chars | Placeholder text | Notable signal |
|---|---:|---:|---|---|
| `before/synthetic_quality_gate_pass_CV.pdf` | 2 | 1597 | no | Extracted text includes raw bullet key `default`; role override bullet is absent. |
| `before/synthetic_quality_gate_pass_CoverLetter.pdf` | 1 | 1218 | no | Baseline cover letter generated successfully. |
| `after/synthetic_quality_gate_pass_CV.pdf` | 1 | 2121 | no | Extracted text includes the role override bullet and no raw bullet keys. |
| `after/synthetic_quality_gate_pass_CoverLetter.pdf` | 1 | 1218 | no | Cover letter remains stable while gates validate role context. |

## SHA-256

```text
478973ac7b4da69ac2aa8e1d2dfd009e0bcb375d8ce77c4c4b643d79c2a04e38  after/synthetic_quality_gate_pass_CV.pdf
8af8c6cd5bd1067e5e9e277c35a8e2cc806d1973202eb9945d8401cf0612bb92  after/synthetic_quality_gate_pass_CoverLetter.pdf
0b3d137fe498e1cf42901f31ffa34820ae75d5b259da4e91b5a422d26f6f08b4  before/synthetic_quality_gate_pass_CV.pdf
92fe4a142924319607d6123bef0226df36e5a9b68b154b9a4ab74226c824b6cb  before/synthetic_quality_gate_pass_CoverLetter.pdf
```
