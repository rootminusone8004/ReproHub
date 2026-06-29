"""
About Page — Help and Documentation

Rebuilt to actually use the design system already defined in
static/css/styles.css (signal colors, status badges, mono/display
fonts, surface cards) instead of a plain st.markdown() text dump. That
stylesheet ships a full "instrument panel" theme - including a
.status-badge component for reproduced/marginal/not_reproduced/
could_not_verify - but nothing in the app actually used it; this page
is the first to put those tokens to work.
"""

import streamlit as st
from datetime import datetime
from app.config import config
from core.engine import StatisticalTestEngine

# Single source of truth per test: display name, category (drives which
# accent color its card gets), and the effect size it reports. Replaces
# the old standalone _TEST_DISPLAY_NAMES dict - same drift-safety
# guarantee (every key in StatisticalTestEngine.SUPPORTED_TESTS must
# have an entry here, checked below), but one place to edit instead of
# two, and rich enough to render a real card instead of a bullet point.
_TEST_META = {
    "t_test_independent": ("Independent t-test", "parametric", "Cohen's d"),
    "paired_t_test": ("Paired t-test", "parametric", "Cohen's d"),
    "one_way_anova": ("One-way ANOVA", "parametric", "Eta-squared (η²)"),
    "pearson_correlation": ("Pearson correlation", "parametric", "r"),
    "linear_regression": ("Linear regression", "parametric", "R² / Adj-R²"),
    "logistic_regression": ("Logistic regression", "parametric", "McFadden pseudo-R²"),
    "mann_whitney_u": ("Mann-Whitney U", "nonparametric", "Rank-biserial r"),
    "kruskal_wallis": ("Kruskal-Wallis H", "nonparametric", "Eta-squared (approx.)"),
    "wilcoxon_signed_rank": ("Wilcoxon signed-rank", "nonparametric", "Rank-biserial r"),
    "spearman_correlation": ("Spearman correlation", "nonparametric", "ρ (rho)"),
    "chi_square": ("Chi-square test", "nonparametric", "Cramér's V"),
}

_CATEGORY_LABEL = {"parametric": "Parametric", "nonparametric": "Non-parametric"}


def _test_card(test_type: str) -> str:
    name, category, effect = _TEST_META[test_type]
    return f"""
    <div class="rh-test-card rh-test-{category}">
        <div class="rh-category-tag">{_CATEGORY_LABEL[category]}</div>
        <div class="rh-test-name">{name}</div>
        <div class="rh-test-effect">Effect size: {effect}</div>
    </div>
    """


def render():
    supported = StatisticalTestEngine.SUPPORTED_TESTS
    missing_meta = supported - _TEST_META.keys()
    if missing_meta:
        # Surfaced visibly rather than silently skipped, so a newly
        # added engine test is impossible to forget about here.
        st.warning(
            f"⚠️ Engine supports test(s) with no display metadata configured: "
            f"{sorted(missing_meta)}. Add them to _TEST_META in this file.",
        )

    # ---- Hero -----------------------------------------------------
    st.markdown(
        f"""
        <div class="rh-hero">
            <div class="rh-hero-icon">🔬</div>
            <div>
                <p class="rh-hero-title">{config.APP_NAME}</p>
                <p class="rh-hero-tagline">{config.APP_DESCRIPTION}</p>
                <div class="rh-meta-row">
                    <span class="rh-pill">v{config.APP_VERSION}</span>
                    <span class="rh-pill">MIT License</span>
                    <span class="rh-pill">{len(supported)} statistical tests</span>
                    <span class="rh-pill">No API keys required</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Mission ----------------------------------------------------
    st.markdown('<div class="rh-section-label">Why it exists</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="rh-card">
        Most published statistical claims are never independently re-checked against
        the underlying data. <strong>ReproHub</strong> closes that gap: upload a paper
        and its dataset, and it re-runs every reported test from scratch with
        SciPy/statsmodels, then scores how well each claim holds up against the raw
        numbers — no manual spreadsheet work, no guesswork.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- How it works -------------------------------------------------
    st.markdown('<div class="rh-section-label">How it works</div>', unsafe_allow_html=True)
    steps = [
        ("📄", "Upload", "Provide the research paper (PDF) and its dataset (CSV or Excel)."),
        ("📋", "Extract & review", "Claims are pulled from APA-style notation and fuzzy-matched to dataset columns — confirm or fix mappings before verifying."),
        ("🔬", "Verify", "Each claim's test is re-run for real against your data, then scored with composite scoring (not just a p-value check)."),
        ("📊", "Dashboard", "See per-claim verdicts, discrepancies, and the weakest component behind any failure."),
        ("📄", "Report", "Export a shareable reproducibility report with the full breakdown."),
    ]
    step_html = "".join(
        f"""
        <div class="rh-step">
            <div class="rh-step-number">{i}</div>
            <div>
                <div class="rh-step-title">{icon} {title}</div>
                <div class="rh-step-desc">{desc}</div>
            </div>
        </div>
        """
        for i, (icon, title, desc) in enumerate(steps, start=1)
    )
    st.markdown(f'<div class="rh-card">{step_html}</div>', unsafe_allow_html=True)

    # ---- Scoring methodology -----------------------------------------
    st.markdown('<div class="rh-section-label">How scoring works</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="rh-card">
        <p style="color: var(--text-secondary); margin-bottom: 0.3rem;">
        Composite score — weighs three components together, rather than a bare p-value match:
        </p>
        <div class="rh-weight-bar">
            <div class="rh-weight-segment-p" style="width:50%"></div>
            <div class="rh-weight-segment-es" style="width:30%"></div>
            <div class="rh-weight-segment-st" style="width:20%"></div>
        </div>
        <div class="rh-legend">
            <span><span class="rh-legend-dot" style="background:var(--accent)"></span>p-value agreement — 50%</span>
            <span><span class="rh-legend-dot" style="background:var(--signal-verified)"></span>effect size agreement — 30%</span>
            <span><span class="rh-legend-dot" style="background:var(--signal-marginal)"></span>test statistic agreement — 20%</span>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 0.6rem"></div>', unsafe_allow_html=True)

    badges = [
        ("status-reproduced", "Reproduced", "score ≥ 0.80"),
        ("status-marginal", "Marginal", "score ≥ 0.55"),
        ("status-not-reproduced", "Not reproduced", "score < 0.55"),
        ("status-could-not-verify", "Could not verify", "test couldn't be run"),
    ]
    badge_html = "".join(
        f"""
        <div class="rh-card" style="display:flex; align-items:center; justify-content:space-between; gap: 0.75rem;">
            <span class="status-badge {cls}">{label}</span>
            <span class="rh-test-effect">{meaning}</span>
        </div>
        """
        for cls, label, meaning in badges
    )
    st.markdown(f'<div class="rh-grid">{badge_html}</div>', unsafe_allow_html=True)

    # ---- Supported tests ----------------------------------------------
    st.markdown('<div class="rh-section-label">Supported statistical tests</div>', unsafe_allow_html=True)
    cards = "".join(_test_card(t) for t in sorted(supported) if t in _TEST_META)
    st.markdown(f'<div class="rh-grid">{cards}</div>', unsafe_allow_html=True)

    # ---- Tech stack -----------------------------------------------------
    st.markdown('<div class="rh-section-label">Built with</div>', unsafe_allow_html=True)
    tech = [
        "Streamlit", "SciPy", "statsmodels", "scikit-learn", "Plotly",
        "Matplotlib", "PyPDF", "pdfplumber", "ReportLab", "Jinja2",
        "Pydantic v2", "FuzzyWuzzy",
    ]
    tech_html = "".join(f'<span class="rh-tech-pill">{t}</span>' for t in tech)
    st.markdown(f'<div class="rh-tech-row">{tech_html}</div>', unsafe_allow_html=True)

    # ---- Footer ----------------------------------------------------------
    st.markdown(
        f"""
        <div class="rh-footer">
            <span>© {datetime.now().year} Junaid Ahmed Rupok · MIT License</span>
            <span>
                <a href="https://github.com/Junaid-Ahmed-Rupok/ReproHub" target="_blank">GitHub</a>
                &nbsp;·&nbsp;
                <a href="mailto:junaidahmedrupok@gmail.com">Contact</a>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
