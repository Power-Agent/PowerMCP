import copy

import numpy as np

from reliabilityassessment.data_processing.resca import _resca, resca


def test_resca():
    np.random.seed(1)

    NOAREA = 3
    NUNITS = 5

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

    MAXDAY = np.array([1, 92, 183])
    SUSTAT = np.random.random((NOAREA, 6))
    SUSTAT = np.vstack([SUSTAT, [0, 0, 0, 0, 0, 0]])
    QTR = np.array([13 * 168 + 0.5, 13 * 2 * 168 + 0.5, 13 * 3 * 168 + 0.5])
    RATES = np.random.random((NUNITS, 3))
    CAPOWN = np.array([[1.0, 0.5, 0, 0, 0], [0, 0.5, 1.0, 0.4, 0], [0, 0, 0, 0.6, 1.0]])

    SUSTAT_copy = copy.deepcopy(SUSTAT)
    SUSTAT_1_truth = np.array([111.84484222, 1.46481165, 2.36289247, 0.0])

    _resca(SUSTAT, MAXDAY, QTR, CAPOWN, RATES, JENT, INTCH)
    np.testing.assert_array_almost_equal(SUSTAT[:, 1], SUSTAT_1_truth)

    resca(SUSTAT_copy, MAXDAY, QTR, CAPOWN, RATES, JENT, INTCH)
    np.testing.assert_array_almost_equal(SUSTAT_copy[:, 1], SUSTAT_1_truth)
