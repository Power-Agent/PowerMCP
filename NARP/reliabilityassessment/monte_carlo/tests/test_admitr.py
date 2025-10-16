import numpy as np

from reliabilityassessment.monte_carlo.admitr import _admitr, admitr


def test_admitr():
    BB = np.array([[1.5, -0.5, -0.5], [-0.5, 2.5, -1.0], [-0.5, -1.0, 3.0]])
    BN = np.array(
        [[0, 50.0, 100.0, 100.0], [1, 50.0, 100.0, 100.0], [2, 50.0, 100.0, 100.0]]
    )
    NR = 1  # delibrately use 1 here since this is an artificially created test case

    # vanilla version
    BB, LT = _admitr(BB, BN, NR)
    np.testing.assert_array_equal(
        BB, np.array([[1.5, -0.5, 0.0], [-0.5, 3.0, 0.0], [0.0, 0.0, 0.0]])
    )
    np.testing.assert_array_equal(LT, np.array([0, 2, 1], dtype=int))

    # vectorized version
    BB = np.array([[1.5, -0.5, -0.5], [-0.5, 2.5, -1.0], [-0.5, -1.0, 3.0]])

    BB, LT = admitr(BB, BN, NR)
    # np.testing.assert_array_equal(BB, np.array([[1.5, -0.5], [-0.5, 3.0]]))
    np.testing.assert_array_equal(
        BB, np.array([[1.5, -0.5, 0.0], [-0.5, 3.0, 0.0], [0.0, 0.0, 0.0]])
    )
    np.testing.assert_array_equal(LT, np.array([0, 2, 1], dtype=int))
