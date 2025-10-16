import numpy as np
import pytest

from reliabilityassessment.monte_carlo.line_prob_sampling import (
    discrete_prob_gen,
    lstate,
    lstate_original,
)


# The following three tests are probabilistic which rely on the law of large numbers.
# If a test failure occurs, run again and see if the test passes
@pytest.mark.slow
def test_lstate():
    # arrange
    NLINES = 1000000
    PROB = np.array([0.9216, 0.0768, 0.0016, 0.0000, 0.0000, 0.0000])
    PROBL = np.cumsum(PROB)
    PROBL_mat = np.tile(PROBL, (NLINES, 1))
    # act
    LNSTAT = lstate(PROBL_mat, test_seed=42)
    # assert
    assert LNSTAT.size == NLINES
    LNSTAT_bins = np.bincount(LNSTAT)
    print(f"LNSTAT_bins={LNSTAT_bins}")
    assert LNSTAT_bins.size <= PROBL.size
    for i in range(LNSTAT_bins.size - 1):
        assert PROB[i] == pytest.approx(LNSTAT_bins[i + 1] / NLINES, 0.05)


@pytest.mark.slow
def test_lstate_original():
    # arrange
    NLINES = 1000000
    PROB = np.array([0.9216, 0.0768, 0.0016, 0.0000, 0.0000, 0.0000])
    PROBL = np.cumsum(PROB)
    # act
    LNSTAT = lstate_original(NLINES, PROBL, test_seed=42)
    # assert
    assert LNSTAT.size == NLINES
    LNSTAT_bins = np.bincount(LNSTAT)
    print(f"LNSTAT_bins={LNSTAT_bins}")
    assert LNSTAT_bins.size <= PROBL.size
    for i in range(LNSTAT_bins.size - 1):
        assert PROB[i] == pytest.approx(LNSTAT_bins[i + 1] / NLINES, 0.05)


@pytest.mark.slow
def test_generate_discrete_probability_generator():
    # arrange
    NLINES = 1000000
    PROB = np.array([0.9216, 0.0768, 0.0016, 0.0000, 0.0000, 0.0000])
    PROBL = np.cumsum(PROB)
    # act
    LNSTAT = discrete_prob_gen(NLINES, PROBL, test_seed=42)
    # assert
    assert LNSTAT.size == NLINES
    LNSTAT_bins = np.bincount(LNSTAT)
    print(f"LNSTAT_bins={LNSTAT_bins}")
    assert LNSTAT_bins.size <= PROBL.size
    for i in range(LNSTAT_bins.size - 1):
        assert PROB[i] == pytest.approx(LNSTAT_bins[i + 1] / NLINES, 0.05)


@pytest.mark.slow
def test_lstate_benchmark(benchmark):
    # setup
    NLINES = 1000000
    PROB = np.array([0.9216, 0.0768, 0.0016, 0.0000, 0.0000, 0.0000])
    PROBL = np.cumsum(PROB)
    PROBL_mat = np.tile(PROBL, (NLINES, 1))
    # benchmark
    benchmark(lstate, PROBL_mat)


@pytest.mark.slow
def test_lstate_original_benchmark(benchmark):
    # setup
    NLINES = 1000000
    PROB = np.array([0.9216, 0.0768, 0.0016, 0.0000, 0.0000, 0.0000])
    PROBL = np.cumsum(PROB)
    # benchmark
    benchmark(lstate_original, NLINES, PROBL)


@pytest.mark.slow
def test_discrete_prob_gen_benchmark(benchmark):
    # setup
    NLINES = 1000000
    PROB = np.array([0.9216, 0.0768, 0.0016, 0.0000, 0.0000, 0.0000])
    PROBL = np.cumsum(PROB)
    # benchmark
    benchmark(discrete_prob_gen, NLINES, PROBL)
