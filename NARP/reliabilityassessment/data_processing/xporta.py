import numpy as np


# vectorized version
def xporta(JENT, INTCH, HRLOAD):
    """
    Add power interchanges based on contracts to hourly load for each area

    :param numpy.ndarray JENT: 2D array of contract number with shape (NOAREA, NOAREA)
        the (i,j)-th element specifies the contract number between area-i and area-j.
    :param numpy.ndarray INTCH: 2D array of the contract content with shape
        (total number of contracts, 365). (``JENT[i,j]``, k)-th element means the
        contracted power (MW) on the kth day from area-i to area-j.
    :param numpy.ndarray HRLOAD: 2D array of hourly load (MW) with shape (NOAREA, 8760)

    .. note:: All input arrays are modified in-place;
              Contracts always specify daily power transfer from high-indexed area
              to low-indexed area.
    """
    for j1, j2 in zip(*np.nonzero(JENT != -1)):
        contract_id = JENT[j1, j2]
        for day in np.nonzero(INTCH[contract_id])[0]:
            HRLOAD[j1, day * 24 : (day + 1) * 24] += INTCH[contract_id, day]
            HRLOAD[j2, day * 24 : (day + 1) * 24] -= INTCH[contract_id, day]


# original version
def _xporta(JENT, INTCH, HRLOAD):
    NOAREA = HRLOAD.shape[0]
    for j1 in range(NOAREA):
        for j2 in range(NOAREA):
            if JENT[j1, j2] == -1:
                continue
            contractIdx = JENT[j1, j2]
            for k in range(365):
                if INTCH[contractIdx, k] == 0:
                    continue
                k1 = k * 24
                k2 = k1 + 24
                for k3 in range(k1, k2):
                    HRLOAD[j1, k3] = HRLOAD[j1, k3] + INTCH[contractIdx, k]
                    HRLOAD[j2, k3] = HRLOAD[j2, k3] - INTCH[contractIdx, k]
