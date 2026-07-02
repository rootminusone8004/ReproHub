# 🔬 ReproHub

### Research Reproducibility Verification Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://reprohub.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![SciPy](https://img.shields.io/badge/SciPy-Statistical%20Engine-8CAAE6?style=flat&logo=scipy&logoColor=white)](https://scipy.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-22c55e?style=flat)]()

---

> **The reproducibility crisis is real.** Only ~40% of psychology studies replicate successfully. Most researchers never check the numbers. ReproHub changes that — upload a paper and its dataset, and get a full reproducibility verdict in seconds.

---

## 📖 What is ReproHub?

**ReproHub** is an automated research reproducibility verification platform. It takes a research paper (PDF) and its underlying dataset (CSV), re-runs every statistical test from scratch, and tells you exactly how well the reported results hold up against the raw data.

No manual checking. No guesswork. Just evidence.

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 📄 | **Smart PDF Parsing** | Upload any research paper — ReproHub extracts every statistical claim automatically |
| 🤖 | **Regex-Based Extraction** | Detects APA-style results: t-tests, ANOVA, correlations, regressions, and more |
| 🔬 | **Real Statistical Re-runs** | Actually executes the tests on your data — no simulation, no shortcuts |
| 📊 | **Composite Scoring** | Multi-factor verdict weighing p-values, effect sizes, and test statistics together |
| 🗺️ | **Column Mapping UI** | Fuzzy-matches paper prose to dataset columns; fully editable before verification |
| 💡 | **Remediation Guidance** | Pinpoints the weakest component when a claim fails — not just "failed" |
| 📄 | **PDF Report Export** | Download a professional reproducibility report for sharing or publishing |
| 🔒 | **No API Keys Required** | Fully open-source, runs locally, no external services needed |

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Junaid-Ahmed-Rupok/ReproHub.git
cd ReproHub

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app/main.py
```

👉 **Live Demo:** [reprohub.streamlit.app](https://reproapp-8jb7vbhnqyltxq23bsr8xn.streamlit.app/)

---

## 🔬 Supported Statistical Tests

### Parametric Tests
| Test | Effect Size Reported |
|------|----------------------|
| Independent t-test | Cohen's d |
| Paired t-test | Cohen's d |
| One-way ANOVA | Eta-squared (η²) |
| Pearson Correlation | r |
| Linear Regression | R², Adj-R², per-coefficient p-values |
| Logistic Regression | McFadden pseudo-R², LR chi-square |

### Non-Parametric Tests
| Test | Effect Size Reported |
|------|----------------------|
| Mann-Whitney U | Rank-biserial correlation |
| Kruskal-Wallis H | Eta-squared approximation |
| Wilcoxon Signed-Rank | Rank-biserial correlation |
| Spearman Correlation | ρ (rho) |
| Chi-square | Cramér's V |

---

## 📊 How Reproducibility is Scored

ReproHub uses a **composite scoring model** — not just p-value comparison.

```
Composite Score = (p-value agreement × 50%)
               + (effect size agreement × 30%)
               + (test statistic agreement × 20%)
```

Each component is scored 0–1 using exponential decay, so small differences are penalised gradually and large differences are penalised heavily.

| Score | Status | Meaning |
|-------|--------|---------|
| ≥ 0.80 | ✅ **Reproduced** | Results align across all dimensions |
| ≥ 0.55 | ⚠️ **Marginal** | Close but meaningful discrepancies exist |
| < 0.55 | ❌ **Not Reproduced** | Results do not hold up against the data |
| — | ❓ **Could Not Verify** | Missing columns, unsupported test, or insufficient data |

> **Why composite scoring?** A claim with matching p-values but wildly different effect sizes (e.g. Cohen's d = 0.2 vs 0.8) should not be called "reproduced." The old p-value-only approach missed this. ReproHub doesn't.

---

## 🗺️ How It Works

```
 ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
 │  Upload PDF │────▶│ Extract      │────▶│ Map Columns     │────▶│ Re-run Tests │
 │  + CSV Data │     │ Claims       │     │ (Fuzzy Match +  │     │ (SciPy /     │
 └─────────────┘     │ (Regex/APA)  │     │  Manual Review) │     │  statsmodels)│
                     └──────────────┘     └─────────────────┘     └──────┬───────┘
                                                                          │
                     ┌──────────────┐     ┌──────────────────┐           │
                     │ Export PDF   │◀────│ Composite Score  │◀──────────┘
                     │ Report       │     │ + Explanation    │
                     └──────────────┘     └──────────────────┘
```

**Step 1 — Upload:** Provide a PDF paper and its CSV dataset.

**Step 2 — Extract:** ReproHub scans for APA-style statistical notation and pulls out every claim automatically.

**Step 3 — Review:** Check the auto-mapped column assignments, fix anything the fuzzy matcher got wrong, and confirm each claim.

**Step 4 — Verify:** ReproHub re-runs the actual statistical tests and scores each claim using composite scoring.

**Step 5 — Report:** Download a detailed reproducibility report with per-claim breakdowns, scores, and remediation advice.

---

## 📂 Project Structure

```
ReproHub/
├── app/                        # Streamlit web application
│   ├── pages/
│   │   ├── 1_upload.py         # File upload + claim extraction
│   │   ├── 2_review.py         # Column mapping + claim confirmation
│   │   ├── 3_dashboard.py      # Results visualisation
│   │   ├── 4_report.py         # PDF report generation
│   │   └── 5_about.py          # About page
│   ├── config.py               # App configuration
│   └── main.py                 # Entry point + navigation
│
├── core/                       # Core logic
│   ├── engine.py               # Statistical test engine (11 tests)
│   ├── extractor.py            # Regex-based claim extraction
│   ├── comparator.py           # Composite reproducibility scoring
│   ├── matcher.py              # Fuzzy column matching
│   ├── validator.py            # Claim validation
│   ├── remediation.py          # Remediation guidance
│   └── schema.py               # Shared data schemas
│
├── models/                     # Pydantic data models
│   ├── claim.py
│   ├── result.py               # Result model with composite scoring
│   ├── report.py
│   └── validation.py
│
├── utils/                      # Utility functions
│   ├── pdf_parser.py           # PDF text extraction
│   ├── fuzzy_matcher.py        # FuzzyWuzzy wrapper
│   ├── file_handlers.py
│   ├── report_generator.py     # PDF report generation
│   ├── visualizations.py
│   └── helpers.py
│
├── tests/                      # Unit tests
├── data/                       # Raw, processed, benchmark data
├── static/                     # CSS, images, templates
├── docs/                       # Documentation
├── requirements.txt
└── README.md
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Framework** | Streamlit |
| **Language** | Python 3.9+ |
| **Statistics** | SciPy, statsmodels |
| **ML / Encoding** | scikit-learn |
| **Visualization** | Plotly, Matplotlib, Seaborn |
| **PDF Processing** | PyPDF, pdfplumber |
| **Report Generation** | ReportLab, Jinja2 |
| **Fuzzy Matching** | FuzzyWuzzy + python-Levenshtein |
| **Data Models** | Pydantic v2 |
| **Deployment** | Streamlit Cloud |

---

## 📋 Requirements

```
pandas >= 2.0.0
numpy >= 1.24.0
scipy >= 1.10.0
statsmodels >= 0.14.0
scikit-learn >= 1.3.0
streamlit >= 1.29.0
plotly >= 5.17.0
matplotlib >= 3.7.0
pypdf >= 3.0.0
pdfplumber >= 0.10.0
reportlab >= 4.0.0
jinja2 >= 3.1.0
pydantic >= 2.0.0
fuzzywuzzy >= 0.18.0
python-Levenshtein >= 0.21.0
```

---

## 🤝 Contributing

Contributions are welcome. Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes with clear, documented code
4. Write or update tests where applicable
5. Commit with a descriptive message (`git commit -m 'feat: add X'`)
6. Push to your branch (`git push origin feature/your-feature`)
7. Open a Pull Request

Please open an issue first for major changes so we can discuss the approach.

---

## 🗺️ Roadmap

- [ ] LLM-powered claim extraction (prose-level, not just APA notation)
- [ ] LLM-powered column mapping (semantic, not just fuzzy string matching)
- [ ] Claim deduplication (same result across abstract + results section)
- [ ] Support for Excel, SPSS, Stata, and `.docx` input formats
- [ ] Batch mode (verify multiple papers at once)
- [ ] Unit test coverage for all core modules

---

## 👨‍💻 About the Developer

<div align="center">
<img src="https://avatars.githubusercontent.com/Junaid-Ahmed-Rupok" width="100" style="border-radius:50%"/>

### Sarder Junaid Ahmed
**Data Scientist & Machine Learning Engineer**

*Transforming complex data into strategic decisions through rigorous statistical modeling and production-ready machine learning systems.*

[![GitHub](https://img.shields.io/badge/GitHub-Junaid--Ahmed--Rupok-181717?logo=github)](https://github.com/Junaid-Ahmed-Rupok)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Sarder%20Junaid%20Ahmed-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sarder-junaid-ahmed-059b68240/)
[![Portfolio](https://img.shields.io/badge/Portfolio-junaid--ahmed--rupok.github.io-1E88E5?logo=githubpages&logoColor=white)](https://junaid-ahmed-rupok.github.io/__portfolio__Yes/)
[![Email](https://img.shields.io/badge/Email-junaidahmedrupok%40gmail.com-EA4335?logo=gmail&logoColor=white)](mailto:junaidahmedrupok@gmail.com)

</div>

**Specializations:** Statistical ML · Causal Inference · Trustworthy AI · Fairness-Aware ML · RAG Systems

**Selected Research:**
- 📄 **Ahmed, S.J.** et al. (2026). *Machine Learning for Crime Classification: A Fairness-Aware Approach to Class Imbalance.* Journal of Machine Learning and Applications, 2(1), 9–17. [DOI: 10.61577/jmla.2026.100002](https://doi.org/10.61577/jmla.2026.100002)
- 📄 **Ahmed, S.J.** et al. (2026). *CF-EGAT: A Causal Fairness-Aware Equity Graph Attention Network for Country-Level Environmental Livability Classification.* SPECTRA 2026. 🏆 **1st Best Paper Award**
- 📄 **Ahmed, S.J.** (2025). *Multi-Dimensional Statistical Similarity for Governance Classification: Beyond Arbitrary Thresholds.* APMEE 2025. 🏆 **Best Research Paper Award**

**Other Deployed Projects:**
- 🔬 [ReproHub](https://reproapp-8jb7vbhnqyltxq23bsr8xn.streamlit.app/) — Automated research reproducibility platform with composite scoring across 11 statistical tests
- 📊 [StatsPro](https://statistical-analysis-app-7axetqtx75ncuu7fr8irxj.streamlit.app/) — AI-powered statistical analysis platform with automated CSV-to-report workflows

**Honors:**
🏆 1st Best Paper — SPECTRA 2026 &nbsp;·&nbsp;
🏆 Best Research Paper — APMEE 2025 &nbsp;·&nbsp;
🎖️ Esteemed Alumni Award — YLRL RUET 2024 &nbsp;·&nbsp;
⭐ Perfect GPA 5.00/5.00 — SSC & HSC &nbsp;·&nbsp;
🎓 National Merit Scholarship — 2009 & 2013

---

## 📝 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built in response to the reproducibility crisis in scientific research. Powered entirely by open-source Python libraries.

<div align="center">

Built with [Streamlit](https://streamlit.io) · [LangChain](https://www.langchain.com) · [Groq](https://groq.com) · [FAISS](https://github.com/facebookresearch/faiss) · [sentence-transformers](https://www.sbert.net)

</div>

---

<p align="center">
  Made with ❤️ for open science and reproducible research
</p>
