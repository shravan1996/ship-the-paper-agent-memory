"""Paired bootstrap over questions."""

import random


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def paired_bootstrap(a, b, n=10000, seed=0):
    """Mean of b minus a, with a 95% percentile interval from resampling question pairs."""
    assert len(a) == len(b) and a
    rng = random.Random(seed)
    diffs = [y - x for x, y in zip(a, b)]
    k = len(diffs)
    boots = sorted(mean([diffs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return {"diff": mean(diffs), "lo": boots[int(0.025 * n)], "hi": boots[int(0.975 * n) - 1], "n": k}
