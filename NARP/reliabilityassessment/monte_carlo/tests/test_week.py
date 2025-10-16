import numpy as np

from reliabilityassessment.monte_carlo.week import week


def test_week():
    CLOCK = 12.5
    MFA = 0
    NUMINQ = 0
    IPOINT = -1
    EVNTS = np.array([4, 0, 0, 0, 8, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0], dtype=float)
    ATRIB = np.array([1.5, 1])

    NUNITS = 3
    PLNDST = np.ones((NUNITS,))

    JPLOUT = np.zeros((52, NUNITS + 1), dtype=int)
    JPLOUT[0, 0:3] = [2, 2, 1]
    JPLOUT[1, 0:2] = [1, 2]
    JPLOUT[2, 0:3] = [2, 1, 0]

    JHOUR = 12
    IPOINT, MFA, NUMINQ = week(
        CLOCK, ATRIB, MFA, NUMINQ, IPOINT, EVNTS, PLNDST, JHOUR, JPLOUT
    )
    assert IPOINT == 0
    assert MFA == 4
    assert NUMINQ == 1
    PLNDST_true = np.array([1.0, 0.0, 0.0])
    np.testing.assert_array_almost_equal(PLNDST, PLNDST_true)

    # cover the case when MT == 0
    CLOCK = 1234.5
    JHOUR = 1234
    PLNDST = np.ones((NUNITS,))
    IPOINT, MFA, NUMINQ = week(
        CLOCK, ATRIB, MFA, NUMINQ, IPOINT, EVNTS, PLNDST, JHOUR, JPLOUT
    )
    PLNDST_true = np.ones((NUNITS,))
    np.testing.assert_array_almost_equal(PLNDST, PLNDST_true)

    # cover the case when JWEEK > 51
    CLOCK = 8760.5
    JHOUR = 8760
    PLNDST = np.ones((NUNITS,))
    IPOINT, MFA, NUMINQ = week(
        CLOCK, ATRIB, MFA, NUMINQ, IPOINT, EVNTS, PLNDST, JHOUR, JPLOUT
    )
    PLNDST_true = np.ones((NUNITS,))
    np.testing.assert_array_almost_equal(PLNDST, PLNDST_true)
