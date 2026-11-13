import os
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.simulator import simulator
from models.wave_detector import monowave
from models.identifier import identifier


DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "btcusd.csv")

PRESET_WINDOWS = {
    "Default Study Window (Idx 5570)": 5570,
    "Strong Impulse Rally (Idx 12400)": 12400,
    "Corrective Consolidation (Idx 28500)": 28500,
    "Volatile Reversal (Idx 54200)": 54200,
    "Complex Wave Sequence (Idx 81000)": 81000,
}

STRUCTURE_COLORS = {
    ":5": "#38bdf8",    # Sky blue (Impulsive 5)
    ":s5": "#818cf8",   # Indigo (Special 5)
    ":L5": "#10b981",   # Emerald (Terminal Last 5)
    ":F3": "#f59e0b",   # Amber (First 3)
    ":c3": "#f97316",   # Orange (Center 3)
    "x:c3": "#ec4899",  # Pink (X-wave Center 3)
    ":sL3": "#a855f7",  # Purple (Second-to-Last 3)
    ":L3": "#ef4444",   # Red (Terminal Last 3)
}

PLAIN_ENGLISH_LABELS = {
    ":5": ("Trend Impulse", "Strong directional move pushing the main trend forward."),
    ":s5": ("Extended Trend", "High-momentum trend wave (often Wave 3 or part of a complex pattern)."),
    ":L5": ("Pattern End (Wave 5/C)", "Concludes a 5-wave trend or a 3-wave correction — watch for a reversal."),
    ":F3": ("Pullback Start (Wave A)", "First leg of a counter-trend pullback or consolidation."),
    ":c3": ("Consolidation (Wave B)", "Middle corrective wave inside a pullback or triangle."),
    "x:c3": ("Connector Wave (X)", "Links two separate corrective patterns together."),
    ":sL3": ("Triangle Setup (Wave D)", "Second-to-last wave of a narrowing triangle or wedge."),
    ":L3": ("Triangle End (Wave E)", "Final wave of a triangle or terminal pattern — breakout often follows."),
}

RULE_PLAIN_SUMMARY = {
    1: "Shallow pullback (<38.2%) — strong trend continuation",
    2: "Moderate pullback (38.2%–61.8%) — normal trend pause",
    3: "Golden Ratio pullback (~61.8%) — pivotal decision level",
    4: "Deep pullback (61.8%–100%) — corrective / overlapping market",
    5: "Full retracement (100%–161.8%) — prior wave completely reversed",
    6: "Strong breakout (161.8%–261.8%) — powerful expansion wave",
    7: "Extreme thrust (>261.8%) — sharp reversal after a minor pause",
}


@st.cache_data(show_spinner=False)
def load_dataset(path):
    df = pd.read_csv(path)
    if "hl2" not in df.columns and {"high", "low"}.issubset(df.columns):
        df["hl2"] = (df["high"] + df["low"]) / 2.0
    return df


def run_neely_pipeline(df, start_idx, n_steps, price_col, neutrality_angle, fib_tol):
    """Execute the full 5-stage Glenn Neely Elliott Wave analysis on the selected window."""
    sim = simulator.__new__(simulator)
    sim.data_path = DATA_PATH
    sim.dataframe = df
    sim.value = price_col
    sim.enable_file_log = False
    sim.gen_list = []
    sim.gen_time = []
    sim.gen_datetime = []
    sim.init_idx = 0
    sim.data = df[price_col]
    sim(start_idx, value=price_col)

    mon = monowave(neutrality_angle=neutrality_angle, enable_file_log=False)
    idf = identifier(fib_tolerance=fib_tol)

    for _ in range(n_steps):
        p = sim.gen()
        mon.add(p)
        idf.add(p)
        mon.analyze()

    idf.label = mon.label
    idf.monowave = mon.group_monowave
    idf()

    return sim, mon, idf


def generate_layperson_summary(mon, idf):
    """Create a plain-English narrative summarizing what the chart shows."""
    if not mon.price or len(mon.price) < 2:
        return "Not enough price points loaded yet."

    start_p = mon.price[0]
    end_p = mon.price[-1]
    net_change = end_p - start_p
    net_pct = (net_change / start_p) * 100.0
    overall_dir = "upward (bullish)" if net_change >= 0 else "downward (bearish)"

    dir_vals = [v for v in mon.direction.values() if v is not None]
    dir_pct = round(100.0 * sum(1 for v in dir_vals if v == "Dir") / max(1, len(dir_vals)), 1)

    phase_desc = (
        "mostly trending (Directional)"
        if dir_pct >= 55
        else "choppy / consolidating (Sideways & Corrective)"
    )

    last_pat_text = "No completed multi-wave pattern has finished yet in this window."
    if idf.patterns:
        lp = idf.patterns[-1]
        if lp["termination"] == ":L5" and "Impulse" in lp["pattern_type"]:
            pat_plain = "a **5-Wave Trend Impulse**"
            implication = "which signals strong directional momentum that just reached a 5th-wave milestone"
        elif lp["termination"] == ":L5":
            pat_plain = "a **3-Wave Corrective Pullback (Flat/Zigzag)**"
            implication = "which suggests a counter-trend pause completed and the main trend can resume"
        else:
            pat_plain = "a **Contracting Triangle / Terminal Pattern**"
            implication = "which typically precedes a sharp post-triangle breakout"
        last_pat_text = (
            f"Most recently, the model isolated {pat_plain} from **{lp['start_wave']} to {lp['end_wave']}** "
            f"({lp['direction']}), {implication}."
        )

    return (
        f"**Plain-English Summary:** Over these **{len(mon.price)} minutes**, Bitcoin moved **{overall_dir}** "
        f"by **${net_change:+,.2f} ({net_pct:+.2f}%)** (`${start_p:,.2f}` → `${end_p:,.2f}`). "
        f"The algorithm simplified **{len(mon.price)} raw price ticks** into **{len(mon.group_monowave)} major price swings**, "
        f"filtering out **{len(mon.rollbacks)} minor sideways wiggles** along the way. "
        f"Market behavior in this window is **{phase_desc}** ({dir_pct}% directional action). {last_pat_text}"
    )


def build_wave_figure(
    sim,
    mon,
    idf,
    show_raw_price=True,
    show_monowaves=False,
    show_groupwaves=True,
    label_mode="Key Turning Points (Easy to Read)",
    show_patterns=True,
    show_rollbacks=False,
    fib_wave_idx=None,
    dark_mode=True,
):
    """Build the interactive multi-layer Plotly figure with zero title/legend overlap."""
    x_indices = list(range(len(mon.price)))
    x_labels = sim.gen_datetime if len(sim.gen_datetime) == len(mon.price) else x_indices

    fig = go.Figure()

    # 1. Shaded Pattern Isolation Regions (:L5 and :L3 completed patterns)
    if show_patterns and idf.patterns:
        for pat in idf.patterns:
            s_i = pat["start_idx"]
            e_i = pat["end_idx"]
            if 0 <= s_i < len(x_labels) and 0 <= e_i < len(x_labels):
                is_impulse = pat["termination"] == ":L5" and "Impulse" in pat["pattern_type"]
                fill_col = "rgba(16, 185, 129, 0.09)" if is_impulse else "rgba(245, 158, 11, 0.09)"
                border_col = "rgba(16, 185, 129, 0.40)" if is_impulse else "rgba(245, 158, 11, 0.40)"
                short_tag = "5-Wave Trend" if is_impulse else ("3-Wave Pullback" if pat["termination"] == ":L5" else "Triangle/Terminal")
                fig.add_vrect(
                    x0=x_labels[s_i],
                    x1=x_labels[e_i],
                    fillcolor=fill_col,
                    line=dict(color=border_col, width=1, dash="dot"),
                    annotation_text=f"{short_tag} ({pat['start_wave']}→{pat['end_wave']})",
                    annotation_position="bottom left",
                    annotation_font=dict(
                        size=10,
                        color="#10b981" if is_impulse else "#f59e0b",
                    ),
                )

    # 2. Raw Price Series
    if show_raw_price and mon.price:
        fig.add_trace(
            go.Scatter(
                x=x_labels,
                y=mon.price,
                mode="lines",
                name="Raw BTC/USD Price",
                line=dict(
                    color="rgba(148, 163, 184, 0.55)" if dark_mode else "rgba(100, 116, 139, 0.55)",
                    width=1.5,
                ),
                hovertemplate="<b>Minute %{pointNumber}</b><br>Time: %{x}<br>BTC Price: $%{y:,.2f}<extra>Raw Price</extra>",
            )
        )

    # 3. Raw Monowaves (M1, M2, ...)
    if show_monowaves and mon.price:
        m_verts = mon.monowave_vertices()
        if m_verts:
            mx = [x_labels[v[0]] for v in m_verts]
            my = [v[1] for v in m_verts]
            ml = [v[2] for v in m_verts]
            fig.add_trace(
                go.Scatter(
                    x=mx,
                    y=my,
                    mode="lines+markers",
                    name="Small Sub-Waves (Monowaves M1..n)",
                    line=dict(color="#38bdf8", width=1.2, dash="dot"),
                    marker=dict(size=4, color="#38bdf8", symbol="circle-open"),
                    text=ml,
                    hovertemplate="<b>Small Wave %{text}</b><br>Time: %{x}<br>Price: $%{y:,.2f}<extra></extra>",
                )
            )

    # 4. Confirmed Group Waves (Rule of Observation: m1, m2, ...)
    if show_groupwaves and mon.group_monowave:
        gx = [x_labels[0]]
        gy = [mon.price[0]]
        gtext = ["<b>Start of Analysis Window</b>"]
        gcolors = ["#6366f1"]
        gsizes = [8]

        for i in range(len(mon.group_monowave)):
            end_i = mon.group_monowave[i][-1]
            gx.append(x_labels[end_i])
            gy.append(mon.price[end_i])

            if i in idf.details:
                d = idf.details[i]
                p_struct = d["primary_structure"]
                plain_title, plain_explain = PLAIN_ENGLISH_LABELS.get(
                    p_struct, ("Wave Segment", d["structure_meaning"])
                )
                rule_explain = RULE_PLAIN_SUMMARY.get(d["rule"], "")
                gcolors.append(STRUCTURE_COLORS.get(p_struct, "#f43f5e"))
                is_milestone = p_struct in (":L5", ":L3", ":5", ":s5")
                gsizes.append(11 if is_milestone else 8)
                gtext.append(
                    f"<b>Swing {d['wave_name']}: {plain_title}</b><br>"
                    f"What it means: {plain_explain}<br>"
                    f"Next wave retraced: <b>{d['m2_m1_ratio']}%</b> ({rule_explain})<br>"
                    f"Neely Technical Code: Rule <b>{d['rule_code']}</b> → Structure <b>{p_struct}</b>"
                )
            else:
                gcolors.append("#a855f7")
                gsizes.append(8)
                gtext.append(f"<b>Swing m{i + 1}</b> (Still developing — waiting for next wave break)")

        fig.add_trace(
            go.Scatter(
                x=gx,
                y=gy,
                mode="lines+markers",
                name="Major Structural Swings (Neely Group Waves)",
                line=dict(color="#f43f5e" if dark_mode else "#e11d48", width=2.8),
                marker=dict(
                    size=gsizes,
                    color=gcolors,
                    line=dict(width=1.5, color="#ffffff" if dark_mode else "#0f172a"),
                ),
                text=gtext,
                hovertemplate="%{text}<br>Time: %{x}<br>Price: $%{y:,.2f}<extra></extra>",
            )
        )

    # 5. Rule of Neutrality Rollbacks (< 45 deg absorbed turns)
    if show_rollbacks and mon.rollbacks:
        rx = [x_labels[r["index"]] for r in mon.rollbacks if r["index"] < len(x_labels)]
        ry = [r["price"] for r in mon.rollbacks if r["index"] < len(x_labels)]
        rtxt = [
            f"Filtered sideways wiggle ({r['angle']}° < {mon.neutrality_angle}° threshold)"
            for r in mon.rollbacks
            if r["index"] < len(x_labels)
        ]
        fig.add_trace(
            go.Scatter(
                x=rx,
                y=ry,
                mode="markers",
                name="Filtered Sideways Noise (<45°)",
                marker=dict(size=9, color="#eab308", symbol="diamond", line=dict(width=1, color="#000")),
                text=rtxt,
                hovertemplate="<b>Filtered Noise (Rule of Neutrality)</b><br>%{text}<br>Price: $%{y:,.2f}<extra></extra>",
            )
        )

    # 6. Wave Annotations
    if label_mode != "Hide Labels" and mon.group_monowave:
        pattern_ends = {p["end_wave"] for p in idf.patterns}
        pattern_starts = {p["start_wave"] for p in idf.patterns}

        for i in range(len(mon.group_monowave)):
            w_name = f"m{i + 1}"
            m_idx = mon.group_monowave[i][-1]
            prev_idx = mon.group_monowave[0][0] if i == 0 else mon.group_monowave[i - 1][-1]
            is_peak = mon.price[m_idx] >= mon.price[prev_idx]
            y_shift = 18 if is_peak else -18

            d = idf.details.get(i)
            p_struct = d["primary_structure"] if d else ""
            plain_short, _ = PLAIN_ENGLISH_LABELS.get(p_struct, ("Wave", ""))

            # In "Key Turning Points" mode, only show labels on major milestones (:L5, :L3, :5, :s5, pattern starts/ends)
            if label_mode == "Key Turning Points (Easy to Read)":
                is_key = (
                    w_name in pattern_ends
                    or w_name in pattern_starts
                    or p_struct in (":L5", ":L3", ":5", ":s5")
                )
                if not is_key:
                    continue
                badge_color = STRUCTURE_COLORS.get(p_struct, "#38bdf8")
                short_tag = (
                    "Trend (:5)"
                    if p_struct in (":5", ":s5")
                    else (
                        "Pattern End (:L5)"
                        if p_struct == ":L5"
                        else (
                            "Triangle End (:L3)"
                            if p_struct == ":L3"
                            else f"Pullback ({p_struct})"
                        )
                    )
                )
                label_text = f"<b>{w_name}: {short_tag}</b>"
            elif label_mode == "All Waves (Plain English)":
                badge_color = STRUCTURE_COLORS.get(p_struct, "#94a3b8")
                label_text = f"<b>{w_name}</b> {plain_short.split(' (')[0]}" if d else f"<b>{w_name}</b>"
            else:  # Technical Neely Codes
                badge_color = STRUCTURE_COLORS.get(p_struct, "#94a3b8")
                label_text = f"<b>{w_name}</b> [{d['rule_code']}{p_struct}]" if d else f"<b>{w_name}</b>"

            fig.add_annotation(
                x=x_labels[m_idx],
                y=mon.price[m_idx],
                text=label_text,
                yshift=y_shift,
                showarrow=False,
                font=dict(size=10.5, color=badge_color),
                bgcolor="rgba(15, 23, 42, 0.85)" if dark_mode else "rgba(255, 255, 255, 0.92)",
                bordercolor=badge_color,
                borderwidth=1,
                borderpad=3,
            )

    # 7. Optional Fibonacci Retracement Levels for a selected Group Wave m_k
    if fib_wave_idx is not None and fib_wave_idx in idf.details:
        d = idf.details[fib_wave_idx]
        p_start = d["start_price"]
        p_end = d["end_price"]
        diff = p_end - p_start
        fib_ratios = [
            (0.0, "0.0% (Wave End)"),
            (0.382, "38.2% (Shallow Support/Resistance)"),
            (0.618, "61.8% (Golden Ratio Pivot)"),
            (1.000, "100.0% (Full Retracement)"),
            (1.618, "161.8% (Fibonacci Extension)"),
        ]
        for r_val, r_name in fib_ratios:
            lvl_price = p_end - diff * r_val
            fig.add_hline(
                y=lvl_price,
                line=dict(color="rgba(56, 189, 248, 0.45)", width=1, dash="dash"),
                annotation_text=f"{d['wave_name']} {r_name}: ${lvl_price:,.1f}",
                annotation_position="bottom right",
                annotation_font=dict(size=10, color="#38bdf8"),
            )

    # Place legend cleanly BELOW the chart so it NEVER overlaps the title or top annotations
    fig.update_layout(
        template="plotly_dark" if dark_mode else "plotly_white",
        height=560,
        margin=dict(l=20, r=20, t=55, b=85),
        title=dict(
            text=(
                f"BTC/USD Structural Wave Map — Start Idx {sim.init_idx:,} "
                f"({len(mon.price)} Minutes | {len(mon.group_monowave)} Major Swings | "
                f"{len(idf.patterns)} Completed Patterns)"
            ),
            y=0.96,
            x=0.01,
            xanchor="left",
            yanchor="top",
            font=dict(size=15),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.14,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        xaxis=dict(title="Time (UTC)", showgrid=True),
        yaxis=dict(title="BTC / USD Price ($)", showgrid=True, tickprefix="$"),
        hovermode="closest",
    )

    return fig


def render_streamlit_app():
    st.set_page_config(
        page_title="Neely Elliott Wave Modeling | Changhee Han",
        page_icon="📈",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background-color: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.2);
            padding: 10px 14px;
            border-radius: 12px;
        }
        .color-pill {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 4px;
            color: #fff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    df = load_dataset(DATA_PATH)
    max_start_idx = max(0, len(df) - 500)

    if "start_idx" not in st.session_state:
        st.session_state.start_idx = 5570
    if "n_steps" not in st.session_state:
        st.session_state.n_steps = 90

    # ==================== SIDEBAR CONTROLS ====================
    with st.sidebar:
        st.title("⚙️ Wave Analyzer Controls")
        st.caption("Objective implementation of Glenn Neely's *Mastering Elliott Wave*")

        preset_choice = st.selectbox(
            "1️⃣ Choose a Market Scenario",
            options=["Custom Start Index"] + list(PRESET_WINDOWS.keys()),
            index=1,
        )
        if preset_choice != "Custom Start Index":
            st.session_state.start_idx = PRESET_WINDOWS[preset_choice]

        col_s1, col_s2 = st.columns([3, 2])
        with col_s1:
            start_idx = st.number_input(
                "Start Candle Index",
                min_value=0,
                max_value=max_start_idx,
                value=int(st.session_state.start_idx),
                step=10,
            )
            st.session_state.start_idx = start_idx
        with col_s2:
            st.write("")
            st.write("")
            if st.button("🎲 Random", use_container_width=True):
                st.session_state.start_idx = int(np.random.randint(0, max_start_idx))
                st.rerun()

        n_steps = st.slider(
            "2️⃣ Time Window (Minutes Analyzed)",
            min_value=20,
            max_value=250,
            value=int(st.session_state.n_steps),
            step=5,
        )
        st.session_state.n_steps = n_steps

        st.markdown("**Step-by-Step Playback**")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("⏮ 25", help="Reset window to 25 minutes", use_container_width=True):
                st.session_state.n_steps = 25
                st.rerun()
        with b2:
            if st.button("➕ +1", help="Advance 1 minute", use_container_width=True):
                st.session_state.n_steps = min(250, st.session_state.n_steps + 1)
                st.rerun()
        with b3:
            if st.button("⏩ +10", help="Advance 10 minutes", use_container_width=True):
                st.session_state.n_steps = min(250, st.session_state.n_steps + 10)
                st.rerun()

        auto_play = st.toggle("▶ Watch Waves Form Live", value=False)

        st.divider()
        st.subheader("🎨 Chart Readability")
        label_mode = st.selectbox(
            "Wave Label Style",
            options=[
                "Key Turning Points (Easy to Read)",
                "All Waves (Plain English)",
                "All Waves (Technical Neely Codes)",
                "Hide Labels",
            ],
            index=0,
            help="Choose how much detail to display directly on the chart.",
        )
        dark_mode = st.toggle("Dark Theme", value=True)
        show_raw_price = st.checkbox("Show Raw BTC/USD Price", value=True)
        show_groupwaves = st.checkbox("Show Major Structural Swings", value=True)
        show_patterns = st.checkbox("Highlight Completed Pattern Zones", value=True)
        show_monowaves = st.checkbox("Show Tiny Sub-Waves (M1..n)", value=False)
        show_rollbacks = st.checkbox("Show Filtered Noise (<45°)", value=False)

        with st.expander("⚙️ Advanced Neely Parameters"):
            price_col = st.selectbox(
                "Price Series Type",
                options=["open", "hl2", "close", "high", "low"],
                index=0,
                format_func=lambda x: "hl2 ((High+Low)/2 — Neely Cash Avg)" if x == "hl2" else x.upper(),
            )
            neutrality_angle = st.slider(
                "Noise Filter Angle (Rule of Neutrality °)",
                min_value=0.0,
                max_value=60.0,
                value=45.0,
                step=5.0,
            )
            fib_tol_pct = st.slider(
                "Fibonacci Ratio Leeway (%)",
                min_value=0.5,
                max_value=5.0,
                value=2.0,
                step=0.5,
            )

    # ==================== RUN ENGINE ====================
    sim, mon, idf = run_neely_pipeline(
        df=df,
        start_idx=st.session_state.start_idx,
        n_steps=st.session_state.n_steps,
        price_col=price_col,
        neutrality_angle=neutrality_angle,
        fib_tol=fib_tol_pct / 100.0,
    )

    # ==================== HEADER & BENEFITS OVERVIEW ====================
    st.title("📈 Elliott Wave Structural Analyzer")
    st.markdown(
        "**Turning noisy price charts into clear market structure** — based on Glenn Neely's "
        "*Mastering Elliott Wave*."
    )

    with st.expander("💡 New to Elliott Wave? Click here to see how to read this chart & why it matters", expanded=False):
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            st.markdown(
                """
                ### What Is Elliott Wave Modeling?
                Financial markets do not move in straight lines—they alternate between **Trends (Impulses)** that push prices forward and **Pullbacks (Corrections)** where prices pause or retrace.
                
                **Why Glenn Neely's Method?**  
                Traditional chart reading is often subjective. Glenn Neely created a strict, mathematical rulebook using **Fibonacci ratios (`38.2%`, `61.8%`, `100%`, `161.8%`)** and **price-time geometry** so wave detection is 100% objective and repeatable.
                """
            )
        with b_col2:
            st.markdown(
                """
                ### 4 Key Benefits of This Model
                1. **Filters Out Market Noise:** Automatically ignores minor sideways wiggles (`<45°`) and groups raw minute-by-minute ticks into meaningful **Major Swings (`m1, m2, ...`)**.
                2. **Separates Trend from Pullback:** Distinguishes strong **Trend Impulses (`:5`)** from temporary **Counter-Trend Pullbacks (`:F3`, `:c3`)**.
                3. **Spots Trend Exhaustion Early:** Flags **Pattern Endings (`:L5` and `:L3`)** when a 5-wave trend, 3-wave correction, or triangle has completed.
                4. **Objective Fibonacci Targets:** Measures exact retracement percentages between adjacent waves (`|m2/m1|` and `|m0/m1|`).
                """
            )

    # ==================== PLAIN-ENGLISH SUMMARY BANNER ====================
    st.info(generate_layperson_summary(mon, idf))

    # ==================== KPI METRICS ====================
    dir_vals = [v for v in mon.direction.values() if v is not None]
    dir_pct = round(100.0 * sum(1 for v in dir_vals if v == "Dir") / max(1, len(dir_vals)), 1)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("1. Raw Price Ticks", f"{len(mon.price)} mins", f"Start Idx {sim.init_idx:,}")
    m2.metric("2. Noise Filtered", f"{len(mon.rollbacks)} wiggles", f"Under {neutrality_angle:.0f}° angle")
    m3.metric("3. Major Swings Found", f"{len(mon.group_monowave)} waves", f"Simplified from {len(mon.log_label)} sub-waves")
    m4.metric("4. Trend Strength", f"{dir_pct}%", "Directional (<61.8% pullback)")
    m5.metric("5. Completed Patterns", f"{len(idf.patterns)}", "5-Wave Trends & 3-Wave Pullbacks")

    # ==================== VISUAL COLOR KEY ====================
    st.markdown(
        """
        <div style="margin: 6px 0 4px 0;">
            <span style="font-size:0.82rem; font-weight:600; margin-right:8px;">Chart Color Key:</span>
            <span class="color-pill" style="background:#38bdf8;">🔵 Trend Impulse (:5 / :s5)</span>
            <span class="color-pill" style="background:#f59e0b;">🟠 Pullback / Consolidation (:F3 / :c3)</span>
            <span class="color-pill" style="background:#10b981;">🟢 Pattern End — Wave 5 or C (:L5)</span>
            <span class="color-pill" style="background:#ef4444;">🔴 Triangle / Wedge End (:L3)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ==================== MAIN PLOTLY CHART ====================
    wave_options = {"None (Hide Fibonacci Retracement Lines)": None}
    for k, d in idf.details.items():
        plain_t, _ = PLAIN_ENGLISH_LABELS.get(d["primary_structure"], ("Wave", ""))
        wave_options[f"{d['wave_name']} — {plain_t} [Rule {d['rule_code']} {d['primary_structure']}]"] = k

    selected_fib_label = st.selectbox(
        "📐 Optional: Overlay Fibonacci Support/Resistance Levels for a Specific Swing:",
        options=list(wave_options.keys()),
        index=0,
    )
    fib_wave_idx = wave_options[selected_fib_label]

    fig = build_wave_figure(
        sim=sim,
        mon=mon,
        idf=idf,
        show_raw_price=show_raw_price,
        show_monowaves=show_monowaves,
        show_groupwaves=show_groupwaves,
        label_mode=label_mode,
        show_patterns=show_patterns,
        show_rollbacks=show_rollbacks,
        fib_wave_idx=fib_wave_idx,
        dark_mode=dark_mode,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==================== ANALYTICAL TABS ====================
    tab1, tab2, tab3 = st.tabs(
        [
            "🎯 Completed Elliott Wave Patterns (Easy View)",
            "📋 Detailed Swing-by-Swing Table",
            "📖 How the 5-Stage Neely Algorithm Works",
        ]
    )

    with tab1:
        if idf.patterns:
            st.markdown(
                "Below are the **complete multi-wave patterns** automatically detected in this window. "
                "When a pattern reaches its final wave (`:L5` or `:L3`), the current move is exhausted and a reversal or breakout typically follows:"
            )
            for pat in idf.patterns:
                is_imp = pat["termination"] == ":L5" and "Impulse" in pat["pattern_type"]
                icon = "🚀" if is_imp else ("🔄" if pat["termination"] == ":L5" else "📐")
                plain_type = (
                    "5-Wave Trend Impulse (Strong Directional Move)"
                    if is_imp
                    else (
                        "3-Wave Corrective Pullback (Temporary Counter-Trend Pause)"
                        if pat["termination"] == ":L5"
                        else "5-Wave Triangle / Wedge Consolidation (Pre-Breakout Compression)"
                    )
                )
                st.markdown(
                    f"**{icon} {pat['start_wave']} → {pat['end_wave']} | {plain_type} — {pat['direction']}**  \n"
                    f"- **Price Span:** `${pat['start_price']:,.2f}` → `${pat['end_price']:,.2f}` (Ticks `{pat['start_idx']}` to `{pat['end_idx']}`)  \n"
                    f"- **Wave Sequence:** `{pat['sequence']}`"
                )
                st.divider()
        else:
            st.info("No completed patterns in this range yet — try increasing the Time Window slider on the left.")

    with tab2:
        if idf.details:
            rows = []
            for k, d in idf.details.items():
                plain_name, plain_desc = PLAIN_ENGLISH_LABELS.get(
                    d["primary_structure"], ("Wave", d["structure_meaning"])
                )
                rows.append(
                    {
                        "Swing": d["wave_name"],
                        "Role (Plain English)": plain_name,
                        "Price Move ($)": f"${d['start_price']:,.2f} → ${d['end_price']:,.2f}",
                        "Next Wave Retraced (|m2/m1|)": f"{d['m2_m1_ratio']}%",
                        "Prior Wave Ratio (|m0/m1|)": f"{d['m0_m1_ratio']}%",
                        "Neely Rule": d["rule_code"],
                        "Structure Code": d["primary_structure"],
                        "What It Means": plain_desc,
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.warning("Increase the Time Window slider so at least 3 major swings form.")

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                """
                ### Stages 1–3: Cleaning & Filtering Raw Prices
                1. **Step 1 — Raw Monowaves (`M1, M2, ...`, Book p. 3-2)**  
                   Every time price changes direction (even for 1 minute), it creates a basic building block called a *Monowave*.
                2. **Step 2 — Rule of Proportion (Book pp. 3-3 to 3-8)**  
                   Checks whether pullbacks are **shallow (`<61.8%`, Directional Trend)** or **deep (`>61.8%`, Sideways Consolidation)**.
                3. **Step 3 — Rule of Neutrality (Book pp. 3-9 to 3-13)**  
                   If a price turn is flatter than **45°** (moving sideways rather than up/down), the algorithm absorbs it as noise instead of counting a false wave.
                """
            )
        with c2:
            st.markdown(
                """
                ### Stages 4–5: Grouping Swings & Naming Patterns
                4. **Step 4 — Rules of Observation (Book pp. 3-14 to 3-21)**  
                   Small internal waves are grouped together until price breaks above the prior swing high or below the prior swing low, producing clean **Major Swings (`m1, m2, ...`)**.
                5. **Step 5 — Fibonacci Rules (1–7) & Structure Labels (pp. 3-22 to 3-67)**  
                   Measures how much each swing is retraced by the next (`|m2/m1|`) to assign a **Structure Role**:
                   - **`:5` / `:s5` (Impulse):** Trend continuation
                   - **`:F3` / `:c3` (Corrective):** Counter-trend pullback
                   - **`:L5` / `:L3` (Terminal):** End of a 5-wave trend, 3-wave pullback, or triangle.
                """
            )

    if auto_play and st.session_state.n_steps < 250:
        time.sleep(0.4)
        st.session_state.n_steps += 1
        st.rerun()


if __name__ == "__main__":
    render_streamlit_app()
