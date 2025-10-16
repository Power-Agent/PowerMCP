import numpy as np

from reliabilityassessment.monte_carlo.sumcap import sumcap


def test_sumcap():
    # arrange
    AVAIL = np.array([100, 50, 150])
    CAPOWN = np.array([[1, 0.5, 0], [0, 0.5, 1]])
    CAPCON = np.array([0, 0, 1])
    # act
    CAPAVL, SYSOWN, SYSCON, TRNSFJ = sumcap(AVAIL, CAPOWN, CAPCON)
    # assert
    assert np.array_equal(CAPAVL, np.array([[100.0, 25.0, 0.0], [0.0, 25.0, 150.0]]))
    assert np.array_equal(SYSOWN, np.array([125.0, 175.0]))
    assert np.array_equal(SYSCON, np.array([150.0, 150.0]))
    assert np.array_equal(TRNSFJ, np.array([25.0, -25.0]))
