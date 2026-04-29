import numpy as np


def sumcap(AVAIL, CAPOWN, CAPCON):
    """
    Determine the total available capacity for each system (area).

    :param numpy.ndarray AVAIL: array of the finalized power capacity
        (in nominal value) of each unit
    :param numpy.ndarray CAPOWN: 2D array, the (j,i) th element means
        the fraction of unit i owned by area j.
    :param numpy.ndarray CAPCON: 1D array of length NUINT; the CAPCON[i] means the area
        that the ith generator physically resides in.
    :return: (*tuple*) -- CAPAVL: 2D array, the (j,i) th element means the
                                  the fraction (available) capacity of the ith
                                  generator owned by the jth area
                          SYSOWN: the genuine/net capacity owned by each area.
                          SYSCON: the literal capacity owned by each area.
                          TRNSFJ: the capacity transferred out to the rest area(s)
                                  from the current system (area)
    """

    # Split Capacity by Ownership.
    NOAREA, NUNITS = CAPOWN.shape

    CAPAVL = np.multiply(CAPOWN, AVAIL.T)

    SYSOWN = np.sum(CAPAVL, axis=1)

    SYSCON = np.zeros(NOAREA)

    for i in range(NUNITS):
        j = CAPCON[i]
        SYSCON[j] = SYSCON[j] + AVAIL[i]

    TRNSFJ = SYSCON - SYSOWN

    return CAPAVL, SYSOWN, SYSCON, TRNSFJ
