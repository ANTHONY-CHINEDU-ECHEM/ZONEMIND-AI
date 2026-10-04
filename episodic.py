"""Episodic memory and the strategy knob tuner.

Every operating day becomes an episode: the outlook the agent saw that morning, the
strategy knobs it chose, and what the day then cost in energy, demand and comfort. When
a new day begins the tuner retrieves the most similar past days and asks which knob
settings worked best under those conditions.

The estimate is a locally weighted ridge regression. Within the neighbourhood of
similar days, the day score is regressed on the outlook features (to absorb the
remaining weather and attendance differences) and on indicator variables for each knob
value. The indicator coefficients are the estimated effect of each choice. Evidence is gathered
by randomised exploration during commissioning, which is safe because every knob value
is policy compliant and every command is verified. After commissioning a knob leaves
its default only when the estimated saving clears a confidence margin.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

FEATURES = ("t_max", "t_min", "t_mean", "ghi_mean", "attendance", "is_monday", "dr_today")
_SCALES = np.array([5.0, 5.0, 5.0, 100.0, 0.25, 1.0, 0.5])


def context_vector(outlook: dict) -> np.ndarray:
    return np.array([float(outlook[f]) for f in FEATURES]) / _SCALES


@dataclass
class Episode:
    day: int
    label: str
    outlook: dict
    knobs: dict
    energy_cost: float
    peak_kw: float
    comfort_kh: float
    score: float
    explored: bool = False


class EpisodicMemory:
    def __init__(self) -> None:
        self.episodes: list[Episode] = []
        self._ctx = np.zeros((0, len(FEATURES)))

    def __len__(self) -> int:
        return len(self.episodes)

    def add(self, episode: Episode) -> None:
        self.episodes.append(episode)
        self._ctx = np.vstack([self._ctx, context_vector(episode.outlook)])

    def neighbours(self, outlook: dict, k: int) -> tuple[np.ndarray, np.ndarray]:
        """Indices and distances of the ``k`` most similar past days."""
        if not self.episodes:
            return np.array([], dtype=int), np.array([])
        dist = np.linalg.norm(self._ctx - context_vector(outlook), axis=1)
        idx = np.argsort(dist, kind="stable")[:k]
        return idx, dist[idx]

    def summaries(self, outlook: dict, k: int = 3) -> list[dict]:
        """Short records of the most similar days, for prompts and audit trails."""
        idx, _ = self.neighbours(outlook, k)
        out = []
        for i in idx:
            e = self.episodes[int(i)]
            out.append({"t_max": round(e.outlook["t_max"], 1), "t_min": round(e.outlook["t_min"], 1),
                        "attendance": round(e.outlook["attendance"], 2), "knobs": e.knobs,
                        "energy_cost": round(e.energy_cost, 2), "peak_kw": round(e.peak_kw, 1),
                        "comfort_kh": round(e.comfort_kh, 2)})
        return out

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([asdict(e) for e in self.episodes], fh)

    @classmethod
    def load(cls, path: str | Path) -> "EpisodicMemory":
        memory = cls()
        with open(path, encoding="utf-8") as fh:
            for raw in json.load(fh):
                memory.add(Episode(**raw))
        return memory


class KnobTuner:
    def __init__(self, cfg, memory: EpisodicMemory, seed: int = 0):
        self.m, self.memory = cfg.memory, memory
        self.knobs = {name: list(spec["values"]) for name, spec in cfg.memory.knobs.items()}
        self.defaults = {name: spec.default for name, spec in cfg.memory.knobs.items()}
        self.rng = np.random.default_rng(seed)

    def _random(self) -> dict:
        return {name: values[int(self.rng.integers(len(values)))] for name, values in self.knobs.items()}

    def choose(self, outlook: dict) -> tuple[dict, dict]:
        """Pick today's knobs. Returns the choice and a record of how it was made."""
        if len(self.memory) < self.m.warmup_days:
            return self._random(), {"how": "commissioning exploration", "explored": True}
        if self.rng.random() < self.m.epsilon:
            return self._random(), {"how": "scheduled exploration", "explored": True}

        idx, dist = self.memory.neighbours(outlook, self.m.neighbours)
        episodes = [self.memory.episodes[int(i)] for i in idx]
        bandwidth = self.m.bandwidth * max(float(dist.max()) / 2.0, 1e-3)
        w = np.exp(-0.5 * (dist / bandwidth) ** 2)
        centre = context_vector(outlook)
        columns = [np.ones(len(idx)), *(self.memory._ctx[idx] - centre).T]
        layout: list[tuple[str, object]] = []
        for name, values in self.knobs.items():
            for value in values:
                columns.append(np.array([1.0 if e.knobs[name] == value else 0.0 for e in episodes]))
                layout.append((name, value))
        x = np.column_stack(columns)
        y = np.array([e.score for e in episodes])
        penalty = self.m.ridge * np.eye(x.shape[1])
        penalty[0, 0] = 0.0
        xtw = x.T * w
        beta = np.linalg.solve(xtw @ x + penalty, xtw @ y)
        resid = y - x @ beta
        sigma = float(np.sqrt(np.average(resid**2, weights=w)))

        # A knob leaves its default only when the evidence from similar days is clear: the
        # estimated saving must exceed ``confidence`` standard errors. Daily scores are noisy,
        # and acting on noise is worse than not adapting at all.
        offset = 1 + len(FEATURES)
        choice, effects = {}, {}
        for name, values in self.knobs.items():
            stats = {}
            for j, (knob, value) in enumerate(layout):
                if knob == name:
                    wj = w * x[:, offset + j]
                    ess = float(wj.sum() ** 2 / max((wj**2).sum(), 1e-12))   # effective sample size
                    stats[value] = (float(beta[offset + j]), ess)
            base_effect, base_n = stats[self.defaults[name]]
            choice[name], best_gain = self.defaults[name], 0.0
            effects[name] = {}
            for value, (effect, ess) in stats.items():
                gain = base_effect - effect
                se = sigma * np.sqrt(1.0 / max(ess, 1e-6) + 1.0 / max(base_n, 1e-6))
                effects[name][str(value)] = {"saving_vs_default": round(gain, 2), "std_error": round(float(se), 2)}
                if value != self.defaults[name] and gain > self.m.confidence * se and gain > best_gain:
                    choice[name], best_gain = value, gain
        return choice, {"how": "episodic memory", "explored": False, "neighbours": len(idx),
                        "effects": effects, "residual_sd": round(sigma, 2)}
