# 📄 README.md — Copy & Paste

markdown
# 🔬 ReproHub

## Research Reproducibility Verification Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://reprohub.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 About

**ReproHub** is a web application that automatically verifies statistical claims from research papers by re-analyzing the original data.

**The Problem:** Researchers spend hours manually checking statistical results in papers. Most don't do it at all because it's too time-consuming.

**The Solution:** Upload a paper (PDF) and its dataset (CSV), and ReproHub automatically:
- 🤖 Extracts all statistical claims from the paper
- 🔬 Re-runs the statistical tests on the raw data
- 📊 Compares claimed results vs. actual results
- 📄 Generates a detailed reproducibility report

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Paper Upload** | Upload research papers in PDF format |
| 📊 **Dataset Upload** | Upload CSV datasets used in the paper |
| 🤖 **AI Extraction** | Automatically extracts statistical claims from the paper |
| 🔬 **Statistical Verification** | Re-runs t-tests, ANOVA, correlations, and more |
| 📊 **Interactive Dashboard** | Visualize results with charts and tables |
| 📄 **PDF Reports** | Generate professional reproducibility reports |
| 💡 **Remediation Guidance** | Get actionable advice for failed claims |
| 🔒 **No API Keys Required** | Works with mock data out of the box |

---

## 🚀 Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/Junaid-Ahmed-Rupok/ReproHub.git
cd ReproHub

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app/main.py
```

### Live Demo

👉 [https://reprohub.streamlit.app/](https://reprohub.streamlit.app/)

---

## 📂 Project Structure

```
ReproHub/
├── app/                    # Streamlit web application
│   ├── pages/              # App pages (upload, review, dashboard, report, about)
│   ├── __init__.py
│   ├── config.py           # Configuration settings
│   └── main.py             # Main entry point
├── core/                   # Core logic (statistics, extraction, comparison)
├── utils/                  # Utility functions
├── models/                 # Data models
├── tests/                  # Unit tests
├── data/                   # Data storage
├── static/                 # Static assets (CSS, images)
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 🔬 Supported Statistical Tests

| Test | Type |
|------|------|
| Independent t-test | Parametric |
| Paired t-test | Parametric |
| One-way ANOVA | Parametric |
| Pearson correlation | Parametric |
| Linear regression | Parametric |
| Mann-Whitney U | Non-parametric |
| Chi-square test | Non-parametric |
| Spearman correlation | Non-parametric |
| *Kruskal-Wallis H* | *Coming soon* |
| *Wilcoxon Signed-Rank* | *Coming soon* |
| *Logistic regression* | *Coming soon* |

---

## 📊 Understanding Results

| Status | Meaning |
|--------|---------|
| ✅ **Reproduced** | The claim matches the data (p-value difference < 0.01) |
| ⚠️ **Marginal** | Close but not exact (p-value difference 0.01-0.05) |
| ❌ **Not Reproduced** | The claim does not match the data (p-value difference ≥ 0.05) |
| ❓ **Could Not Verify** | Cannot test this claim (missing data, wrong type, unclear) |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Framework** | Streamlit |
| **Language** | Python 3.9+ |
| **Statistics** | SciPy, StatsModels |
| **Visualization** | Plotly, Matplotlib |
| **PDF Processing** | PyPDF, pdfplumber |
| **Report Generation** | ReportLab, Jinja2 |
| **Deployment** | Streamlit Cloud |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/contributing.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Junaid Ahmed Rupok**

- GitHub: [@Junaid-Ahmed-Rupok](https://github.com/Junaid-Ahmed-Rupok)
- Email: junaidahmedrupok@gmail.com

---

## 🙏 Acknowledgments

- Inspired by the reproducibility crisis in scientific research
- Built for the Erasmus Mundus Scholarship application
- Powered by open-source Python libraries

---

## 📧 Contact

For questions, feedback, or collaboration:

- **Email:** junaidahmedrupok@gmail.com
- **GitHub Issues:** [Report a bug](https://github.com/Junaid-Ahmed-Rupok/ReproHub/issues)

---

**Made with ❤️ for open science and reproducible research.**
```

---
