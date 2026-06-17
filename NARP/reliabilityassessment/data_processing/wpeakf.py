import numpy as np


# vanilla version
def _wpeakf(DYLOAD):
    """
    Finds weekly peaks (MW)

    :param numpy.ndarray DYLOAD: 2D array, daily peak load amount (MW)
                               1st dim: areaIdx, 2nd dim: dayIdx

    :return: (*numpy.ndarray*) WPEAK -- 2D array, weekly peak load amount (MW)
               1st dim: areaIdx, 2nd dim: weekIdx
    """
    NOAREA = DYLOAD.shape[0]
    WPEAK = np.zeros((NOAREA, 52))
    # 52 weeks in one year is a fixed value in our program

    for areaIdx in range(NOAREA):
        for weekIdx in range(52):
            XMAX = float("-Inf")
            JW = 7
            if (
                weekIdx == 51
            ):  # since 365 day in one year is a fixed value in our program;
                JW = 8  # thus, the 'last week' has '8 days'
            for j in range(JW):
                j1 = weekIdx * 7 + j
                if DYLOAD[areaIdx, j1] > XMAX:
                    XMAX = DYLOAD[areaIdx, j1]
            WPEAK[areaIdx, weekIdx] = XMAX
    return WPEAK


# vectorized version
def wpeakf(DYLOAD):
    """
    Finds weekly peaks (MW)

    :param numpy.ndarray DYLOAD: 2D array, daily peak load amount (MW)
                               1st dim: areaIdx, 2nd dim: dayIdx

    :return: (*numpy.ndarray*) WPEAK -- 2D array, weekly peak load amount (MW)
               1st dim: areaIdx, 2nd dim: weekIdx
    """
    WPEAK = np.reshape(DYLOAD[:, :-1], (DYLOAD.shape[0], 52, 7)).max(axis=2)
    WPEAK[:, -1] = np.maximum(WPEAK[:, -1], DYLOAD[:, -1])
    return WPEAK
