from copy import deepcopy

import numpy as np

from reliabilityassessment.data_processing.xporta import _xporta, xporta


def test_xporta():
    NOAREA = 3

    JENT = (-1) * np.ones((NOAREA, NOAREA), dtype=int)
    NO_CONTRACTS = 0
    JENT[1, 0] = 0
    NO_CONTRACTS += 1
    JENT[2, 1] = 1
    NO_CONTRACTS += 1

    # NO_CONTRACTS = 2
    INTCH = np.zeros((NO_CONTRACTS, 365))
    INTCH[0, 0:30] = 110.5  # MW
    INTCH[1, 20:80] = 120.5  # MW

    HRLOAD = np.random.random((NOAREA, 8760))
    HRLOAD1 = deepcopy(HRLOAD)
    np.testing.assert_array_equal(HRLOAD, HRLOAD1)  # make sure the copy works

    _xporta(JENT, INTCH, HRLOAD)  # original version
    xporta(JENT, INTCH, HRLOAD1)  # vectorized version
    np.testing.assert_array_equal(HRLOAD, HRLOAD1)
