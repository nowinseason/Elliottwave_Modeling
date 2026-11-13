# Glenn Neely - Mastering Elliott Wave (Chapter 3, pp. 3-32 to 3-67)
# Pre-Constructive Rules of Logic, Position Indicator Sequences, and Pattern Isolation


class structure:
    """
    Transforms Retracement Rule Identifiers (1a-7d) into Neely Structure Labels
    (:5, :s5, :L5, :F3, :c3, x:c3, :sL3, :L3), simplifies multi-label lists using
    Position Indicator sequences (pp. 3-60 to 3-64), and isolates completed Elliott
    Wave patterns via Pattern Isolation Procedures (pp. 3-64 to 3-67).
    """

    STRUCTURE_DESCRIPTIONS = {
        ":5": "Impulsive Five (:5) — Wave 1 or 3 of an Impulse, or Wave A of a Zigzag",
        ":s5": "Special Five (:s5) — Wave 3 of a 5th-Wave Failure/Extension or C-wave in a Complex Correction",
        ":L5": "Last Five (:L5) — Terminal Wave 5 of an Impulse or Wave C of a Flat/Zigzag (Pattern Conclusion)",
        ":F3": "First Three (:F3) — Wave A of a Correction or Wave 1 of a Terminal Impulse",
        ":c3": "Center Three (:c3) — Wave B of a Correction, Triangle Leg, or Wave 3 of a Terminal",
        "x:c3": "X-Wave Center Three (x:c3) — Connecting X-wave between two Standard Corrections",
        ":sL3": "Second-to-Last Three (:sL3) — Wave D of a Triangle or Wave 4 of a Terminal (precedes :L3)",
        ":L3": "Last Three (:L3) — Wave E concluding a Triangle or Wave 5 concluding a Terminal (Pattern Conclusion)",
    }

    def __init__(self, price=None, label=None, monowave=None, logic=None):
        self.price = price if price is not None else list()
        self.label = label if label is not None else list()
        self.monowave = monowave if monowave is not None else dict()
        self.logic = logic if logic is not None else dict()
        self.primary_structure = dict()
        self.patterns = list()

    def _has(self, idx):
        return idx in self.monowave and len(self.monowave[idx]) > 0

    def _bounds(self, idx):
        if not self._has(idx):
            return 0, 0
        end_idx = self.monowave[idx][-1]
        start_idx = self.monowave[0][0] if idx == 0 else self.monowave[idx - 1][-1]
        return start_idx, end_idx

    def p(self, idx, param="e"):
        """Price of endpoint ('e') or startpoint ('s') of group wave `idx`."""
        if not self._has(idx):
            return self.price[-1] if self.price else 0.0
        s_idx, e_idx = self._bounds(idx)
        return self.price[e_idx] if param == "e" else self.price[s_idx]

    def l(self, idx):
        """Time duration (in base time units) consumed by group wave `idx`."""
        if not self._has(idx):
            return 1
        s_idx, e_idx = self._bounds(idx)
        return max(1, e_idx - s_idx)

    def c(self, idx):
        """Signed price change of group wave `idx`."""
        if not self._has(idx):
            return 0.0
        return self.p(idx, "e") - self.p(idx, "s")

    def ac(self, idx):
        """Absolute vertical price coverage |change| of group wave `idx`."""
        return abs(self.c(idx))

    def r(self, idx):
        """Absolute price retracement of wave `idx` by wave `idx + 1`."""
        if not self._has(idx + 1):
            return 0.0
        return self.ac(idx + 1)

    def n(self, idx):
        """Number of raw monowaves (M1, M2, ...) compacted inside group wave `idx`."""
        if not self._has(idx) or not self.label:
            return 1
        s = self.monowave[idx][0]
        e = self.monowave[idx][-1] + 1
        return max(1, len(set(self.label[s:e])))

    def btw(self, idx, idx_a, idx_b):
        """Check whether wave bounds overlap in price range."""
        if not (self._has(idx) and self._has(idx_a) and self._has(idx_b)):
            return False
        if self.c(idx) >= 0:
            return self.p(idx_a, "s") > self.p(idx_b, "e")
        return self.p(idx_a, "e") > self.p(idx_b, "s")

    def cmp(self, idx, idx_a, idx_b):
        """Compare directional end prices between wave `idx_a` and `idx_b`."""
        if not (self._has(idx) and self._has(idx_a) and self._has(idx_b)):
            return False
        if self.c(idx) >= 0:
            return self.p(idx_b, "e") > self.p(idx_a, "e")
        return self.p(idx_b, "e") < self.p(idx_a, "e")

    @staticmethod
    def size(values):
        vals = [abs(v) for v in values]
        if len(vals) < 2:
            return True
        a = max(vals)
        b = min(vals)
        rem = list(vals)
        rem.remove(b)
        c = min(rem)
        return a >= c

    def structure_labeling(self, idx):
        """
        Pre-Constructive Rules of Logic (Chapter 3, pp. 3-35 to 3-59):
        Transforms the Rule-Condition code of `m1` (`idx`) into candidate Structure Labels.
        Index mapping relative to m1 (`idx`):
          idx - 2 : m(-1)
          idx - 1 : m0
          idx     : m1
          idx + 1 : m2
          idx + 2 : m3
        """
        if idx not in self.logic or not self.logic[idx]:
            return
        code = self.logic[idx][0]
        labels = []

        def add_lbl(*items):
            for it in items:
                if it not in labels:
                    labels.append(it)

        m0_c = self.ac(idx - 1)
        m1_c = max(1e-9, self.ac(idx))
        m2_c = self.ac(idx + 1)
        m3_c = self.ac(idx + 2)
        m_1_c = self.ac(idx - 2)

        m0_t = self.l(idx - 1)
        m1_t = self.l(idx)
        m2_t = self.l(idx + 1)
        m3_t = self.l(idx + 2)

        # ==================== RULE 1 (pp. 3-35 to 3-37) ====================
        # Base list: {:5/(:c3)/(x:c3)/[:sL3]/[:s5]}
        if code == "1a":
            if m2_t >= m1_t or (self._has(idx + 2) and m2_t >= m3_t):
                add_lbl(":5")
            if self._has(idx - 2) and 1.00 * m0_c <= m_1_c <= 1.618 * m0_c:
                add_lbl(":s5")
            if self._has(idx - 2) and abs(m0_c - m2_c) / m1_c <= 0.382:
                if m_1_c >= 1.618 * m1_c:
                    add_lbl(":c3")
                else:
                    add_lbl(":sL3", ":c3")
            if not labels:
                add_lbl(":5")

        elif code == "1b":
            add_lbl(":5")
            if self._has(idx - 2) and 1.00 * m0_c <= m_1_c <= 1.618 * m0_c and self.cmp(idx, idx - 1, idx + 3):
                add_lbl(":s5")
            if self.btw(idx, idx - 1, idx + 1) and self._has(idx + 2) and m3_c > m1_c and m3_t <= m1_t:
                if self._has(idx - 2) and m_1_c > m1_c:
                    add_lbl(":sL3")
                else:
                    add_lbl(":c3")
            if self._has(idx + 2) and m3_c < m1_c and self.btw(idx, idx - 1, idx + 1):
                add_lbl(":c3")

        elif code == "1c":
            add_lbl(":5")
            if abs(m0_c - m1_c) / m1_c <= 0.15 and self._has(idx + 2) and m3_c > m1_c:
                add_lbl(":c3")
            if self._has(idx + 2) and m3_c > m1_c and m3_t < m1_t:
                add_lbl(":sL3")

        elif code == "1d":
            add_lbl(":5")

        # ==================== RULE 2 (pp. 3-37 to 3-40) ====================
        # Base list: {:5/(:sL3)/[:c3]/[:s5]}
        elif code == "2a":
            add_lbl(":5")
            if self.cmp(idx, idx - 1, idx + 3):
                add_lbl(":s5")
            if self._has(idx - 2) and abs(m0_c - m2_c) / max(1e-9, m2_c) <= 0.382 and m_1_c >= 1.618 * m1_c:
                add_lbl(":c3")
            if self._has(idx - 2) and m_1_c > m0_c and m0_t < m1_t and self._has(idx + 2) and m3_t <= m1_t:
                add_lbl(":c3")

        elif code == "2b":
            add_lbl(":5")
            if not self.cmp(idx, idx - 1, idx + 3):
                add_lbl(":s5")
            if self._has(idx - 2) and m_1_c >= 1.618 * m1_c and self._has(idx + 2) and m3_c > m_1_c:
                add_lbl(":c3")
            if self.btw(idx, idx - 1, idx + 1) and m0_t > m1_t:
                add_lbl(":sL3")

        elif code == "2c":
            add_lbl(":5")
            if not self.cmp(idx, idx - 1, idx + 3):
                add_lbl(":s5", "x:c3")
            if self._has(idx - 2) and m0_c < m_1_c < 2.618 * m1_c and self._has(idx + 2) and m3_c < m1_c:
                add_lbl(":c3")
            if m2_t <= m1_t and self._has(idx + 2) and m3_c > m1_c:
                add_lbl(":sL3")

        elif code == "2d":
            if m2_t >= m1_t or (self._has(idx + 2) and m2_t >= m3_t):
                add_lbl(":5")
            if m2_t <= m1_t and self._has(idx + 2) and m3_c > m1_c and abs(m0_t - m1_t) <= max(1, 0.382 * m1_t):
                add_lbl(":c3")
            if self._has(idx + 2) and m3_c > m1_c and m3_t < m1_t:
                add_lbl(":sL3")
            if not labels:
                add_lbl(":5")

        elif code == "2e":
            add_lbl(":5")
            if m2_t <= m1_t and self._has(idx + 2) and m3_c > m1_c:
                add_lbl(":c3")

        # ==================== RULE 3 (pp. 3-40 to 3-43) ====================
        # Base list: {:F3/:c3/:s5/:5/(:sL3)/[:L5]}
        elif code == "3a":
            if not self._has(idx + 2):
                add_lbl(":5", ":F3", ":c3")
            elif m3_c > 2.618 * m1_c:
                add_lbl(":c3", ":s5")
            elif 1.618 * m1_c <= m3_c <= 2.618 * m1_c:
                add_lbl(":s5", ":c3", ":F3")
            elif 1.00 * m1_c <= m3_c < 1.618 * m1_c:
                add_lbl(":F3", ":5", ":s5")
            else:
                add_lbl(":5", ":F3", ":s5")
            if self._has(idx - 2) and m1_c > m0_c and m1_c > m_1_c and m2_t <= m1_t:
                add_lbl(":L5")

        elif code == "3b":
            if not self._has(idx + 2):
                add_lbl(":5", ":c3", ":s5")
            elif m3_c > 2.618 * m1_c:
                add_lbl(":c3", ":s5")
            elif 1.618 * m1_c <= m3_c <= 2.618 * m1_c:
                add_lbl(":c3", ":s5")
            elif 1.00 * m1_c <= m3_c < 1.618 * m1_c:
                add_lbl(":5", ":s5", ":c3")
            else:
                add_lbl(":5", ":s5", ":F3")

        elif code == "3c":
            if not self._has(idx + 2):
                add_lbl(":F3", ":c3", ":sL3")
            elif m3_c > 2.618 * m1_c:
                add_lbl(":c3", ":sL3")
            elif 1.618 * m1_c <= m3_c <= 2.618 * m1_c:
                add_lbl(":F3", ":c3", ":sL3", ":s5")
            elif 1.00 * m1_c <= m3_c < 1.618 * m1_c:
                add_lbl(":F3", ":c3", ":sL3", ":s5")
            else:
                add_lbl(":c3", ":F3", ":s5")

        elif code == "3d":
            if not self._has(idx + 2):
                add_lbl(":5", ":c3", ":F3")
            elif m3_c > 2.618 * m2_c:
                add_lbl(":5", ":c3", ":sL3")
            elif 1.618 * m2_c <= m3_c <= 2.618 * m2_c:
                add_lbl(":c3", ":sL3", ":5")
            else:
                add_lbl(":5", ":c3", ":F3")

        elif code == "3e":
            if not self._has(idx + 2):
                add_lbl(":5", ":c3", ":F3")
            elif m3_c > 2.618 * m2_c:
                add_lbl(":5", ":c3", ":sL3")
            elif 1.618 * m2_c <= m3_c <= 2.618 * m2_c:
                add_lbl(":5", ":c3")
            else:
                add_lbl(":5", ":F3")

        elif code == "3f":
            if not self._has(idx + 2):
                add_lbl(":5", ":c3", ":F3")
            elif m3_c >= 1.618 * m2_c:
                add_lbl(":5", ":c3")
            else:
                add_lbl(":5", ":F3")

        # ==================== RULE 4 (pp. 3-44 to 3-50) ====================
        # Condition 'a': {:F3/:c3/:s5/[:sL3]}
        elif code == "4ai":
            if m3_t >= m2_t:
                add_lbl(":F3", ":s5")
            else:
                add_lbl(":F3", ":c3")
            if self.n(idx + 1) >= 3 and m2_t < m1_t:
                add_lbl(":L5")

        elif code == "4aii":
            if self._has(idx - 2) and m_1_c > 2.618 * m1_c:
                add_lbl(":F3")
            else:
                add_lbl(":s5", ":F3")

        elif code == "4aiii":
            if self._has(idx - 2) and m_1_c > 2.618 * m1_c:
                add_lbl(":F3")
            else:
                add_lbl(":s5", ":F3")

        # Condition 'b': {:F3/:c3/:s5/(:sL3)/(x:c3)/[:L5]}
        elif code == "4bi":
            if m3_t <= m2_t:
                add_lbl(":F3", ":c3")
            else:
                add_lbl(":F3", ":c3", ":s5")
            if self._has(idx - 2) and m1_c > m0_c and m1_c > m_1_c and m2_t <= m1_t:
                add_lbl(":L5")

        elif code == "4bii":
            add_lbl(":F3", ":c3")
            if self._has(idx - 2) and m1_c > m0_c and m1_c > m_1_c and m2_t <= m1_t:
                add_lbl(":L5")
            if m3_t > m2_t:
                add_lbl(":sL3", ":s5")

        elif code == "4biii":
            add_lbl(":c3", ":F3")
            if self._has(idx - 2) and m1_c > m0_c and m1_c > m_1_c and m2_t <= m1_t:
                add_lbl(":L5")

        # Condition 'c': {:c3/(:F3)/(x:c3)}
        elif code == "4ci":
            add_lbl(":F3", ":c3")
            if self._has(idx + 1) and m2_c > m1_c:
                add_lbl("x:c3")

        elif code == "4cii":
            if m2_t <= m1_t and m3_c > 1.618 * m1_c:
                add_lbl(":c3", ":F3")
            else:
                add_lbl(":F3", ":c3", "x:c3")

        elif code == "4ciii":
            add_lbl(":c3", ":F3")

        # Condition 'd': {:F3/(:c3)/(x:c3)}
        elif code in ("4di", "4dii"):
            if m2_t <= m1_t:
                add_lbl(":F3", ":c3")
            else:
                add_lbl(":F3", "x:c3")

        elif code == "4diii":
            if m3_t > m1_t and m2_t <= m1_t:
                add_lbl(":c3", ":F3")
            else:
                add_lbl(":F3", ":c3")

        # Condition 'e': {:F3/(x:c3)/[:c3]}
        elif code in ("4ei", "4eii", "4dei"):
            if m3_t <= m2_t:
                add_lbl(":F3")
            else:
                add_lbl(":F3", "x:c3", ":c3")

        elif code == "4eiii":
            if m3_t > m1_t and m2_t <= m1_t:
                add_lbl("x:c3", ":F3")
            else:
                add_lbl(":F3", ":c3")

        # ==================== RULE 5 (pp. 3-50 to 3-54) ====================
        # Base list: {:F3/:c3/:5/:L5/(:L3)}
        elif code == "5a":
            if self.n(idx + 1) > 3:
                add_lbl(":5", ":s5", ":F3")
            else:
                if m1_t >= m2_t:
                    if self._has(idx - 2) and m2_c < m_1_c and m3_c < 0.618 * m2_c:
                        add_lbl(":L3", ":L5")
                    else:
                        add_lbl(":L5")
                else:
                    add_lbl(":F3", ":c3", ":L5")

        elif code == "5b":
            if m3_c > m2_c:
                if abs(m0_c - m1_c) < abs(m0_c - 1.618 * m1_c):
                    add_lbl(":c3", "x:c3")
                else:
                    add_lbl(":F3", ":c3")
            elif m3_c >= 0.618 * m1_c:
                add_lbl(":F3")
            else:
                add_lbl(":c3", ":F3")

        elif code == "5c":
            if m1_t >= m2_t:
                if abs(m2_c - 1.618 * m1_c) / m1_c <= 0.15:
                    add_lbl(":L3", ":L5")
                elif self._has(idx - 2) and m_1_c < m0_c:
                    add_lbl(":sL3", ":c3")
                else:
                    add_lbl(":F3", ":L5")
            else:
                add_lbl(":F3", ":c3")

        elif code == "5d":
            if self.n(idx + 1) > 3:
                add_lbl(":F3")
            elif m1_t >= m2_t and self._has(idx - 2) and m_1_c < m0_c:
                add_lbl(":sL3", ":c3")
            elif m3_c < 0.618 * m2_c:
                add_lbl(":F3", ":c3")
            else:
                add_lbl(":F3", ":L3")

        # ==================== RULE 6 (pp. 3-54 to 3-57) ====================
        # Base list: {:5/:s5/:L5/:F3/:c3/:L3}
        elif code == "6a":
            if self.n(idx + 1) > 3:
                add_lbl(":5", ":s5", ":F3")
            else:
                if m1_t >= m2_t:
                    if m3_c < m2_c and self._has(idx - 2) and m2_c > m_1_c:
                        add_lbl(":L5", ":L3")
                    else:
                        add_lbl(":L5")
                else:
                    add_lbl(":F3", "x:c3")

        elif code == "6b":
            if self.n(idx + 2) > 3:
                add_lbl(":5", ":s5", ":F3")
            else:
                if m1_t <= m0_t or m1_t <= m2_t:
                    add_lbl("x:c3", ":F3")
                elif m1_t >= m2_t:
                    add_lbl(":L5", ":L3")
                else:
                    add_lbl(":c3", ":sL3")

        elif code == "6c":
            add_lbl(":F3")
            if m1_t >= m2_t:
                add_lbl(":L3", ":L5")
            elif m2_t <= m1_t and self._has(idx - 2):
                add_lbl(":sL3")

        elif code == "6d":
            if m0_t <= m1_t or m2_t <= m1_t:
                add_lbl(":F3")
            else:
                add_lbl(":L3", ":L5", ":F3")

        # ==================== RULE 7 (pp. 3-57 to 3-60) ====================
        # Base list: {:L5/:L3/:F3/:c3/:5/:s5}
        elif code == "7a":
            if self.n(idx + 1) > 3:
                add_lbl(":5", ":s5", ":F3")
            else:
                add_lbl(":L5")
                if m3_c < 0.618 * m2_c and self._has(idx - 2) and m_1_c < m0_c:
                    add_lbl(":L3")

        elif code == "7b":
            if self.n(idx + 2) > 3:
                add_lbl(":F3", ":c3", ":L3", ":L5")
            else:
                if m0_c >= 0.618 * m1_c and 1.00 * m2_c <= m3_c <= 2.618 * m2_c:
                    add_lbl(":c3")
                elif m1_t >= m2_t:
                    add_lbl(":L5", ":L3", ":sL3")
                else:
                    add_lbl(":c3", ":L3")

        elif code == "7c":
            add_lbl(":F3")
            if m2_t <= m0_t:
                add_lbl(":L3", ":L5")
            elif m1_t >= m2_t:
                add_lbl(":L5", ":sL3")

        elif code == "7d":
            if m0_t <= m1_t or m2_t <= m1_t:
                add_lbl(":F3", "x:c3", ":c3")
            else:
                add_lbl(":L5", ":L3", ":F3")

        else:
            add_lbl(":5", ":F3")

        self.logic[idx] = (code,) + tuple(labels)

    def apply_position_indicator_rules(self):
        """
        Implementation of Position Indicators (Chapter 3, pp. 3-60 to 3-64):
        Uses surrounding wave Structure choices to eliminate impossible Position Indicators
        and select the best primary Structure label for each wave.
        """
        keys = sorted(self.logic.keys())
        for idx in keys:
            tup = self.logic[idx]
            code = tup[0]
            candidates = list(tup[1:]) if len(tup) > 1 else [":5"]

            next_candidates = list(self.logic.get(idx + 1, ("",))[1:])
            prev_candidates = list(self.logic.get(idx - 1, ("",))[1:])

            filtered = []
            for lbl in candidates:
                # ":sL3" requires an ":L3" immediately following it (p. 3-63)
                if lbl == ":sL3" and next_candidates and ":L3" not in next_candidates:
                    continue
                # ":L5" should be preceded by ":F3" or ":c3" when previous wave is known (p. 3-64)
                if lbl == ":L5" and prev_candidates and not any(
                    p in prev_candidates for p in (":F3", ":c3", "x:c3", ":5", ":s5")
                ):
                    continue
                filtered.append(lbl)

            if not filtered:
                filtered = candidates

            self.logic[idx] = (code,) + tuple(filtered)
            self.primary_structure[idx] = filtered[0]

    def isolate_patterns(self):
        """
        Pattern Isolation Procedures (Chapter 3, pp. 3-64 to 3-67, Figures 3-31 to 3-35):
        Scans forward for waves containing ':L5' or ':L3' (which conclude Elliott patterns),
        then searches backward (3+ waves) for a valid pattern beginning (':F3', ':5', 'x:c3')
        requiring an odd number of waves (3 or 5) to form a complete Elliott Wave pattern.
        """
        self.patterns = []
        keys = sorted(self.logic.keys())
        if len(keys) < 3:
            return self.patterns

        used_up_to = -1
        for pos, end_wave_idx in enumerate(keys):
            structs = self.logic[end_wave_idx][1:]
            primary = self.primary_structure.get(end_wave_idx, structs[0] if structs else "")
            term_type = None
            if primary in (":L5", ":L3"):
                term_type = primary
            elif ":L5" in structs:
                term_type = ":L5"
            elif ":L3" in structs:
                term_type = ":L3"

            if not term_type or end_wave_idx <= used_up_to:
                continue

            # Search backward for pattern start (5 or 3 waves: pos - 4 or pos - 2)
            # per Figure 3-32 & 3-33 (p. 3-66)
            chosen_start = None
            for back_steps in (4, 2):
                if pos - back_steps >= 0:
                    cand_idx = keys[pos - back_steps]
                    if cand_idx < used_up_to:
                        continue
                    cand_structs = self.logic[cand_idx][1:]
                    if any(s in cand_structs for s in (":F3", ":5", "x:c3", ":s5", ":L5", ":L3")):
                        chosen_start = cand_idx
                        break

            if chosen_start is None and pos >= 2 and keys[pos - 2] >= used_up_to:
                chosen_start = keys[pos - 2]

            if chosen_start is not None:
                wave_span = [k for k in keys if chosen_start <= k <= end_wave_idx]
                s_price_idx, _ = self._bounds(chosen_start)
                _, e_price_idx = self._bounds(end_wave_idx)
                start_p = self.price[s_price_idx]
                end_p = self.price[e_price_idx]
                direction = "Bullish (Up)" if end_p >= start_p else "Bearish (Down)"

                if term_type == ":L5":
                    if len(wave_span) >= 5 or ":5" in self.logic[chosen_start][1:]:
                        pattern_class = "Impulse / 5-Wave Pattern (:L5 Termination)"
                    else:
                        pattern_class = "Standard Correction — Flat or Zigzag (:L5 Termination)"
                else:
                    pattern_class = "Triangle or Terminal Pattern (:L3 Termination)"

                seq_parts = []
                for idx_i, k in enumerate(wave_span):
                    lbl_disp = term_type if idx_i == len(wave_span) - 1 else self.primary_structure.get(k, self.logic[k][1])
                    seq_parts.append(f"m{k + 1}({lbl_disp})")

                self.patterns.append(
                    {
                        "start_wave": f"m{chosen_start + 1}",
                        "end_wave": f"m{end_wave_idx + 1}",
                        "wave_count": len(wave_span),
                        "termination": term_type,
                        "pattern_type": pattern_class,
                        "direction": direction,
                        "start_idx": s_price_idx,
                        "end_idx": e_price_idx,
                        "start_price": round(start_p, 2),
                        "end_price": round(end_p, 2),
                        "sequence": " - ".join(seq_parts),
                    }
                )
                used_up_to = end_wave_idx

        return self.patterns

    def run_all(self):
        for idx in sorted(self.logic.keys()):
            self.structure_labeling(idx)
        self.apply_position_indicator_rules()
        self.isolate_patterns()
        return self.logic

    @classmethod
    def describe_structure(cls, label):
        return cls.STRUCTURE_DESCRIPTIONS.get(label, "Elliott Wave Structure Label")


# Alias for backward compatibility with models/structure_labeling.py
transformation = structure
