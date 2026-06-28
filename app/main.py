"""
ReproHub - Main Application Entry Point
Streamlit web application for research reproducibility verification.
"""
import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="ReproHub - Research Reproducibility Verification",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.config import config, ConfigError

# Pages, in pipeline order, with the session-state flag (if any) required
# to reach them. "upload" has no prerequisite - it's the front door.
PAGE_ORDER = [
    ("📤 Upload", "upload", None),
    ("📋 Review", "review", "extraction_complete"),
    ("📊 Dashboard", "dashboard", "analysis_complete"),
    ("📄 Report", "report", "analysis_complete"),
    ("ℹ️ About", "about", None),
]


def init_session_state() -> None:
    """Initialize all session state variables."""
    defaults = {
        # Upload state
        "paper_file": None,
        "dataset_file": None,
        "paper_text": None,
        "dataset_df": None,

        # Extraction state
        "claims": [],
        "extraction_complete": False,
        "column_mappings": {},

        # Review state
        "confirmed_claims": [],
        "review_complete": False,

        # Results state
        "results": [],
        "reproducibility_score": None,
        "analysis_complete": False,

        # Report state
        "report_generated": False,
        "report_data": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> str:
    """Render the sidebar navigation. Returns the selected page's slug."""
    with st.sidebar:
        st.title("🔬 ReproHub")
        st.caption(config.APP_DESCRIPTION)
        st.divider()

        labels = [label for label, _slug, _req in PAGE_ORDER]
        slugs = {label: slug for label, slug, _req in PAGE_ORDER}
        requirements = {label: req for label, _slug, req in PAGE_ORDER}

        selected_label = st.radio(
            "Navigation",
            labels,
            index=0,
            key="navigation",
        )

        # Block navigation to pages whose prerequisite step hasn't run yet,
        # instead of letting the page crash on missing data.
        required_flag = requirements[selected_label]
        if required_flag and not st.session_state.get(required_flag):
            st.warning(
                "Complete the previous step first to unlock this page.",
                icon="🔒",
            )
            selected_label = "📤 Upload"

        st.divider()

        # Status indicators
        st.subheader("📊 Progress")

        col1, col2 = st.columns(2)
        with col1:
            claims_count = len(st.session_state.claims) if st.session_state.claims else 0
            st.metric("Claims", claims_count)

        with col2:
            score = st.session_state.reproducibility_score
            if score is not None:
                st.metric("Score", f"{score}%")
            else:
                st.metric("Score", "—")

        # Show status indicators
        st.divider()
        status = []
        if st.session_state.extraction_complete:
            status.append("✅ Claims extracted")
        if st.session_state.review_complete:
            status.append("✅ Claims confirmed")
        if st.session_state.analysis_complete:
            status.append("✅ Analysis complete")

        if status:
            for s in status:
                st.write(s)
        else:
            st.caption("Upload files to begin")

        st.divider()
        st.caption(f"v{config.APP_VERSION}")

    return slugs[selected_label]


def render_page(slug: str) -> None:
    """Import and render the selected page, failing gracefully if it
    isn't implemented yet or raises an error."""
    try:
        module = __import__(f"app.pages.{slug}", fromlist=["render"])
    except ModuleNotFoundError:
        st.info(f"The **{slug.title()}** page hasn't been built yet. Check back soon.")
        return

    try:
        module.render()
    except Exception as exc:  # noqa: BLE001 - surface page errors without killing the app
        st.error(f"Something went wrong loading this page: {exc}")
        if config.DEBUG:
            st.exception(exc)


def main() -> None:
    """Main application entry point."""
    # Ensure directories exist
    config.ensure_directories()

    # Fail fast and visibly if required config (e.g. OPENAI_API_KEY,
    # AI_MODEL) is missing, instead of crashing later inside extraction.
    try:
        config.validate(require_ai=True)
    except ConfigError as exc:
        st.error("ReproHub is misconfigured and cannot start safely.")
        st.code(str(exc))
        st.stop()

    # Initialize session state
    init_session_state()

    # Render sidebar and get selected page
    selected_slug = render_sidebar()

    # Render the selected page
    render_page(selected_slug)


if __name__ == "__main__":
    main()
