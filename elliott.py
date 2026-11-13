### Elliott Wave Modeling — CLI & Streamlit Entrypoint
import os
import argparse

from data.simulator import simulator
from models.wave_detector import monowave
from models.identifier import identifier

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "btcusd.csv")


def run_cli(start_idx=5570, steps=60):
    sim = simulator(DATA_PATH)
    sim(start_idx)
    mon = monowave()
    idf = identifier()

    print(f"=== Glenn Neely Elliott Wave Engine (Start Idx: {start_idx}, Steps: {steps}) ===")
    for step in range(steps):
        price = sim.gen()
        mon.add(price)
        idf.add(price)
        price_val, label, direc, status = mon.analyze()

    idf.label = mon.label
    idf.monowave = mon.group_monowave
    idf()

    print(f"\nSummary after {steps} ticks:")
    print(f"  - Raw Monowaves identified : {len(mon.log_label)} ({mon.log_label[0]} .. {mon.log_label[-1]})")
    print(f"  - Neutrality Rollbacks     : {len(mon.rollbacks)}")
    print(f"  - Confirmed Group Waves    : {len(mon.group_monowave)}")
    print(f"  - Labeled Wave Structures  : {len(idf.details)}")
    print("\nWave Structure Breakdown:")
    for k, d in idf.details.items():
        structs = "/".join(d["structures"])
        print(
            f"  {d['wave_name']:>4} | Tick {d['start_idx']:>3} -> {d['end_idx']:>3} "
            f"| ${d['start_price']:>9,.2f} -> ${d['end_price']:>9,.2f} "
            f"| Rule {d['rule_code']:<5} | Primary: {d['primary_structure']:<5} "
            f"| {{{structs}}} | m2/m1={d['m2_m1_ratio']}%, m0/m1={d['m0_m1_ratio']}%"
        )

    if idf.patterns:
        print("\nIsolated Complete Elliott Patterns:")
        for pat in idf.patterns:
            print(
                f"  [{pat['start_wave']} -> {pat['end_wave']}] {pat['pattern_type']} "
                f"({pat['direction']}): {pat['sequence']}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Glenn Neely Elliott Wave Modeling")
    parser.add_argument("--start", type=int, default=5570, help="Starting candle index in btcusd.csv")
    parser.add_argument("--steps", type=int, default=80, help="Number of ticks to analyze")
    args, _ = parser.parse_known_args()
    run_cli(start_idx=args.start, steps=args.steps)
