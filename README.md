# Elliott Wave Structural Modeling (Glenn Neely Method)

An algorithmic Python implementation and interactive **Streamlit + Plotly** visualization of **Glenn Neely's *Mastering Elliott Wave* (Version 2.0, Chapter 3: Preliminary Analysis)**.

## Overview & 5-Stage Pipeline

Unlike subjective chart-pattern guessing, Glenn Neely's method formalizes Elliott Wave analysis into a strict, sequential deductive pipeline:

1. **Monowave Identification (`models/wave_detector.py` — `mono_indexing`)**  
   Tracks every single directional price movement from one change in price direction to the next (`M1, M2, M3, ...`).
2. **Rule of Proportion (`models/wave_detector.py` — `rule_of_proportion`)**  
   Evaluates price-time progression angles against a 45° diagonal square (±25% perimeter deviation) and classifies market action into **Directional (`Dir`, retracement `< 61.8%`)** vs. **Non-Directional (`Non-Dir`, retracement `> 61.8%`)**.
3. **Rule of Neutrality (`models/wave_detector.py` — `rule_of_neurality`)**  
   Filters horizontal noise: when a change in price direction progresses at an angle shallower than **45°** to the horizontal axis, the turn is rolled back into the ongoing monowave.
4. **Rules of Observation & Wave Grouping (`models/wave_detector.py` — `rule_of_observation`)**  
   Consolidates interior monowaves (`mg0, mg2`) inside the high/low bounds of `m1` until either the peak or trough of `m1` is broken, establishing confirmed **Group Waves (`m1, m2, ...`)**.
5. **Retracement Rules (1–7), Pre-Constructive Logic & Pattern Isolation (`models/identifier.py` & `models/structure_labeling.py`)**  
   - Computes **Rule (1–7)** from the retracement ratio `|m2| / |m1|`, **Condition (`a`–`f`)** from `|m0| / |m1|`, and **Category (`i`–`iii`)** from `|m3| / |m2|` (for Rule 4).
   - Transforms `(Rule, Condition, Category)` identifiers (e.g., `1a`, `3b`, `4ai`, `5c`, `6d`, `7a`) into **Neely Structure Labels**:
     - **Impulsive:** `:5`, `:s5` (Special Five), `:L5` (Last Five)
     - **Corrective:** `:F3` (First Three), `:c3` (Center Three), `x:c3` (X-Wave Center Three), `:sL3` (Second-to-Last Three), `:L3` (Last Three)
   - Applies **Position Indicator Sequences** to filter candidate lists and **Pattern Isolation Procedures** to isolate completed 3-wave and 5-wave Elliott formations terminating at `:L5` or `:L3`.

---

## Project Structure

```text
Elliottwave_Modeling/
├── app.py                         # Interactive Streamlit dashboard & Plotly visualizer
├── main.py                        # Streamlit entrypoint alias
├── elliott.py                     # CLI runner for headless analysis & wave inspection
├── requirements.txt               # Python dependencies (streamlit, plotly, pandas, numpy)
├── data/
│   ├── btcusd.csv                 # Historical BTC/USD OHLCV dataset
│   └── simulator.py               # Tick-by-tick & batch price series simulator
└── models/
    ├── wave_detector.py           # Monowaves, Proportion, Neutrality & Observation Rules
    ├── identifier.py              # Retracement Rules (1–7), Conditions (a–f) & Categories (i–iii)
    └── structure_labeling.py      # Pre-Constructive Logic (1a–7d) & Pattern Isolation (:L5 / :L3)
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Interactive Streamlit Web App
```bash
streamlit run app.py
```

### 3. Run the Command-Line Wave Analyzer
```bash
python elliott.py --start 5570 --steps 100
```
