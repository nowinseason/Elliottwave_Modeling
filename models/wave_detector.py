# Glenn Neely - Mastering Elliott Wave (Chapter 3: Preliminary Analysis)
# Monowave Identification, Rule of Proportion, Rule of Neutrality, and Rules of Observation
import os
import math
import warnings
import numpy as np

warnings.filterwarnings("ignore")


class monowave:
    def __init__(self, neutrality_angle=45.0, enable_file_log=False):
        # Initial settings and outputs
        self.idx = 1
        self.status = str()
        self.price = list()
        self.label = list()

        # Rule activation switches
        self.rule_of_proportion_switch = False
        self.rule_of_neurality_switch = False
        self.rule_of_observation_switch = False
        self.price_leng = False
        self.isdirectionchanged = False

        # Price-Time scaling parameters (Chapter 3, pp. 3-3 to 3-8)
        self.timestamp = float(86400)
        self.ratio = float(10 / 86400)
        self.ptr = self.timestamp * self.ratio
        self.neutrality_angle = float(neutrality_angle)
        self.enable_file_log = enable_file_log

        # Analytical outputs
        self.log_index = list()       # 1-based price index where each unique label begins
        self.log_label = list()       # Unique monowave labels ['M1', 'M2', ...]
        self.direction = dict()       # Index -> 'Dir' or 'Non-Dir' (Rule of Proportion)
        self.angles = dict()          # Monowave index -> progression angle in degrees
        self.rollbacks = list()       # Rule of Neutrality rollback events (< 45 deg)
        self.group_monowave = dict()  # Group wave index -> list of 0-based price indices
        self.newline = list()         # Interpolated group wave line
        self.mono_line = list()       # Interpolated raw monowave line
        self.mono618 = 0.0

        # Internal state for Rule of Observation
        self.stop = True
        self.group_idx = 0
        self.tmp_r_ob = dict()

    def add(self, price):
        self.price.append(float(price))

    def mono_indexing(self):
        """
        Identify Monowaves (M1, M2, M3, ...) by tracking every change in price direction
        (Chapter 3, p. 3-2, Figures 3-2a & 3-2b).
        """
        if len(self.price) < 3:
            self.price_leng = False
            self.rule_of_proportion_switch = False
            self.rule_of_neurality_switch = False
            self.isdirectionchanged = False
            label = "M" + str(self.idx)
            price = self.price[-1]

            if self.price[0] <= self.price[-1]:
                self.status = "inc"
            else:
                self.status = "dec"
        else:
            self.price_leng = True
            self.rule_of_proportion_switch = True

            if self.status == "inc":
                if self.price[-2] <= self.price[-1]:
                    label = "M" + str(self.idx)
                    price = self.price[-1]
                    self.isdirectionchanged = False
                    self.rule_of_neurality_switch = False
                else:
                    self.idx += 1
                    label = "M" + str(self.idx)
                    price = self.price[-1]
                    self.status = "dec"
                    self.isdirectionchanged = True
                    self.rule_of_neurality_switch = True

            elif self.status == "dec":
                if self.price[-2] <= self.price[-1]:
                    self.idx += 1
                    label = "M" + str(self.idx)
                    price = self.price[-1]
                    self.status = "inc"
                    self.isdirectionchanged = True
                    self.rule_of_neurality_switch = True
                else:
                    label = "M" + str(self.idx)
                    price = self.price[-1]
                    self.isdirectionchanged = False
                    self.rule_of_neurality_switch = False

        self.label.append(label)
        return label, price

    def logger(self, label):
        """Record the starting moment of each new monowave label."""
        if label not in self.log_label:
            self.log_label.append(label)
            self.log_index.append(len(self.price))
            if len(self.log_label) >= 2:
                self.rule_of_observation_switch = True
        else:
            self.rule_of_observation_switch = False

    def group_wave_encoding(self, start, end):
        """Encode a confirmed Group Monowave (Rule of Observation)."""
        start = max(0, int(start))
        end = int(end)
        if end <= start:
            end = start + 1
        idx_li = list(range(start, end))
        self.group_monowave[self.group_idx] = idx_li
        self.group_idx += 1
        self.tmp_r_ob = dict()

    def rule_of_proportion(self):
        """
        Rule of Proportion (Chapter 3, pp. 3-3 to 3-8, Figures 3-6 to 3-11):
        Evaluates whether each monowave is retraced by less than 61.8% (Directional Action, 'Dir')
        or more than 61.8% (Non-Directional Action, 'Non-Dir') and checks the 45-degree
        price-time square progression (within 25% deviation of the square perimeter).
        """
        for i in range(len(self.log_label) - 1):
            start_idx = max(0, self.log_index[i] - 1)
            new_idx = self.log_index[i + 1] - 1
            end_idx = max(start_idx, new_idx - 1)

            start_price = self.price[start_idx]
            end_price = self.price[end_idx]
            new_price = self.price[new_idx]

            mono_change = end_price - start_price
            mono_return = new_price - end_price
            self.mono618 = 0.618 * abs(mono_change)

            t_pass = max(1, end_idx - start_idx)
            base_t = t_pass * self.ptr
            angle = round(math.degrees(math.atan(abs(mono_change) / base_t)), 1)
            self.angles[i] = angle

            # 25% deviation bounds of the price-time square (Figure 3-6, p. 3-6)
            upper_limit = abs(mono_change) * 1.25
            lower_limit = base_t * 1.25

            upper_angle = round(math.degrees(math.atan(upper_limit / base_t)), 1)
            lower_angle = round(math.degrees(math.atan(abs(mono_change) / lower_limit)), 1)

            if self.mono618 < abs(mono_return):
                if angle <= upper_angle and angle >= lower_angle:
                    for key in range(start_idx, new_idx):
                        self.direction[key] = "Dir"
                else:
                    for key in range(start_idx, new_idx):
                        self.direction.setdefault(key, "Non-Dir")
                self.direction[new_idx] = "Non-Dir"
            else:
                for key in range(start_idx, new_idx + 1):
                    self.direction[key] = "Dir"

    def rule_of_neurality(self, label):
        """
        Rule of Neutrality (Chapter 3, pp. 3-9 to 3-13, Figures 3-12 to 3-14b):
        Activates when price direction changes. If the angle of the new move is under
        45 degrees (progressing more horizontally than vertically), rolls back the new
        monowave label into the prior monowave.
        """
        if self.neutrality_angle <= 0 or len(self.log_label) < 2:
            return

        new_idx = len(self.price) - 1
        new_price = self.price[new_idx]
        end_price = self.price[new_idx - 1]
        change = new_price - end_price

        angle = round(math.degrees(math.atan(abs(change) / self.ptr)), 1)

        if angle < self.neutrality_angle:
            self.rollbacks.append(
                {
                    "index": new_idx,
                    "price": new_price,
                    "prev_price": end_price,
                    "angle": angle,
                    "rolled_back_label": label,
                }
            )
            self.log_label.pop()
            self.log_index.pop()
            self.label.pop()
            self.label.append(self.log_label[-1])
            self.idx -= 1
            self.rule_of_observation_switch = False
            if self.status == "dec":
                self.status = "inc"
            elif self.status == "inc":
                self.status = "dec"

    def preset_r_ob(self):
        """Initialize the first Group Monowave once M1 completes and M2 begins."""
        if len(self.log_label) == 2 and self.stop:
            start = 0
            end = len(self.label) - 1
            self.group_idx = 0
            self.group_wave_encoding(start, end)
            self.stop = False

    def rule_of_observation(self):
        """
        Rules of Observation (Chapter 3, pp. 3-14 to 3-21, Figures 3-20a/b & 3-21a/b):
        Determines when m2 (or monowave group mg2) is confirmed complete by observing
        when the high or low of m1 is broken.
        """
        if self.group_idx < 1:
            return

        if self.group_idx < 2:
            start_index = self.group_monowave[self.group_idx - 1][0]
            start_price = self.price[start_index]
            end_index = self.group_monowave[self.group_idx - 1][-1]
            end_price = self.price[end_index]
        else:
            start_index = self.group_monowave[self.group_idx - 2][-1]
            start_price = self.price[start_index]
            end_index = self.group_monowave[self.group_idx - 1][-1]
            end_price = self.price[end_index]

        current_turn_idx = self.log_index[-1] - 2
        if current_turn_idx <= end_index:
            return

        mono_end_price = self.price[current_turn_idx]
        interior_candidates = {
            p: idx
            for p, idx in self.tmp_r_ob.items()
            if end_index <= idx < current_turn_idx
        }

        if start_price - end_price < 0:  # m1 is an advancing (upward) wave
            if start_price <= mono_end_price <= end_price:
                # Consolidating inside m1's price range (mg2 forming)
                pass
            elif mono_end_price < start_price:
                # Low of m1 broken: first turn-up completes m2 (Figure 3-20a, 2nd diagram)
                new_start_index = end_index + 1
                new_end_index = self.log_index[-1] - 1
                self.group_wave_encoding(new_start_index, new_end_index)
            elif mono_end_price > end_price:
                # High of m1 broken: m2 confirmed complete at lowest point between
                # high of m1 and newest high (Figure 3-20a, 1st diagram)
                new_start_index = end_index + 1
                if interior_candidates:
                    min_p = min(interior_candidates.keys())
                    trough_idx = interior_candidates[min_p]
                    new_end_index = max(new_start_index + 1, trough_idx + 1)
                    self.group_wave_encoding(new_start_index, new_end_index)
                    new_start_index2 = new_end_index
                    new_end_index2 = self.log_index[-1] - 1
                    if new_end_index2 > new_start_index2:
                        self.group_wave_encoding(new_start_index2, new_end_index2)
                else:
                    new_end_index = self.log_index[-1] - 1
                    self.group_wave_encoding(new_start_index, new_end_index)

        elif start_price - end_price > 0:  # m1 is a declining (downward) wave
            if end_price <= mono_end_price <= start_price:
                # Consolidating inside m1's price range (mg2 forming)
                pass
            elif mono_end_price > start_price:
                # High of m1 broken: first turn-down completes m2 (Figure 3-20a, 3rd diagram)
                new_start_index = end_index + 1
                new_end_index = self.log_index[-1] - 1
                self.group_wave_encoding(new_start_index, new_end_index)
            elif mono_end_price < end_price:
                # Low of m1 broken: m2 confirmed complete at highest point between
                # low of m1 and newest low (Figure 3-20a, 4th diagram)
                new_start_index = end_index + 1
                if interior_candidates:
                    max_p = max(interior_candidates.keys())
                    peak_idx = interior_candidates[max_p]
                    new_end_index = max(new_start_index + 1, peak_idx + 1)
                    self.group_wave_encoding(new_start_index, new_end_index)
                    new_start_index2 = new_end_index
                    new_end_index2 = self.log_index[-1] - 1
                    if new_end_index2 > new_start_index2:
                        self.group_wave_encoding(new_start_index2, new_end_index2)
                else:
                    new_end_index = self.log_index[-1] - 1
                    self.group_wave_encoding(new_start_index, new_end_index)
        else:
            # Flat initial wave edge case
            new_start_index = end_index + 1
            new_end_index = self.log_index[-1] - 1
            if new_end_index > new_start_index:
                self.group_wave_encoding(new_start_index, new_end_index)

    def groupwave_line(self):
        """
        Generate linear segments connecting the start and termination points of
        all confirmed Group Monowaves.
        """
        if not self.group_monowave:
            return []

        first_grp = self.group_monowave[0]
        st = np.linspace(
            self.price[first_grp[0]],
            self.price[first_grp[-1]],
            len(first_grp),
        )

        for i in range(len(self.group_monowave) - 1):
            prev_end_idx = self.group_monowave[i][-1]
            curr_end_idx = self.group_monowave[i + 1][-1]
            seg_len = curr_end_idx - prev_end_idx
            if seg_len > 0:
                new = np.linspace(
                    self.price[prev_end_idx],
                    self.price[curr_end_idx],
                    seg_len + 1,
                )[1:]
                st = np.append(st, new)
        return st.tolist()

    def monowave_vertices(self):
        """
        Return the list of raw Monowave vertices:
        [(price_idx, price, label), ...] including the initial point (0, price[0], 'M0').
        """
        if not self.price:
            return []
        vertices = [(0, self.price[0], "Start")]
        for i in range(len(self.log_label) - 1):
            lbl = self.log_label[i]
            end_idx = max(0, self.log_index[i + 1] - 2)
            vertices.append((end_idx, self.price[end_idx], lbl))
        # Add currently developing monowave endpoint
        if self.log_label:
            last_idx = len(self.price) - 1
            if vertices[-1][0] != last_idx:
                vertices.append((last_idx, self.price[last_idx], self.log_label[-1] + "*"))
        return vertices

    def groupwave_vertices(self):
        """
        Return the list of confirmed Group Wave vertices from Rule of Observation:
        [(group_idx, price_idx, price, label), ...]
        """
        if not self.group_monowave:
            return []
        vertices = []
        for i in range(len(self.group_monowave)):
            m_idx = self.group_monowave[i][-1]
            vertices.append((i, m_idx, self.price[m_idx], f"m{i + 1}"))
        return vertices

    def analyze(self):
        label, price = self.mono_indexing()
        self.direction[len(self.price) - 1] = None
        self.logger(label)

        if self.rule_of_proportion_switch:
            self.rule_of_proportion()

        if self.rule_of_neurality_switch:
            self.rule_of_neurality(label)

        self.preset_r_ob()
        if len(self.log_label) > 2:
            mono_end_idx = self.log_index[-1] - 2
            mono_end_price = self.price[mono_end_idx]
            self.tmp_r_ob[mono_end_price] = mono_end_idx
            if self.rule_of_observation_switch:
                self.rule_of_observation()
                self.newline = self.groupwave_line()
        elif self.group_monowave:
            self.newline = self.groupwave_line()

        label = self.label[-1]
        direc = self.direction.get(len(self.price) - 1)

        if self.enable_file_log:
            os.makedirs("models/logs", exist_ok=True)
            filename = os.path.join(os.getcwd(), "models/logs", "log.txt")
            with open(filename, "a") as f:
                f.write(f"{self.price[-1]}, {self.label[-1]}, {direc}\n")

        return price, label, direc, self.status
