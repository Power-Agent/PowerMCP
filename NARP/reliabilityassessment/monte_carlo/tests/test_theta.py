import numpy as np

from reliabilityassessment.monte_carlo.theta import theta


def test_theta():
    # arrange
    NUNITS = 2
    Z = np.array([[1, 2], [3, 4]])
    INJ = np.array([[0.2], [0.5]])
    # act
    THET = theta(Z, INJ)
    # assert
    assert THET.size == NUNITS
    assert np.array_equal(THET, np.array([[1.2], [2.6]]))
