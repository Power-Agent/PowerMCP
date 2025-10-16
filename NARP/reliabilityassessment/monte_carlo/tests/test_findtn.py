import numpy as np

from reliabilityassessment.monte_carlo.findtn import findtn


def test_findtn():
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

    JDAY = 5
    TRNSFR_truth = np.zeros((NOAREA,))
    TRNSFR_truth[0] = -110.5
    TRNSFR_truth[1] = 110.5
    TRNSFR_truth[2] = 0.0
    TRNSFR = findtn(JENT, INTCH, JDAY)
    np.testing.assert_array_almost_equal(TRNSFR, TRNSFR_truth)

    JDAY = 25
    TRNSFR_truth = np.zeros((NOAREA,))
    TRNSFR_truth[0] = -110.5
    TRNSFR_truth[1] = -10.0
    TRNSFR_truth[2] = 120.5
    TRNSFR = findtn(JENT, INTCH, JDAY)
    np.testing.assert_array_almost_equal(TRNSFR, TRNSFR_truth)

    JDAY = 50
    TRNSFR_truth = np.zeros((NOAREA,))
    TRNSFR_truth[0] = 0.0
    TRNSFR_truth[1] = -120.5
    TRNSFR_truth[2] = 120.5
    TRNSFR = findtn(JENT, INTCH, JDAY)
    np.testing.assert_array_almost_equal(TRNSFR, TRNSFR_truth)

    JDAY = 100
    TRNSFR_truth = np.zeros((NOAREA,))
    TRNSFR_truth[0] = 0.0
    TRNSFR_truth[1] = 0.0
    TRNSFR_truth[2] = 0.0
    TRNSFR = findtn(JENT, INTCH, JDAY)
    np.testing.assert_array_almost_equal(TRNSFR, TRNSFR_truth)
