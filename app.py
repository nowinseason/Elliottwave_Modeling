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


def build_wave_figure(
    sim,
    mon,
    idf,
    show_raw_price=True,
    show_monowaves=True,
    show_groupwaves=True,
    show_annotations=True,
    show_patterns=True,
    show_rollbacks=True,
    fib_wave_idx=None,
    dark_mode=True,
):
    """Build the interactive multi-layer Plotly figure for Neely Elliott Wave analysis."""
    x_indices = list(range(len(mon.price)))
    x_labels = sim.gen_datetime if len(sim.gen_datetime) == len(mon.price) else x_indices

    fig = go.Figure()

    # 1. Shaded Pattern Isolation Regions (:L5 and :L3 completed patterns)
    if show_patterns and idf.patterns:
        for i, pat in enumerate(idf.patterns):
            s_i = pat["start_idx"]
            e_i = pat["end_idx"]
            if 0 <= s_i < len(x_labels) and 0 <= e_i < len(x_labels):
                is_impulse = pat["termination"] == ":L5" and "Impulse" in pat["pattern_type"]
                fill_col = "rgba(16, 185, 129, 0.08)" if is_impulse else "rgba(245, 158, 11, 0.08)"
                border_col = "rgba(16, 185, 129, 0.35)" if is_impulse else "rgba(245, 158, 11, 0.35)"
                fig.add_vrect(
                    x0=x_labels[s_i],
                    x1=x_labels[e_i],
                    fillcolor=fill_col,
                    line=dict(color=border_col, width=1, dash="dot"),
                    annotation_text=f"{pat['start_wave']}→{pat['end_wave']} ({pat['termination']})",
                    annotation_position="top left",
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
                name="BTC/USD Price",
                line=dict(
                    color="#64748b" if dark_mode else "#94a3b8",
                    width=1.4,
                ),
                hovertemplate="<b>Tick %{pointNumber}</b><br>Time: %{x}<br>Price: $%{y:,.2f}<extra>Raw Price</extra>",
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
                    name="Monowaves (M1..Mn)",
                    line=dict(color="#38bdf8", width=1.3, dash="dot"),
                    marker=dict(size=5, color="#38bdf8", symbol="circle-open"),
                    text=ml,
                    hovertemplate="<b>Monowave %{text}</b><br>Time: %{x}<br>Price: $%{y:,.2f}<extra>Monowave</extra>",
                )
            )

    # 4. Confirmed Group Waves (Rule of Observation: m1, m2, ...)
    if show_groupwaves and mon.group_monowave:
        gx = [x_labels[0]]
        gy = [mon.price[0]]
        gtext = ["Start (m0 origin)"]
        gcolors = ["#6366f1"]

        for i in range(len(mon.group_monowave)):
            end_i = mon.group_monowave[i][-1]
            gx.append(x_labels[end_i])
            gy.append(mon.price[end_i])

            if i in idf.details:
                d = idf.details[i]
                p_struct = d["primary_structure"]
                s_list = "/".join(d["structures"])
                gcolors.append(STRUCTURE_COLORS.get(p_struct, "#f43f5e"))
                gtext.append(
                    f"<b>{d['wave_name']}</b> | Rule <b>{d['rule_code']}</b> → <b>{p_struct}</b><br>"
                    f"Candidates: {{{s_list}}}<br>"
                    f"|m2/m1| Retracement: {d['m2_m1_ratio']}%<br>"
                    f"|m0/m1| Proportion: {d['m0_m1_ratio']}%<br>"
                    f"{d['structure_meaning']}"
                )
            else:
                gcolors.append("#a855f7")
                gtext.append(f"<b>m{i + 1}</b> (Developing surrounding context)")

        fig.add_trace(
            go.Scatter(
                x=gx,
                y=gy,
                mode="lines+markers",
                name="Group Waves (Rule of Observation)",
                line=dict(color="#f43f5e" if dark_mode else "#e11d48", width=2.8),
                marker=dict(
                    size=9,
                    color=gcolors,
                    line=dict(width=1.5, color="#ffffff" if dark_mode else "#0f172a"),
                ),
                text=gtext,
                hovertemplate="%{text}<br>Time: %{x}<br>Price: $%{y:,.2f}<extra>Group Wave</extra>",
            )
        )

    # 5. Rule of Neutrality Rollbacks (< 45 deg absorbed turns)
    if show_rollbacks and mon.rollbacks:
        rx = [x_labels[r["index"]] for r in mon.rollbacks if r["index"] < len(x_labels)]
        ry = [r["price"] for r in mon.rollbacks if r["index"] < len(x_labels)]
        rtxt = [
            f"Rolled back {r['rolled_back_label']} (Angle: {r['angle']}° < {mon.neutrality_angle}°)"
            for r in mon.rollbacks
            if r["index"] < len(x_labels)
        ]
        fig.add_trace(
            go.Scatter(
                x=rx,
                y=ry,
                mode="markers",
                name="Rule of Neutrality Rollback (<45°)",
                marker=dict(size=9, color="#eab308", symbol="diamond", line=dict(width=1, color="#000")),
                text=rtxt,
                hovertemplate="<b>Neutrality Rollback</b><br>%{text}<br>Price: $%{y:,.2f}<extra></extra>",
            )
        )

    # 6. Wave Annotations (m1, m2... + Neely Rule & Structure Label)
    if show_annotations and mon.group_monowave:
        for i in range(len(mon.group_monowave)):
            m_idx = mon.group_monowave[i][-1]
            prev_idx = mon.group_monowave[0][0] if i == 0 else mon.group_monowave[i - 1][-1]
            is_peak = mon.price[m_idx] >= mon.price[prev_idx]
            y_shift = 16 if is_peak else -16

            if i in idf.details:
                d = idf.details[i]
                p_struct = d["primary_structure"]
                badge_color = STRUCTURE_COLORS.get(p_struct, "#f43f5e")
                label_text = f"<b>m{i + 1}</b> [{d['rule_code']}{p_struct}]"
                hover_txt = (
                    f"Wave m{i + 1}: Rule {d['rule_code']} | Structure { d['structures'] } "
                    f"| m2/m1={d['m2_m1_ratio']}%, m0/m1={d['m0_m1_ratio']}%"
                )
            else:
                badge_color = "#94a3b8"
                label_text = f"<b>m{i + 1}</b>"
                hover_txt = f"Wave m{i + 1} (Awaiting subsequent wave confirmation)"

            fig.add_annotation(
                x=x_labels[m_idx],
                y=mon.price[m_idx],
                text=label_text,
                yshift=y_shift,
                showarrow=False,
                font=dict(size=11, color=badge_color),
                bgcolor="rgba(15, 23, 42, 0.80)" if dark_mode else "rgba(255, 255, 255, 0.88)",
                bordercolor=badge_color,
                borderwidth=1,
                borderpad=2,
                hovertext=hover_txt,
            )

    # 7. Optional Fibonacci Retracement Levels for a selected Group Wave m_k
    if fib_wave_idx is not None and fib_wave_idx in idf.details:
        d = idf.details[fib_wave_idx]
        p_start = d["start_price"]
        p_end = d["end_price"]
        diff = p_end - p_start
        fib_ratios = [
            (0.0, "0.0% (m1 End)"),
            (0.382, "38.2% (Rule 1/2)"),
            (0.618, "61.8% (Rule 3 Proportion)"),
            (1.000, "100.0% (Rule 4/5)"),
            (1.618, "161.8% (Rule 5/6)"),
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

    fig.update_layout(
        template="plotly_dark" if dark_mode else "plotly_white",
        height=580,
        margin=dict(l=20, r=20, t=45, b=20),
        title=dict(
            text=(
                f"Glenn Neely Elliott Wave Structural Analysis — BTC/USD "
                f"(Start Idx: {sim.init_idx:,} | {len(mon.price)} Ticks | "
                f"{len(mon.group_monowave)} Group Waves)"
            ),
            font=dict(size=16),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
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
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background-color: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.2);
            padding: 12px 16px;
            border-radius: 12px;
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
        st.session_state.n_steps = 100

    # ==================== SIDEBAR CONTROLS ====================
    with st.sidebar:
        st.title("⚙️ Wave Engine Controls")
        st.caption("Based on Glenn Neely's *Mastering Elliott Wave* (Version 2.0, Chapter 3)")

        preset_choice = st.selectbox(
            "Preset Market Window",
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

        price_col = st.selectbox(
            "Price Series Type (Ch. 2, p. 2-10)",
            options=["open", "hl2", "close", "high", "low"],
            index=0,
            format_func=lambda x: "hl2 ((High+Low)/2 — Neely Cash Avg)" if x == "hl2" else x.upper(),
        )

        n_steps = st.slider(
            "Simulation Window Size (Candles)",
            min_value=15,
            max_value=300,
            value=int(st.session_state.n_steps),
            step=5,
        )
        st.session_state.n_steps = n_steps

        # Step-by-step playback buttons
        st.markdown("**Step-by-Step Playback**")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("⏮ 25", help="Reset window to 25 ticks", use_container_width=True):
                st.session_state.n_steps = 25
                st.rerun()
        with b2:
            if st.button("➕ +1", help="Advance 1 tick", use_container_width=True):
                st.session_state.n_steps = min(300, st.session_state.n_steps + 1)
                st.rerun()
        with b3:
            if st.button("⏩ +10", help="Advance 10 ticks", use_container_width=True):
                st.session_state.n_steps = min(300, st.session_state.n_steps + 10)
                st.rerun()

        auto_play = st.toggle("▶ Live Tick-by-Tick Simulation", value=False)

        st.divider()
        st.subheader("📐 Neely Rule Parameters")
        neutrality_angle = st.slider(
            "Rule of Neutrality Threshold (°)",
            min_value=0.0,
            max_value=60.0,
            value=45.0,
            step=5.0,
            help="Turns shallower than this angle (default 45°, Fig. 3-14a/b) are rolled back into the current monowave.",
        )
        fib_tol_pct = st.slider(
            "Fibonacci Ratio Leeway (%)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            help="Neely's leeway around exact 61.8% / 161.8% ratios (p. 3-34).",
        )

        st.divider()
        st.subheader("🎨 Visualization Layers")
        dark_mode = st.toggle("Dark Financial Theme", value=True)
        show_raw_price = st.checkbox("Raw BTC/USD Price", value=True)
        show_monowaves = st.checkbox("Raw Monowaves (M1..Mn)", value=True)
        show_groupwaves = st.checkbox("Confirmed Group Waves (m1..mk)", value=True)
        show_annotations = st.checkbox("Rule & Structure Labels", value=True)
        show_patterns = st.checkbox("Isolated Elliott Pattern Zones", value=True)
        show_rollbacks = st.checkbox("Neutrality Rollbacks (<45°)", value=True)

    # ==================== RUN ENGINE ====================
    sim, mon, idf = run_neely_pipeline(
        df=df,
        start_idx=st.session_state.start_idx,
        n_steps=st.session_state.n_steps,
        price_col=price_col,
        neutrality_angle=neutrality_angle,
        fib_tol=fib_tol_pct / 100.0,
    )

    # ==================== HEADER ====================
    st.title("📈 Elliott Wave Structural Modeling (Glenn Neely Method)")
    st.markdown(
        "Algorithmic implementation of **Glenn Neely's *Mastering Elliott Wave* (Chapter 3)**: "
        "**Monowave Identification** → **Rule of Proportion** → **Rule of Neutrality** → "
        "**Rules of Observation** → **Retracement Rules (1–7)** & **Pre-Constructive Structure Labeling**."
    )

    # ==================== KPI METRICS ====================
    dir_vals = [v for v in mon.direction.values() if v is not None]
    dir_pct = round(100.0 * sum(1 for v in dir_vals if v == "Dir") / max(1, len(dir_vals)), 1)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Candles Analyzed", f"{len(mon.price)}", f"Idx {sim.init_idx:,}")
    m2.metric("Raw Monowaves", f"{len(mon.log_label)}", f"M1 → M{len(mon.log_label)}")
    m3.metric("Neutrality Rollbacks", f"{len(mon.rollbacks)}", f"< {neutrality_angle:.0f}° filtered")
    m4.metric("Group Waves (m_k)", f"{len(mon.group_monowave)}", "Rule of Observation")
    m5.metric("Directional Action", f"{dir_pct}%", "Rule of Proportion")
    m6.metric("Isolated Patterns", f"{len(idf.patterns)}", ":L5 & :L3 Terminations")

    # Optional Fibonacci wave selector above chart
    wave_options = {"None (Hide Fibonacci Levels)": None}
    for k, d in idf.details.items():
        wave_options[f"{d['wave_name']} — Rule {d['rule_code']} ({d['primary_structure']})"] = k

    fib_col1, fib_col2 = st.columns([2, 5])
    with fib_col1:
        selected_fib_label = st.selectbox(
            "🔍 Inspect Fibonacci Retracement Levels for Wave:",
            options=list(wave_options.keys()),
            index=0,
        )
        fib_wave_idx = wave_options[selected_fib_label]
    with fib_col2:
        if fib_wave_idx is not None:
            d = idf.details[fib_wave_idx]
            st.info(
                f"**{d['wave_name']}** (`${d['start_price']:,.2f}` → `${d['end_price']:,.2f}`) | "
                f"**Rule {d['rule_code']}** | **|m2/m1| = {d['m2_m1_ratio']}%**, **|m0/m1| = {d['m0_m1_ratio']}%** | "
                f"**Primary Structure:** `{d['primary_structure']}` — {d['structure_meaning']}"
            )

    # ==================== MAIN PLOTLY CHART ====================
    fig = build_wave_figure(
        sim=sim,
        mon=mon,
        idf=idf,
        show_raw_price=show_raw_price,
        show_monowaves=show_monowaves,
        show_groupwaves=show_groupwaves,
        show_annotations=show_annotations,
        show_patterns=show_patterns,
        show_rollbacks=show_rollbacks,
        fib_wave_idx=fib_wave_idx,
        dark_mode=dark_mode,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==================== ANALYTICAL TABS ====================
    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Wave-by-Wave Retracement & Structure Table",
            "🎯 Isolated Elliott Wave Patterns (:L5 / :L3)",
            "📖 Neely Chapter 3 Methodology Reference",
        ]
    )

    with tab1:
        if idf.details:
            rows = []
            for k, d in idf.details.items():
                rows.append(
                    {
                        "Group Wave": d["wave_name"],
                        "Start Tick": d["start_idx"],
                        "End Tick": d["end_idx"],
                        "Start Price ($)": f"${d['start_price']:,.2f}",
                        "End Price ($)": f"${d['end_price']:,.2f}",
                        "|m2/m1| Retracement (%)": f"{d['m2_m1_ratio']}%",
                        "|m0/m1| Proportion (%)": f"{d['m0_m1_ratio']}%",
                        "|m3/m2| Category (%)": f"{d['m3_m2_ratio']}%" if d["m3_m2_ratio"] is not None else "—",
                        "Rule Code": d["rule_code"],
                        "Primary Structure": d["primary_structure"],
                        "Candidate Structures": "{ " + " / ".join(d["structures"]) + " }",
                        "Neely Interpretation": d["structure_meaning"],
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.warning("Increase the simulation window size so at least 3 confirmed Group Waves form.")

    with tab2:
        if idf.patterns:
            st.markdown(
                "Completed Elliott Wave sequences identified via **Neely's Pattern Isolation Procedures** "
                "(Chapter 3, pp. 3-64 to 3-67, Figures 3-31 to 3-35) by forward-searching for `:L5` and `:L3` "
                "terminations and backward-tracing 3 or 5 waves to the pattern origin:"
            )
            st.dataframe(pd.DataFrame(idf.patterns), use_container_width=True, hide_index=True)
        else:
            st.info("No `:L5` or `:L3` pattern terminations isolated in the current window yet.")

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                """
                ### Stages 1–3: Chart Preparation & Filtering
                1. **Identification of Monowaves (`mono_indexing`, p. 3-2)**  
                   Every single directional price segment from one change in direction to the next is indexed chronologically (`M1, M2, M3, ...`).
                2. **Rule of Proportion (`rule_of_proportion`, pp. 3-3 to 3-8)**  
                   Evaluates the price-time progression angle against a 45° diagonal square (±25% perimeter deviation) and classifies price action into:
                   - **Directional (`Dir`)**: Retracements `< 61.8%`
                   - **Non-Directional (`Non-Dir`)**: Retracements `> 61.8%`
                3. **Rule of Neutrality (`rule_of_neurality`, pp. 3-9 to 3-13)**  
                   When price changes direction at an angle shallower than **45°** (moving more horizontally than vertically), the turn is rolled back into the ongoing monowave.
                """
            )
        with c2:
            st.markdown(
                """
                ### Stages 4–5: Observation, Retracement & Structure
                4. **Rules of Observation (`rule_of_observation`, pp. 3-14 to 3-21)**  
                   Consolidates interior monowaves (`mg0, mg2`) until either the **high** or **low** of `m1` is exceeded, confirming the terminal points of Group Waves (`m1, m2, ...`).
                5. **Retracement Rules 1–7 & Structure Labeling (pp. 3-22 to 3-67)**  
                   - **Rule (1–7)** from `|m2| / |m1|`: `<38.2%` (R1), `38.2–61.8%` (R2), `~61.8%` (R3), `61.8–100%` (R4), `100–161.8%` (R5), `161.8–261.8%` (R6), `>261.8%` (R7).
                   - **Condition (`a`–`f`)** from `|m0| / |m1|` and **Category (`i`–`iii`)** from `|m3| / |m2|`.
                   - **Pre-Constructive Rules of Logic** transform `(Rule, Condition)` into Structure Labels (`:5`, `:s5`, `:L5`, `:F3`, `:c3`, `x:c3`, `:sL3`, `:L3`).
                """
            )

    if auto_play and st.session_state.n_steps < 300:
        time.sleep(0.4)
        st.session_state.n_steps += 1
        st.rerun()


if __name__ == "__main__":
    render_streamlit_app()

