import numpy as np


def resca(SUSTAT, MAXDAY, QTR, CAPOWN, RATES, JENT, INTCH):
    """
    Calculate the total owned capacity with peak interchange and seasonal effects

    :param numpy.ndarray SUSTAT: statistics of each area with shape (NOAREA+1, 6)
                                 SUSTAT(J,0): total load (MW), initialized by PKLOAD(J)
                                 SUSTAT(J,1): total generation (MW)
                                 SUSTAT(J,2): loss of power (MW), XLOL
                                 SUSTAT(J,3): intermediate value (MW),
                                    e.g.: (SUSTAT(I,2)-SUSTAT(I,1))/SUSTAT(I,1)*100,
                                    i.e., total owned net capacity
                                 SUSTAT(J,4): loss of load probability, XLOLP
                                 SUSTAT(J,5): loss of energy (MWh), EUE (expected
                                    unserved energy), the last row is kept for total
                                    statistic purpose.
    :param numpy.ndarray MAXDAY: index of the day in a year with maximum daily peak,
        shape (NOAREA, )
    :param numpy.ndarray QTR: quarterly index (in units of hours) with shape (3, )
        e.g. [13*168+0.5, 13*2*168+0.5, 13*3*168+0.5]
    :param numpy.ndarray CAPOWN: shape (NOAREA, NUNITS), the (j, i)th element means
        the fraction of unit i owned by area j.
    :param numpy.ndarray RATES: shape (NUNITS, 4), (i, j)th element means the rated
        power (MW) of unit i in the j-th season.
    :param numpy.ndarray JENT: 2D array of pointer identifying a specific contract with
        shape (NOAREA, NOAREA), the (i, j)th element means the contract (no.)
        between area i and area j.
    :param numpy.ndarray INTCH: 2D array of the contract content with shape (total
        number of contracts, 365), the (JENT[i, j], k)th element means the contracted
        power (MW) on the kth day from area i to area j.

    .. note:: SUSTAT is modified in place.
    """
    NUINTS = CAPOWN.shape[1]
    NOAREA = SUSTAT.shape[0] - 1
    for i in range(NOAREA):
        IDAY = MAXDAY[i]
        IPER = np.argmax(QTR > IDAY * 24)
        for j in range(NUINTS):
            SUSTAT[i, 1] += CAPOWN[i, j] * RATES[j, IPER]

        SUSTAT[i, 1] -= INTCH[JENT[i, :][JENT[i, :] != -1], IDAY].sum()
        SUSTAT[i, 1] += INTCH[JENT[:, i][JENT[:, i] != -1], IDAY].sum()


def _resca(SUSTAT, MAXDAY, QTR, CAPOWN, RATES, JENT, INTCH):
    """
    Calculate the total owned capacity with peak interchange and seasonal effects

    :param numpy.ndarray SUSTAT: statistics of each area with shape (NOAREA+1, 6)
                                 SUSTAT(J,0): total load (MW), initialized by PKLOAD(J)
                                 SUSTAT(J,1): total generation (MW)
                                 SUSTAT(J,2): loss of power (MW), XLOL
                                 SUSTAT(J,3): intermediate value (MW),
                                    e.g.: (SUSTAT(I,2)-SUSTAT(I,1))/SUSTAT(I,1)*100,
                                    i.e., total owned net capacity
                                 SUSTAT(J,4): loss of load probability, XLOLP
                                 SUSTAT(J,5): loss of energy (MWh), EUE (expected
                                    unserved energy), the last row is kept for total
                                    statistic purpose.
    :param numpy.ndarray MAXDAY: index of the day in a year with maximum daily peak,
        shape (NOAREA, )
    :param numpy.ndarray QTR: quarterly index (in units of hours) with shape (3, )
        e.g. [13*168+0.5, 13*2*168+0.5, 13*3*168+0.5]
    :param numpy.ndarray CAPOWN: shape (NOAREA, NUNITS), the (j, i)th element means
        the fraction of unit i owned by area j.
    :param numpy.ndarray RATES: shape (NUNITS, 4), (i, j)th element means the rated
        power (MW) of unit i in the j-th season.
    :param numpy.ndarray JENT: 2D array of pointer identifying a specific contract with
        shape (NOAREA, NOAREA), the (i, j)th element means the contract (no.)
        between area i and area j.
    :param numpy.ndarray INTCH: 2D array of the contract content with shape (total
        number of contracts, 365), the (JENT[i, j], k)th element means the contracted
        power (MW) on the kth day from area i to area j.

    .. note:: SUSTAT is modified in place.
    """

    NOAREA = SUSTAT.shape[0] - 1
    for i in range(NOAREA):
        IDAY = MAXDAY[i]
        IHR = IDAY * 24
        IPER = 0

        if IHR > QTR[0]:
            IPER = 1

        if IHR > QTR[1]:
            IPER = 2

        if IHR > QTR[2]:
            IPER = 3

        NUINTS = CAPOWN.shape[1]
        for j in range(NUINTS):
            SUSTAT[i, 1] += CAPOWN[i, j] * RATES[j, IPER]

        for j1 in range(NOAREA):
            if JENT[i, j1] != -1:
                IP = JENT[i, j1]
                SUSTAT[i, 1] -= INTCH[IP, IDAY]

            if JENT[j1, i] != -1:
                IP = JENT[j1, i]
                SUSTAT[i, 1] += INTCH[IP, IDAY]
