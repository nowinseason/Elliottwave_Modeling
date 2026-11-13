# Glenn Neely - Mastering Elliott Wave (Chapter 3, pp. 3-22 to 3-32)
# Retracement Rule Identification (Rules 1-7), Condition Identification (a-f),
# and Category Identification (i-iii)
from models.structure_labeling import structure


class identifier:
    """
    Computes Neely's Retracement Rules (1-7), Conditions (a-f), and Categories (i-iii)
    for each confirmed Group Monowave (m1) using surrounding waves m0, m2, and m3,
    then transforms Rule Identifiers into Neely Structure Labels (:5, :s5, :L5, :F3, :c3, x:c3, :sL3, :L3).
    """

    def __init__(self, fib_tolerance=0.02):
        self.price = list()
        self.label = list()
        self.monowave = dict()
        self.logic = dict()       # group_idx -> tuple of (rule_code, structure_labels, details_dict)
        self.details = dict()     # group_idx -> detailed ratio & structure metadata
        self.patterns = list()    # Isolated Elliott Wave patterns (pp. 3-64 to 3-67)
        self.cur_idx = 1
        self.fib_tolerance = float(fib_tolerance)

        self.rule = None
        self.precon = None
        self.condition = None
        self.category = ""

    def add(self, data):
        self.price.append(float(data))

    def _wave_bounds(self, idx):
        """Return (start_price_idx, end_price_idx) for group wave `idx`."""
        end_idx = self.monowave[idx][-1]
        if idx == 0:
            start_idx = self.monowave[0][0]
        else:
            start_idx = self.monowave[idx - 1][-1]
        return start_idx, end_idx

    def _wave_prices(self, idx):
        """Return (start_price, end_price) for group wave `idx`."""
        s_idx, e_idx = self._wave_bounds(idx)
        return self.price[s_idx], self.price[e_idx]

    def _wave_change(self, idx):
        """Return vertical price coverage |end_price - start_price| for group wave `idx`."""
        sp, ep = self._wave_prices(idx)
        return abs(ep - sp)

    def startidx(self):
        """
        Determine initial wave index for analysis.
        Following Neely (p. 3-2 & 3-22), we can start from group wave 1 (which has m0 = wave 0)
        or from the earliest important low/high.
        """
        if self.cur_idx is None:
            self.cur_idx = 1

    def rule_identifier(self, mono_idx):
        """
        Rule Identification (Chapter 3, p. 3-23 & Figure 3-30, p. 3-31):
        Measures m2's price retracement of m1: r_m2_m1 = |m2| / |m1|.
        """
        self.idx = mono_idx
        m1_change = max(1e-9, self._wave_change(self.idx))
        m2_change = self._wave_change(self.idx + 1)
        self.r_m2_m1 = m2_change / m1_change

        tol = self.fib_tolerance
        if self.r_m2_m1 < 0.382:
            self.rule = 1
        elif abs(self.r_m2_m1 - 0.618) <= tol:
            # Rule 3: m2 is ~61.8% of m1 (with Neely's Fibonacci leeway, p. 3-34)
            self.rule = 3
        elif 0.382 <= self.r_m2_m1 < 0.618:
            self.rule = 2
        elif 0.618 < self.r_m2_m1 < 1.000:
            self.rule = 4
        elif 1.000 <= self.r_m2_m1 < 1.618:
            self.rule = 5
        elif 1.618 <= self.r_m2_m1 <= 2.618:
            self.rule = 6
        else:
            self.rule = 7

    def condition_identifier(self):
        """
        Condition Identification (Chapter 3, pp. 3-23 to 3-32):
        Measures m0's price relationship to m1: r_m0_m1 = |m0| / |m1|.
        """
        m1_change = max(1e-9, self._wave_change(self.idx))
        m0_change = self._wave_change(self.idx - 1)
        self.r_m0_m1 = m0_change / m1_change

        proportion = self.r_m0_m1
        tol = self.fib_tolerance

        if proportion < 0.382:
            self.precon = "a"
        elif 0.382 <= proportion < 0.618:
            self.precon = "b"
        elif 0.618 <= proportion < 1.000:
            self.precon = "c"
        elif abs(proportion - 1.618) <= tol:
            self.precon = "d2"
        elif 1.000 <= proportion < 1.618:
            self.precon = "d1"
        elif 1.618 < proportion <= 2.618:
            self.precon = "e"
        else:
            self.precon = "f"

    def precon_to_con(self):
        """
        Translate pre-condition into Rule-specific Condition ('a'-'f')
        and Category ('i'-'iii' for Rule 4), per Diagrams on pp. 3-31 & 3-32.
        """
        self.category = ""

        # Rule 1 (p. 3-23 & p. 3-31)
        if self.rule == 1:
            if self.precon in ("a", "b"):
                self.condition = "a"
            elif self.precon == "c":
                self.condition = "b"
            elif self.precon in ("d1", "d2"):
                self.condition = "c"
            else:
                self.condition = "d"

        # Rule 2 (p. 3-24 & p. 3-31)
        elif self.rule == 2:
            if self.precon == "a":
                self.condition = "a"
            elif self.precon == "b":
                self.condition = "b"
            elif self.precon == "c":
                self.condition = "c"
            elif self.precon in ("d1", "d2"):
                self.condition = "d"
            else:
                self.condition = "e"

        # Rule 3 (p. 3-25 & p. 3-31)
        elif self.rule == 3:
            if self.precon == "a":
                self.condition = "a"
            elif self.precon == "b":
                self.condition = "b"
            elif self.precon == "c":
                self.condition = "c"
            elif self.precon == "d1":
                self.condition = "d"
            elif self.precon in ("d2", "e"):
                self.condition = "e"
            else:
                self.condition = "f"

        # Rule 4 (p. 3-26 & p. 3-32)
        elif self.rule == 4:
            if self.precon == "a":
                self.condition = "a"
            elif self.precon in ("b", "c"):
                self.condition = "b"
            elif self.precon == "d1":
                self.condition = "c"
            elif self.precon in ("d2", "e"):
                self.condition = "d"
            else:
                self.condition = "e"
            self.category_identifier()

        # Rules 5, 6, 7 (pp. 3-28 to 3-32)
        elif self.rule in (5, 6, 7):
            if self.precon in ("a", "b", "c"):
                self.condition = "a"
            elif self.precon == "d1":
                self.condition = "b"
            elif self.precon in ("d2", "e"):
                self.condition = "c"
            else:
                self.condition = "d"

        code = f"{self.rule}{self.condition}{self.category}"
        self.logic[self.idx] = (code,)

    def category_identifier(self):
        """
        Categories for Conditions 'a' through 'e' of Rule 4 (p. 3-26):
        Measures m3's retracement of m2: r_m3_m2 = |m3| / |m2|.
        """
        if (self.idx + 2) not in self.monowave:
            self.category = "i"
            self.r_m3_m2 = None
            return

        m2_change = max(1e-9, self._wave_change(self.idx + 1))
        m3_change = self._wave_change(self.idx + 2)
        self.r_m3_m2 = m3_change / m2_change

        if self.r_m3_m2 < 1.618:
            self.category = "i"
        elif 1.618 <= self.r_m3_m2 <= 2.618:
            self.category = "ii"
        else:
            self.category = "iii"

    def __call__(self, *args):
        """
        Analyze all confirmed Group Monowaves that have sufficient surrounding waves
        (at least m0 and m2), then run Pre-Constructive Structure Labeling and
        Position Indicator simplification.
        """
        if args and isinstance(args[0], int):
            return self.logic.get(args[0])

        n_groups = len(self.monowave)
        if n_groups < 3 or not self.price:
            return self.logic

        self.logic = dict()
        self.details = dict()

        # Every group wave idx in [1 .. n_groups - 2] has both m0 (idx-1) and m2 (idx+1)
        for idx in range(1, n_groups - 1):
            self.r_m3_m2 = None
            self.rule_identifier(idx)
            self.condition_identifier()
            self.precon_to_con()

            code = self.logic[idx][0]
            s_idx, e_idx = self._wave_bounds(idx)
            self.details[idx] = {
                "group_idx": idx,
                "wave_name": f"m{idx + 1}",
                "start_idx": s_idx,
                "end_idx": e_idx,
                "start_price": self.price[s_idx],
                "end_price": self.price[e_idx],
                "rule": self.rule,
                "condition": self.condition,
                "category": self.category,
                "rule_code": code,
                "m2_m1_ratio": round(self.r_m2_m1 * 100, 1),
                "m0_m1_ratio": round(self.r_m0_m1 * 100, 1),
                "m3_m2_ratio": round(self.r_m3_m2 * 100, 1) if self.r_m3_m2 is not None else None,
            }

        # Transform Rule Identifiers into Structure Labels (:5, :F3, :c3, :s5, :L5, :sL3, :L3)
        struct_engine = structure(
            price=self.price,
            label=self.label,
            monowave=self.monowave,
            logic=self.logic,
        )
        struct_engine.run_all()
        self.logic = struct_engine.logic
        self.patterns = struct_engine.patterns

        for idx, meta in self.details.items():
            full_tuple = self.logic.get(idx, (meta["rule_code"],))
            structures = list(full_tuple[1:]) if len(full_tuple) > 1 else [":5", ":3"]
            primary = struct_engine.primary_structure.get(idx, structures[0])
            meta["structures"] = structures
            meta["primary_structure"] = primary
            meta["structure_meaning"] = struct_engine.describe_structure(primary)

        return self.logic
