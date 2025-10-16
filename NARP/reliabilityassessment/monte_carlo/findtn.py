import numpy as np


def findtn(JENT, INTCH, JDAY):
    """
    Determine (net) inter-area transferred power on a specific JDAY for an
    interested pair of areas based on fixed contracts (if there exists)

    :param numpy.ndarray JENT: 2D array of pointer identifying a specific contract,
        the (i,j)-th element means the contract (no.) between area-i and area-j,
        shape: (NOAREA, NOAREA)
    :param numpy.ndarray INTCH: 2D array of the contract content, the (JENT[i,j],
        k)-th element means the contracted power (MW) on the kth day from area-i to
        area-j, shape: (total numebr of contracts, 365)
    :param int JDAY: integer index for the day
    :return: (*numpy.ndarray*)  TRNSFR: 1D array with shape (NOAREA, ), the ith
        element means the power transferred-out from this area-i to the rest of pool

    .. note:: TRANSFERS treated as from higher to lower area number
    """

    NOAREA = JENT.shape[0]
    TRNSFR = np.zeros((NOAREA,))
    for j1, j2 in zip(*np.nonzero(JENT != -1)):
        JPOINT = JENT[j1, j2]
        TRNSFR[j1] += INTCH[JPOINT, JDAY]
        TRNSFR[j2] -= INTCH[JPOINT, JDAY]
    return TRNSFR
