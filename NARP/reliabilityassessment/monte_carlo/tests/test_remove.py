import numpy as np

from reliabilityassessment.monte_carlo.remove import remove


def test_remove():
    NUMINQ = 1
    ATRIB = np.array([71.0, 3])
    IPOINT = 0
    EVNTS = np.array([4, 61.5, 2, 0, 0, 0, 0, 0])
    MFA, NUMINQ, IPOINT = remove(NUMINQ, ATRIB, EVNTS, IPOINT)

    assert MFA == 0
    assert NUMINQ == 0
    assert IPOINT == 4
    np.testing.assert_array_equal(ATRIB, [61.5, 2])
    np.testing.assert_array_equal(EVNTS, [4, 0, 0, 0, 0, 0, 0, 0])
