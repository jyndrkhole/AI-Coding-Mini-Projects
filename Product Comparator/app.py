"""Product Comparator — Gradio web portal."""

from __future__ import annotations

import traceback

import gradio as gr
import plotly.graph_objects as go

from src.comparison import (
    best_buy_markdown_link,
    build_price_history_figure,
    compare_product,
    comparison_matrix,
    get_trending,
    render_alternatives_html,
    render_summary_html,
    render_trending_html,
)
from src.config import FREE_MODELS, GROQ_MODEL, SERVER_HOST, SERVER_PORT
from src.groq_client import GroqService

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&display=swap');

:root, .gradio-container, body {
  color-scheme: light !important;
  --ink: #12263A;
  --muted: #4A6478;
  --sea: #1F7A6C;
  --sea-deep: #155E53;
  --mango: #F05A28;
  --mango-deep: #D9481C;
  --sky: #E8F4F1;
  --line: #C9D8E0;
  --card: #FFFFFF;
  --page: #F3F7F8;
  --font-display: 'Bricolage Grotesque', Georgia, sans-serif;
  --font-body: 'Figtree', 'Segoe UI', sans-serif;
}

html, body, .gradio-container, .gradio-container * {
  color-scheme: light !important;
}

.gradio-container {
  font-family: var(--font-body) !important;
  max-width: 1220px !important;
  margin: 0 auto !important;
  padding-bottom: 2rem !important;
  color: var(--ink) !important;
  background: var(--page) !important;
}

.gradio-container, .main, .contain, .app, .wrap {
  background:
    radial-gradient(1000px 480px at 0% -10%, rgba(31,122,108,0.16), transparent 55%),
    radial-gradient(800px 420px at 100% 0%, rgba(240,90,40,0.10), transparent 50%),
    linear-gradient(180deg, #F7FBFC 0%, #EEF4F6 100%) !important;
  color: var(--ink) !important;
}

label, .label-wrap, .label-wrap span, .block-label,
.prose, .prose *, .markdown, .markdown *, table, td, th,
.tab-nav button, .tabs, .form, .input-text, textarea, input, select,
.dataframe, .dataframe *, .pending, .generating {
  color: var(--ink) !important;
  font-family: var(--font-body) !important;
}

.block, .gr-group, .gr-box, .form, .panel {
  background: #FFFFFF !important;
  border-color: var(--line) !important;
  color: var(--ink) !important;
}

textarea, input, select, .scroll-hide textarea {
  background: #FFFFFF !important;
  color: var(--ink) !important;
  border-color: #9DB3C0 !important;
  font-family: var(--font-body) !important;
}

.tab-nav button {
  background: #FFFFFF !important;
  border-color: var(--line) !important;
  font-family: var(--font-body) !important;
}
.tab-nav button.selected {
  background: var(--sky) !important;
  color: var(--sea-deep) !important;
  font-weight: 700 !important;
}

#hero { padding: 1.7rem 0 0.25rem 0; }

#hero .hero-shell {
  display: grid;
  grid-template-columns: 1.45fr 0.8fr;
  gap: 1.2rem;
  align-items: end;
}

@media (max-width: 900px) {
  #hero .hero-shell { grid-template-columns: 1fr; }
}

#hero h1 {
  font-family: var(--font-display) !important;
  font-size: clamp(2.4rem, 4.6vw, 3.6rem) !important;
  line-height: 1.0 !important;
  color: var(--ink) !important;
  letter-spacing: -0.035em;
  margin: 0.2rem 0 0.6rem 0 !important;
}

#hero .subtitle {
  color: var(--muted) !important;
  font-size: 1.1rem;
  max-width: 42rem;
  margin: 0;
  line-height: 1.55;
  font-weight: 500;
}

.hero-stat {
  background: linear-gradient(155deg, #0F2E38 0%, #1F7A6C 100%) !important;
  color: #F4FFFB !important;
  border: none !important;
  border-radius: 20px;
  padding: 1.25rem 1.3rem;
  box-shadow: 0 18px 40px rgba(18, 38, 58, 0.22);
}

.hero-stat strong {
  display: block;
  font-family: var(--font-display);
  font-size: 1.5rem;
  margin-bottom: 0.55rem;
  color: #FFFFFF !important;
  letter-spacing: -0.02em;
}

.hero-stat, .hero-stat * {
  color: #E8FFF8 !important;
}

.store-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.55rem;
}

.store-chips a {
  display: inline-block;
  background: rgba(255,255,255,0.14) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(255,255,255,0.28);
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none !important;
}

.store-chips a:hover {
  background: rgba(255,255,255,0.24) !important;
}

.pc-cta, .pc-card-link, .pc-link-note a {
  pointer-events: auto !important;
  cursor: pointer !important;
  z-index: 2;
  position: relative;
}

#best-link-box {
  background: #FFF4EE !important;
  border: 2px solid #F05A28 !important;
  border-radius: 16px !important;
  padding: 0.85rem 1rem !important;
  margin: 0.75rem 0 1rem 0 !important;
}

#best-link-box a {
  color: #C2410C !important;
  font-size: 1.15rem !important;
  font-weight: 800 !important;
  text-decoration: underline !important;
}

.search-row { margin-top: 0.45rem !important; }

.pc-kicker {
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--sea-deep) !important;
  margin: 0 0 0.35rem 0;
  font-family: var(--font-body);
}

.pc-summary, .pc-overview, .pc-section, .pc-best-panel,
.pc-summary *, .pc-overview *, .pc-section *, .pc-card * {
  color: var(--ink);
  font-family: var(--font-body);
}

.pc-summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pc-best-panel {
  display: grid;
  grid-template-columns: 1.35fr 0.9fr;
  gap: 1rem;
  background: #FFFFFF;
  color: var(--ink);
  border: 2px solid var(--sea);
  border-radius: 22px;
  padding: 1.4rem 1.5rem;
  box-shadow: 0 18px 40px rgba(18, 38, 58, 0.08);
  animation: rise 0.55s ease both;
}

@media (max-width: 900px) {
  .pc-best-panel { grid-template-columns: 1fr; }
}

.pc-best-panel .pc-kicker { color: var(--sea-deep) !important; }
.pc-best-panel h2 {
  font-family: var(--font-display);
  font-size: clamp(1.55rem, 2.6vw, 2.1rem);
  margin: 0 0 0.35rem 0;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
}
.pc-platform-line {
  margin: 0 0 0.55rem 0;
  color: var(--muted) !important;
  font-weight: 500;
}
.pc-reason, .pc-body-text {
  margin: 0.2rem 0 0.8rem 0;
  color: #2C4556 !important;
  line-height: 1.6;
  font-size: 1rem;
}

.pc-best-pricebox {
  background: linear-gradient(165deg, #E8F4F1, #D7EEE8);
  border: 1px solid #9FD4C8;
  border-radius: 16px;
  padding: 1.05rem 1.1rem;
}

.pc-price {
  font-family: var(--font-display);
  font-size: 2.45rem;
  margin: 0.1rem 0 0.35rem 0;
  color: #12352F !important;
  letter-spacing: -0.03em;
}

.pc-list {
  margin: 0 0 0.95rem 0;
  color: #4A6478 !important;
  font-size: 0.95rem;
}

.pc-save {
  display: inline-block;
  margin-left: 0.35rem;
  background: #FFE8DF;
  color: #C2410C !important;
  border: 1px solid #FFB899;
  border-radius: 999px;
  padding: 0.12rem 0.58rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.pc-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  box-sizing: border-box;
  background: var(--mango);
  color: #FFFFFF !important;
  text-decoration: none !important;
  font-weight: 700;
  font-family: var(--font-body);
  border-radius: 12px;
  padding: 0.82rem 1rem;
  transition: transform 0.18s ease, background 0.18s ease;
}

.pc-cta:hover {
  background: var(--mango-deep);
  transform: translateY(-1px);
}

.pc-link-note {
  margin: 0.55rem 0 0 0;
  font-size: 0.72rem;
  color: #668094 !important;
  word-break: break-all;
}
.pc-link-note a { color: var(--sea) !important; font-weight: 600; }

.pc-badge {
  display: inline-block;
  background: #DDF3EE;
  border: 1px solid #8FCBBE;
  color: var(--sea-deep) !important;
  border-radius: 999px;
  padding: 0.22rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.pc-overview, .pc-section {
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1.25rem 1.35rem;
  animation: rise 0.65s ease both;
}

.pc-overview h2, .pc-section h2, .pc-card h3 {
  font-family: var(--font-display);
  margin: 0 0 0.45rem 0;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
}
.pc-overview h2, .pc-section h2 { font-size: 1.5rem; }

.pc-lede {
  color: var(--muted) !important;
  margin: 0 0 0.9rem 0;
  line-height: 1.6;
  font-size: 1.04rem;
  font-weight: 500;
}

.pc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
@media (max-width: 800px) {
  .pc-grid { grid-template-columns: 1fr; }
}
.pc-grid h3 {
  font-size: 0.95rem;
  margin: 0 0 0.4rem 0;
  color: var(--sea-deep) !important;
  font-weight: 700;
  font-family: var(--font-body);
}
.pc-grid ul {
  margin: 0;
  padding-left: 1.1rem;
  color: #2C4556 !important;
  line-height: 1.6;
}
.pc-grid li { color: #2C4556 !important; }

.pc-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0.95rem;
  margin-top: 0.85rem;
}

.pc-card {
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.05rem 1.1rem;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.pc-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 30px rgba(18, 38, 58, 0.09);
}

.pc-card.is-best {
  border: 2px solid var(--sea);
  background: #F0FAF7;
}

.pc-card.pc-editorial {
  background: #FFF6F1;
  border-color: #FFC4A8;
}

.pc-card-top {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  align-items: start;
}

.pc-store {
  margin: 0;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--sea-deep) !important;
}

.pc-card h3 {
  margin: 0.2rem 0 0 0 !important;
  font-size: 1.05rem;
  line-height: 1.35;
}

.pc-pill {
  display: inline-block;
  background: #DDF3EE;
  color: var(--sea-deep) !important;
  border: 1px solid #8FCBBE;
  border-radius: 999px;
  padding: 0.15rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
}
.pc-pill.best {
  background: #FFE8DF;
  color: #C2410C !important;
  border-color: #FFB899;
}

.pc-card-prices {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: baseline;
  margin: 0.7rem 0 0.55rem;
}

.pc-deal {
  font-family: var(--font-display);
  font-size: 1.45rem;
  color: #12352F !important;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.pc-mrp {
  color: #5B7384 !important;
  font-size: 0.88rem;
}

.pc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 0.75rem;
}
.pc-meta span {
  background: #EEF4F7;
  color: #2C4556 !important;
  border: 1px solid #D5E1E8;
  border-radius: 8px;
  padding: 0.2rem 0.5rem;
  font-size: 0.76rem;
  font-weight: 600;
}

.pc-card-link {
  display: inline-block;
  color: var(--sea) !important;
  font-weight: 700;
  text-decoration: none !important;
  font-size: 0.94rem;
}
.pc-card-link:hover { text-decoration: underline !important; }

.pc-empty {
  padding: 1rem;
  color: var(--muted) !important;
  background: #FFFFFF;
  border-radius: 12px;
  border: 1px dashed #9DB3C0;
  font-size: 0.98rem;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

footer, .footer { display: none !important; }
"""


def _empty_figure() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title="Price history will appear after a search",
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFC",
        height=380,
        font=dict(family="Figtree, sans-serif", color="#12263A"),
    )
    return fig


PLACEHOLDER_SUMMARY = """
<div class="pc-summary">
  <div class="pc-overview">
    <p class="pc-kicker">Ready when you are</p>
    <h2>Search a product to unlock the best buy</h2>
    <p class="pc-lede">
      Compare deal vs list price across Amazon, Flipkart, Croma and more — plus expert picks
      from NDTV Shopping, Hindustan Times, Gadgets 360 and similar recommendation sites.
    </p>
  </div>
</div>
"""


def run_compare(query: str, model: str):
    query = (query or "").strip()
    if not query:
        raise gr.Error("Enter a product name to compare.")

    try:
        groq = GroqService(model=model or GROQ_MODEL)
        data = compare_product(query, groq=groq)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise gr.Error(f"Comparison failed: {exc}") from exc

    return (
        render_summary_html(data),
        best_buy_markdown_link(data),
        comparison_matrix(data),
        render_alternatives_html(data),
        build_price_history_figure(data),
    )


def run_trending(category: str, model: str):
    try:
        groq = GroqService(model=model or GROQ_MODEL)
        data = get_trending(category or "All", groq=groq)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise gr.Error(f"Trending fetch failed: {exc}") from exc
    return render_trending_html(data)


def build_ui() -> tuple[gr.Blocks, gr.themes.ThemeClass]:
    theme = gr.themes.Soft(
        primary_hue=gr.themes.Color(
            c50="#E8F4F1",
            c100="#D7EEE8",
            c200="#9FD4C8",
            c300="#6BB9A8",
            c400="#3D9A88",
            c500="#1F7A6C",
            c600="#1F7A6C",
            c700="#155E53",
            c800="#124A42",
            c900="#0D342F",
            c950="#082420",
        ),
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Figtree"),
        font_mono=gr.themes.GoogleFont("IBM Plex Mono"),
    ).set(
        body_background_fill="#F3F7F8",
        body_text_color="#12263A",
        block_background_fill="#FFFFFF",
        block_label_text_color="#12263A",
        block_title_text_color="#12263A",
        block_border_color="#C9D8E0",
        border_color_primary="#C9D8E0",
        input_background_fill="#FFFFFF",
        input_border_color="#9DB3C0",
        button_primary_background_fill="#1F7A6C",
        button_primary_background_fill_hover="#155E53",
        button_primary_text_color="#ffffff",
    )

    with gr.Blocks(title="Product Comparator") as demo:
        with gr.Column(elem_id="hero"):
            gr.HTML(
                """
                <div class="hero-shell">
                  <div>
                    <p class="pc-kicker" style="margin:0;">Stores + expert recommendations</p>
                    <h1>Product Comparator: Smart Search</h1>
                    <p class="subtitle">
                      Find the best buy with deal price, list price, and working store links —
                      plus picks from NDTV Shopping, Hindustan Times and more.
                    </p>
                  </div>
                  <div class="hero-stat">
                    <strong>Shop smarter in one search</strong>
                    <div class="store-chips">
                      <a href="https://www.amazon.in/" target="_blank" rel="noopener">Amazon</a>
                      <a href="https://www.flipkart.com/" target="_blank" rel="noopener">Flipkart</a>
                      <a href="https://www.croma.com/" target="_blank" rel="noopener">Croma</a>
                      <a href="https://www.reliancedigital.in/" target="_blank" rel="noopener">Reliance</a>
                      <a href="https://www.tatacliq.com/" target="_blank" rel="noopener">Tata CLiQ</a>
                      <a href="https://www.vijaysales.com/" target="_blank" rel="noopener">Vijay Sales</a>
                    </div>
                  </div>
                </div>
                """
            )

        with gr.Row(elem_classes=["search-row"]):
            query = gr.Textbox(
                label="What are you buying?",
                placeholder="e.g. Sony WH-1000XM5, iPhone 16, 3L geyser…",
                scale=5,
                autofocus=True,
            )
            model = gr.Dropdown(
                choices=FREE_MODELS,
                value=GROQ_MODEL if GROQ_MODEL in FREE_MODELS else FREE_MODELS[0],
                label="Groq model",
                scale=2,
            )
            compare_btn = gr.Button("Find best buy", variant="primary", scale=1)

        with gr.Tabs():
            with gr.Tab("Best buy & comparison"):
                summary = gr.HTML(value=PLACEHOLDER_SUMMARY)
                best_link = gr.Markdown(
                    value="Best buy store link will appear here after search.",
                    elem_id="best-link-box",
                )
                matrix = gr.Dataframe(
                    label="Precise comparison matrix",
                    interactive=False,
                    wrap=True,
                )
                gr.Markdown("### Relevant alternatives")
                alts = gr.HTML(value="<div class='pc-empty'>Alternatives appear after a search.</div>")

            with gr.Tab("Price history"):
                chart = gr.Plot(value=_empty_figure(), label="12-month price history")

            with gr.Tab("Trending"):
                with gr.Row():
                    category = gr.Dropdown(
                        choices=[
                            "All",
                            "Electronics",
                            "Mobiles",
                            "Fashion",
                            "Beauty",
                            "Home",
                            "Appliances",
                            "Sports",
                        ],
                        value="All",
                        label="Category",
                        scale=3,
                    )
                    trend_btn = gr.Button("Load trending", variant="primary", scale=1)
                trending = gr.HTML(
                    value="<div class='pc-empty'>Load trending products to see prices and store links.</div>"
                )

        compare_btn.click(
            fn=run_compare,
            inputs=[query, model],
            outputs=[summary, best_link, matrix, alts, chart],
        )
        query.submit(
            fn=run_compare,
            inputs=[query, model],
            outputs=[summary, best_link, matrix, alts, chart],
        )
        trend_btn.click(fn=run_trending, inputs=[category, model], outputs=[trending])

        gr.Examples(
            examples=[
                ["Sony WH-1000XM5"],
                ["Apple iPhone 16 128GB"],
                ["Samsung Galaxy Watch 7"],
                ["Nike Air Force 1"],
                ["Dyson V15 Detect"],
            ],
            inputs=[query],
            label="Popular searches",
        )

    return demo, theme


if __name__ == "__main__":
    app, theme = build_ui()
    print(f"\nProduct Comparator running at http://{SERVER_HOST}:{SERVER_PORT}\n", flush=True)
    app.launch(
        server_name=SERVER_HOST,
        server_port=SERVER_PORT,
        share=False,
        inbrowser=True,
        theme=theme,
        css=CUSTOM_CSS,
    )
