import numpy as np

from reliabilityassessment.monte_carlo.gstate import _gstate


def test_gstate():
    # ---------------case1----------------------
    NUNITS = 2
    PROBG = np.array(
        [
            [0.2, 0.5],
            [0.1, 0.7],
        ]
    )
    RATING = np.array([150, 250])
    DERATE = np.array([0.35, 0.15])
    PLNDST = np.array([1, 1])
    rng_42 = np.random.default_rng(seed=42)
    # act
    # random numbers are generated for seed 42
    PCTAVL, AVAIL = _gstate(PROBG, RATING, DERATE, PLNDST, rng=rng_42)
    # assert
    assert PCTAVL.size == NUNITS
    assert AVAIL.size == NUNITS
    # unit 1 random #: 0.7739560485559633
    assert PCTAVL[0] == 0
    assert AVAIL[0] == 0
    # unit 2 random #: 0.4388784397520523
    assert PCTAVL[1] == 0.15
    assert AVAIL[1] == 37.5

    # ---------------case2----------------------
    NUNITS = 2
    PROBG = np.array(
        [
            [0.2, 0.2],
            [0.7, 0.7],
        ]
    )
    RATING = np.array([150, 250])
    DERATE = np.array([0.0, 0.0])
    PLNDST = np.array([1, 1])
    rng_52 = np.random.default_rng(seed=52)
    # act
    # random numbers are generated for seed 42
    PCTAVL, AVAIL = _gstate(PROBG, RATING, DERATE, PLNDST, rng=rng_52)
    # assert
    assert PCTAVL.size == NUNITS
    assert AVAIL.size == NUNITS
    # unit 1 random #: 0.7739560485559633
    assert PCTAVL[0] == 0
    assert AVAIL[0] == 0
    # unit 2 random #: 0.4388784397520523
    assert PCTAVL[1] == 1
    assert AVAIL[1] == 250
