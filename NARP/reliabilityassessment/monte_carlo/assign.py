import numpy as np


def _assign(INJ, LOD, LT, NN, NLS):
    """
    Assigns injections at buses so as to balance positive and negative injections

    :param numpy.ndarray INJ: 1D array of input injections
    :param numpy.ndarray LOD: 1D array of loads with shape (NLINES, )
    :param numpy.ndarray LT: 1D array with shape (NN, ) (i.e., NOAREA)
        LT[I] contains the actual node index corresponding to node I of the reduced
        admittance matrix
    :param int NN: user-specified dimension for the arrays
    :param int NLS: indicator of loss sharing mode, 0: LOSS SHARING, 1: NO LOSS SHARING
    :return: (*tuple*) -- a pair of numpy arrays, INJ1: vector of modified injections
        with shape (NN, ), LODC: vector of load curtailments with shape (NN, )
    """

    LODC = np.zeros(NN)
    INJ1 = INJ[:NN].copy()

    SUMN = 0.0
    SUMP = 0.0

    SUMN = sum(e for e in INJ1 if e <= 0)
    SUMP = sum(e for e in INJ1 if e > 0)

    SUMN = abs(SUMN)
    if SUMN <= SUMP:
        INJ1 = [e * SUMN / SUMP if e > 0 else e for e in INJ1]
        return INJ1, LODC

    if NLS != 0:
        for i in range(NN):
            if INJ1[i] > 0:
                continue
            PINT = INJ1[i]
            INJ1[i] = INJ1[i] * SUMP / SUMN
            J = LT[i]
            LODC[J] = INJ1[i] - PINT
        return INJ1, LODC

    SUML = sum(LOD[:NN])

    DIFF = SUMN - SUMP
    LODC[LT[:NN]] = LOD[LT[:NN]] * DIFF / SUML
    INJ1[:NN] += LODC[LT[:NN]]

    return INJ1, LODC


# vectorized version:
def assign(INJ, LOD, LT, NN, NLS):
    """
    Assigns injections at buses so as to balance positive and negative injections

    :param numpy.ndarray INJ: 1D array of input injections
    :param numpy.ndarray LOD: 1D array of loads with shape (NLINES, )
    :param numpy.ndarray LT: 1D array with shape (NN, ) (i.e., NOAREA)
        LT[I] contains the actual node index corresponding to node I of the reduced
        admittance matrix
    :param int NN: user-specified dimension for the arrays
    :param int NLS: indicator of loss sharing mode, 0: LOSS SHARING, 1: NO LOSS SHARING
    :return: (*tuple*) -- a pair of numpy arrays, INJ1: vector of modified injections
        with shape (NN, ), LODC: vector of load curtailments with shape (NN, )
    """

    LODC = np.zeros(NN)
    INJ1 = INJ[:NN].copy()

    SUMN = abs(sum(INJ1[INJ1 <= 0]))
    SUMP = sum(INJ1[INJ1 > 0])

    SUMN = abs(SUMN)
    if SUMN <= SUMP:  # (Positive injection is larger)
        INJ1[INJ1 > 0] *= SUMN / SUMP if SUMP > 0 else 1
    elif NLS != 0:  # (Negative injection is larger and no loss sharing)
        PINT = INJ1[INJ1 <= 0].copy()
        INJ1[INJ1 <= 0] *= SUMP / SUMN
        LODC[LT[INJ1 <= 0]] = INJ1[INJ1 <= 0] - PINT
    else:  # (Negative injection is larger and loss sharing)
        SUML = sum(LOD[:NN])
        DIFF = SUMN - SUMP
        LODC[LT] = LOD[LT] * DIFF / SUML
        INJ1 += LODC[LT]

    return INJ1, LODC
