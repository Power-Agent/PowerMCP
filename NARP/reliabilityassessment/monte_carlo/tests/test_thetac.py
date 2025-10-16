import numpy as np

from reliabilityassessment.monte_carlo.thetac import thetac


def test_thetac():
    # arrange
    NUNITS = 3
    THET = np.array([0.3, 0.5, 0.7])
    LT = np.array([2, 0, 1])
    # act
    THETC = thetac(THET, LT)
    # assert
    assert THETC.size == NUNITS
    assert np.array_equal(THETC, np.array([0.5, 0.0, 0.3]))
