import numpy as np

from reliabilityassessment.monte_carlo.initl import _initl


def test_initl():
    EVNTS = np.zeros(32)
    EVNTS[: 32 - 4 : 4] = np.arange(0, 32 - 4, 4) + 4
    MFA = 0
    IPOINT = -1
    NUMINQ = 0
    JSTEP = 1
    QTR = np.array([13 * 168 + 0.5, 13 * 2 * 168 + 0.5, 13 * 3 * 168 + 0.5])

    ATRIB, CLOCK, IPOINT, MFA, NUMINQ = _initl(JSTEP, EVNTS, IPOINT, MFA, NUMINQ, QTR)

    ATRIB_truth = np.array([1.0, 1])
    np.testing.assert_array_almost_equal(ATRIB_truth, ATRIB)

    assert CLOCK == 0.0
    assert IPOINT == 20
    assert MFA == 28
    assert NUMINQ == 7

    EVNTS_truth = np.array(
        [
            24,
            0.5,
            3,
            0,
            8,
            2184.5,
            3,
            0,
            12,
            4368.5,
            3,
            0,
            16,
            6552.5,
            3,
            0,
            -1,
            8760.0,
            4,
            0,
            0,
            0.5,
            2,
            0,
            4,
            1.0,
            1,
            0,
            0,
            0,
            0,
            0,
        ]
    )

    np.testing.assert_array_almost_equal(EVNTS_truth, EVNTS)
