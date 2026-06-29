"""
About Page — Help and Documentation

Premium instrument-panel aesthetic. All HTML built via string
concatenation (no f-strings touching HTML) so Streamlit never
escapes curly-brace CSS variables.
"""

import streamlit as st
from datetime import datetime
from app.config import config
from core.engine import StatisticalTestEngine

_TEST_META = {
    "t_test_independent":   ("Independent t-test",      "parametric",    "Cohen's d"),
    "paired_t_test":        ("Paired t-test",            "parametric",    "Cohen's d"),
    "one_way_anova":        ("One-way ANOVA",            "parametric",    "Eta-squared η²"),
    "pearson_correlation":  ("Pearson Correlation",      "parametric",    "r"),
    "linear_regression":    ("Linear Regression",        "parametric",    "R² / Adj-R²"),
    "logistic_regression":  ("Logistic Regression",      "parametric",    "McFadden pseudo-R²"),
    "mann_whitney_u":       ("Mann-Whitney U",           "nonparametric", "Rank-biserial r"),
    "kruskal_wallis":       ("Kruskal-Wallis H",         "nonparametric", "Eta-squared (approx.)"),
    "wilcoxon_signed_rank": ("Wilcoxon Signed-Rank",     "nonparametric", "Rank-biserial r"),
    "spearman_correlation": ("Spearman Correlation",     "nonparametric", "ρ (rho)"),
    "chi_square":           ("Chi-Square Test",          "nonparametric", "Cramér's V"),
}

_CATEGORY_LABEL = {"parametric": "Parametric", "nonparametric": "Non-parametric"}


# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');

/* ── Tokens ── */
:root {
  --bg:            #080c12;
  --surface:       #0d1117;
  --surface-2:     #111722;
  --border:        rgba(99,120,160,0.15);
  --border-bright: rgba(99,120,160,0.30);
  --text-primary:  #e8edf5;
  --text-secondary:#7a8ba8;
  --text-muted:    #4a5568;
  --accent:        #3b82f6;
  --accent-dim:    rgba(59,130,246,0.12);
  --accent-glow:   rgba(59,130,246,0.25);
  --green:         #22c55e;
  --green-dim:     rgba(34,197,94,0.12);
  --amber:         #f59e0b;
  --amber-dim:     rgba(245,158,11,0.12);
  --red:           #ef4444;
  --red-dim:       rgba(239,68,68,0.12);
  --slate:         rgba(99,120,160,0.10);
  --radius:        10px;
  --radius-sm:     6px;
  --mono:          'JetBrains Mono', monospace;
  --display:       'Syne', sans-serif;
  --body:          'Inter', sans-serif;
}

/* ── Reset Streamlit chrome ── */
.block-container { max-width: 860px !important; padding: 2rem 1.5rem 4rem !important; }
.stApp { background: var(--bg) !important; }

/* ── Hero ── */
.ab-hero {
  position: relative;
  padding: 3rem 2.5rem 2.5rem;
  background: var(--surface);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius);
  margin-bottom: 2rem;
  overflow: hidden;
}
.ab-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 50% at 10% 20%, rgba(59,130,246,0.06) 0%, transparent 70%),
    radial-gradient(ellipse 40% 40% at 90% 80%, rgba(34,197,94,0.04) 0%, transparent 60%);
  pointer-events: none;
}
.ab-hero-eyebrow {
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  color: var(--accent);
  text-transform: uppercase;
  margin-bottom: 0.9rem;
}
.ab-hero-title {
  font-family: var(--display);
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.05;
  letter-spacing: -0.02em;
  margin: 0 0 0.6rem;
}
.ab-hero-title span {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 40%, #6366f1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.ab-hero-tagline {
  font-family: var(--body);
  font-size: 1.0rem;
  font-weight: 400;
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 540px;
  margin: 0 0 1.6rem;
}
.ab-pill-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.ab-pill {
  font-family: var(--mono);
  font-size: 0.70rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 0.25rem 0.75rem;
  letter-spacing: 0.03em;
}
.ab-pill.accent { color: var(--accent); border-color: rgba(59,130,246,0.30); background: var(--accent-dim); }

/* ── Section label ── */
.ab-section-label {
  font-family: var(--mono);
  font-size: 0.65rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 0 0 0.75rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1rem;
}

/* ── Generic card ── */
.ab-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  margin-bottom: 1rem;
}
.ab-card p { color: var(--text-secondary); font-family: var(--body); font-size: 0.95rem; line-height: 1.7; margin: 0; }
.ab-card strong { color: var(--text-primary); font-weight: 600; }

/* ── Steps ── */
.ab-steps { display: flex; flex-direction: column; gap: 0; }
.ab-step {
  display: grid;
  grid-template-columns: 2.4rem 1fr;
  gap: 1rem;
  padding: 1.1rem 1.5rem;
  position: relative;
}
.ab-step:not(:last-child) { border-bottom: 1px solid var(--border); }
.ab-step-num {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--accent-dim);
  border: 1px solid rgba(59,130,246,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--accent);
  flex-shrink: 0;
  margin-top: 0.1rem;
}
.ab-step-title {
  font-family: var(--body);
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.2rem;
}
.ab-step-desc {
  font-family: var(--body);
  font-size: 0.86rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* ── Scoring bar ── */
.ab-score-wrap { padding: 1.5rem; }
.ab-score-label {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  margin-bottom: 1rem;
}
.ab-bar {
  display: flex;
  height: 6px;
  border-radius: 100px;
  overflow: hidden;
  gap: 2px;
  margin-bottom: 1.1rem;
}
.ab-bar-p  { background: var(--accent); border-radius: 100px; }
.ab-bar-es { background: var(--green);  border-radius: 100px; }
.ab-bar-ts { background: var(--amber);  border-radius: 100px; }
.ab-legend { display: flex; flex-wrap: wrap; gap: 1.1rem; }
.ab-legend-item {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-family: var(--body);
  font-size: 0.82rem;
  color: var(--text-secondary);
}
.ab-legend-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ab-legend-pct {
  font-family: var(--mono);
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-primary);
}

/* ── Badge grid ── */
.ab-badge-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  margin-bottom: 1rem;
}
.ab-badge-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.ab-verdict {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 500;
  border-radius: 100px;
  padding: 0.28rem 0.75rem;
  letter-spacing: 0.04em;
}
.ab-verdict.reproduced    { color: var(--green); background: var(--green-dim); border: 1px solid rgba(34,197,94,0.25); }
.ab-verdict.marginal      { color: var(--amber); background: var(--amber-dim); border: 1px solid rgba(245,158,11,0.25); }
.ab-verdict.not-repro     { color: var(--red);   background: var(--red-dim);   border: 1px solid rgba(239,68,68,0.25); }
.ab-verdict.could-not     { color: var(--text-muted); background: var(--slate); border: 1px solid var(--border); }
.ab-verdict-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.ab-score-range {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* ── Test grid ── */
.ab-test-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.65rem;
  margin-bottom: 1rem;
}
.ab-test-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
  transition: border-color 0.15s;
  position: relative;
  overflow: hidden;
}
.ab-test-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
}
.ab-test-card.parametric::before    { background: linear-gradient(90deg, var(--accent), transparent); }
.ab-test-card.nonparametric::before { background: linear-gradient(90deg, var(--green), transparent); }
.ab-test-tag {
  font-family: var(--mono);
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  margin-bottom: 0.45rem;
}
.parametric    .ab-test-tag { color: var(--accent); }
.nonparametric .ab-test-tag { color: var(--green); }
.ab-test-name {
  font-family: var(--body);
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.3rem;
}
.ab-test-effect {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* ── Tech pills ── */
.ab-tech-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 1rem; }
.ab-tech-pill {
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--text-secondary);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.3rem 0.7rem;
}

/* ── Divider ── */
.ab-divider { border: none; border-top: 1px solid var(--border); margin: 1.75rem 0; }

/* ── Footer ── */
.ab-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.ab-footer span {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-muted);
}
.ab-footer a {
  color: var(--accent) !important;
  text-decoration: none;
}
.ab-footer a:hover { text-decoration: underline; }

/* ── Responsive ── */
@media (max-width: 600px) {
  .ab-badge-grid { grid-template-columns: 1fr; }
  .ab-hero { padding: 2rem 1.2rem; }
}
</style>
"""


def _test_card(test_type: str) -> str:
    name, category, effect = _TEST_META[test_type]
    tag = _CATEGORY_LABEL[category]
    return (
        '<div class="ab-test-card ' + category + '">'
        + '<div class="ab-test-tag">' + tag + "</div>"
        + '<div class="ab-test-name">' + name + "</div>"
        + '<div class="ab-test-effect">' + effect + "</div>"
        + "</div>"
    )


def render():
    supported = StatisticalTestEngine.SUPPORTED_TESTS

    missing_meta = supported - _TEST_META.keys()
    if missing_meta:
        st.warning(
            "⚠️ Tests with no display metadata: "
            + str(sorted(missing_meta))
            + ". Add them to _TEST_META in about.py."
        )

    # Inject CSS
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────
    hero = (
        '<div class="ab-hero">'
        + '<div class="ab-hero-eyebrow">Research Reproducibility Platform</div>'
        + '<p class="ab-hero-title"><span>' + config.APP_NAME + "</span></p>"
        + '<p class="ab-hero-tagline">' + config.APP_DESCRIPTION + "</p>"
        + '<div class="ab-pill-row">'
        + '<span class="ab-pill accent">v' + config.APP_VERSION + "</span>"
        + '<span class="ab-pill">MIT License</span>'
        + '<span class="ab-pill">' + str(len(supported)) + " statistical tests</span>"
        + '<span class="ab-pill">No API keys required</span>'
        + '<span class="ab-pill">Open source</span>'
        + "</div>"
        + "</div>"
    )
    st.markdown(hero, unsafe_allow_html=True)

    # ── Mission ───────────────────────────────────────────────────────
    st.markdown('<div class="ab-section-label">Why it exists</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ab-card"><p>'
        "Most published statistical claims are never independently re-checked against "
        "the underlying data. <strong>ReproHub</strong> closes that gap: upload a paper "
        "and its dataset, and it re-runs every reported test from scratch with "
        "SciPy / statsmodels, then scores how well each claim holds up — "
        "no manual spreadsheet work, no guesswork."
        "</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ab-divider"></div>', unsafe_allow_html=True)

    # ── How it works ──────────────────────────────────────────────────
    st.markdown('<div class="ab-section-label">How it works</div>', unsafe_allow_html=True)
    steps = [
        ("Upload",              "Provide the research paper (PDF) and its raw dataset (CSV or Excel)."),
        ("Extract &amp; review","Claims are pulled from APA-style notation and fuzzy-matched to dataset columns — confirm or correct mappings before verifying."),
        ("Verify",              "Each claim is re-run against your data with the appropriate test, then scored with a composite model — not just a p-value check."),
        ("Dashboard",           "Inspect per-claim verdicts, numeric discrepancies, and the weakest scoring component behind any failure."),
        ("Export report",       "Download a shareable reproducibility report with the complete breakdown for review or submission."),
    ]
    step_html = ""
    for i, (title, desc) in enumerate(steps, start=1):
        step_html += (
            '<div class="ab-step">'
            + '<div class="ab-step-num">' + str(i).zfill(2) + "</div>"
            + "<div>"
            + '<div class="ab-step-title">' + title + "</div>"
            + '<div class="ab-step-desc">' + desc + "</div>"
            + "</div>"
            + "</div>"
        )
    st.markdown(
        '<div class="ab-card" style="padding: 0;"><div class="ab-steps">' + step_html + "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ab-divider"></div>', unsafe_allow_html=True)

    # ── Scoring ───────────────────────────────────────────────────────
    st.markdown('<div class="ab-section-label">Composite scoring</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ab-card ab-score-wrap">'
        + '<div class="ab-score-label">Three components weighted into a single reproducibility score (0 – 1)</div>'
        + '<div class="ab-bar">'
        + '<div class="ab-bar-p"  style="width:50%"></div>'
        + '<div class="ab-bar-es" style="width:30%"></div>'
        + '<div class="ab-bar-ts" style="width:20%"></div>'
        + "</div>"
        + '<div class="ab-legend">'
        + '<div class="ab-legend-item"><div class="ab-legend-dot" style="background:var(--accent)"></div>'
        + 'p-value agreement <span class="ab-legend-pct">50%</span></div>'
        + '<div class="ab-legend-item"><div class="ab-legend-dot" style="background:var(--green)"></div>'
        + 'Effect size agreement <span class="ab-legend-pct">30%</span></div>'
        + '<div class="ab-legend-item"><div class="ab-legend-dot" style="background:var(--amber)"></div>'
        + 'Test statistic agreement <span class="ab-legend-pct">20%</span></div>'
        + "</div></div>",
        unsafe_allow_html=True,
    )

    verdicts = [
        ("reproduced", "Reproduced",       "score &ge; 0.80"),
        ("marginal",   "Marginal",         "score &ge; 0.55"),
        ("not-repro",  "Not reproduced",   "score &lt; 0.55"),
        ("could-not",  "Could not verify", "test could not run"),
    ]
    badge_html = ""
    for cls, label, meaning in verdicts:
        badge_html += (
            '<div class="ab-badge-card">'
            + '<span class="ab-verdict ' + cls + '">'
            + '<span class="ab-verdict-dot"></span>' + label
            + "</span>"
            + '<span class="ab-score-range">' + meaning + "</span>"
            + "</div>"
        )
    st.markdown(
        '<div class="ab-badge-grid">' + badge_html + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ab-divider"></div>', unsafe_allow_html=True)

    # ── Supported tests ───────────────────────────────────────────────
    st.markdown(
        '<div class="ab-section-label">Supported statistical tests</div>',
        unsafe_allow_html=True,
    )
    cards = "".join(_test_card(t) for t in sorted(supported) if t in _TEST_META)
    st.markdown(
        '<div class="ab-test-grid">' + cards + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ab-divider"></div>', unsafe_allow_html=True)

    # ── Tech stack ────────────────────────────────────────────────────
    st.markdown('<div class="ab-section-label">Built with</div>', unsafe_allow_html=True)
    tech = [
        "Streamlit", "SciPy", "statsmodels", "scikit-learn",
        "Plotly", "Matplotlib", "PyPDF", "pdfplumber",
        "ReportLab", "Jinja2", "Pydantic v2", "FuzzyWuzzy",
    ]
    tech_pills = "".join('<span class="ab-tech-pill">' + t + "</span>" for t in tech)
    st.markdown(
        '<div class="ab-tech-row">' + tech_pills + "</div>",
        unsafe_allow_html=True,
    )

    # ── Footer ────────────────────────────────────────────────────────
    year = str(datetime.now().year)
    st.markdown(
        '<div class="ab-footer">'
        + "<span>&copy; " + year + " Junaid Ahmed Rupok &middot; MIT License</span>"
        + "<span>"
        + '<a href="https://github.com/Junaid-Ahmed-Rupok/ReproHub" target="_blank">GitHub</a>'
        + " &nbsp;&middot;&nbsp; "
        + '<a href="mailto:junaidahmedrupok@gmail.com">Contact</a>'
        + "</span>"
        + "</div>",
        unsafe_allow_html=True,
    )
