import os
import random
import numpy as np
import pandas as pd


class simulator:
    """
    Price series simulator for step-by-step and batch Elliott Wave detection.
    Supports 'open', 'close', 'high', 'low', or Neely's recommended 'hl2'
    ((high + low) / 2, Chapter 2, p. 2-10).
    """

    def __init__(self, data_path, value="open", enable_file_log=False):
        self.data_path = data_path
        self.dataframe = pd.read_csv(data_path)
        if "hl2" not in self.dataframe.columns and {"high", "low"}.issubset(self.dataframe.columns):
            self.dataframe["hl2"] = (self.dataframe["high"] + self.dataframe["low"]) / 2.0

        self.value = value if value in self.dataframe.columns else "open"
        self.enable_file_log = enable_file_log

        self.gen_list = list()
        self.gen_time = list()
        self.gen_datetime = list()
        self.init_idx = 0
        self.data = self.dataframe[self.value]

    def __call__(self, *args, value=None):
        """Initialize or reset the starting index for price generation."""
        if value is not None and value in self.dataframe.columns:
            self.value = value
        self.data = self.dataframe[self.value]

        self.gen_list = list()
        self.gen_time = list()
        self.gen_datetime = list()

        max_idx = max(0, len(self.data) - 2)
        try:
            idx = int(args[0])
            self.init_idx = max(0, min(idx, max_idx))
        except (IndexError, TypeError, ValueError):
            self.init_idx = random.randint(0, max(0, len(self.data) - 500))

        self.gen_list.append(self.init_idx)
        return self.init_idx

    def __len__(self):
        return len(self.gen_time)

    def gen(self):
        """Advance one time unit and return the next price."""
        if not self.gen_list:
            self(0)

        out_idx = self.gen_list[-1]
        if out_idx >= len(self.data):
            out_idx = len(self.data) - 1

        next_idx = min(int(out_idx) + 1, len(self.data) - 1)
        self.gen_list.append(next_idx)

        raw_time = self.dataframe["time"].iloc[out_idx]
        self.gen_time.append(int(raw_time))
        dt_str = pd.to_datetime(raw_time, unit="ms").strftime("%Y-%m-%d %H:%M")
        self.gen_datetime.append(dt_str)

        if self.enable_file_log:
            os.makedirs("data/logs", exist_ok=True)
            filename = os.path.join(os.getcwd(), "data/logs", "log.txt")
            with open(filename, "w") as f:
                for idx in self.gen_list:
                    f.write(f"{idx}\n")

        return float(self.data.iloc[out_idx])
