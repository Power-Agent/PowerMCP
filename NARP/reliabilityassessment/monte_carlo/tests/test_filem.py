import numpy as np

from reliabilityassessment.monte_carlo.filem import filem


def test_filem():
    # Note that: based on the original logic and design of EVNT list (array),
    # its length is multiple of 4 and its last 4 slots are always zeros;

    # case-1: the event list is empty
    MFA = 0
    NUMINQ = 0
    IPOINT = -1
    EVNTS = np.array([4, 0.0, 0, 0, 8, 0.0, 0, 0, 12, 0.0, 0, 0, 0, 0.0, 0, 0])
    ATRIB = np.array([1.5, 3])

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)
    assert NUMINQ == 1
    assert MFA == 4
    assert IPOINT == 0
    EVNTS_true = np.array([-1, 1.5, 3, 0, 8, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0])
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # case-2: new entry is the first
    MFA = 4
    NUMINQ = 1
    IPOINT = 0
    EVNTS = np.array([-1, 1.5, 3, 0, 8, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0])
    ATRIB = np.array([0.5, 2])

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)
    assert NUMINQ == 2
    assert MFA == 8
    assert IPOINT == 4
    EVNTS_true = np.array([-1, 1.5, 3, 0, 0, 0.5, 2, 0, 12, 0, 0, 0, 0, 0, 0, 0])
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # case-3: new entry is the last
    MFA = 8
    NUMINQ = 2
    IPOINT = 4
    EVNTS = np.array([-1, 1.5, 3, 0, 0, 0.5, 2, 0, 12, 0, 0, 0, 0, 0, 0, 0])
    ATRIB = np.array([2.5, 1])

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)
    assert NUMINQ == 3
    assert MFA == 12
    assert IPOINT == 4
    EVNTS_true = np.array([8, 1.5, 3, 0, 0, 0.5, 2, 0, -1, 2.5, 1, 0, 0, 0, 0, 0])
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # case-4: new entry is in the middle
    MFA = 8
    NUMINQ = 2
    IPOINT = 4
    EVNTS = np.array([-1, 1.5, 3, 0, 0, 0.5, 2, 0, 12, 0, 0, 0, 0, 0, 0, 0])
    ATRIB = np.array([1.0, 1])

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)
    assert NUMINQ == 3
    assert MFA == 12
    assert IPOINT == 4
    EVNTS_true = np.array([-1, 1.5, 3, 0, 8, 0.5, 2, 0, 0, 1.0, 1, 0, 0, 0, 0, 0])
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)
