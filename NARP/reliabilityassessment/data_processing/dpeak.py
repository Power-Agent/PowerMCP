import numpy as np


def _dpeak(HRLOAD, hour_within_day=24):
    """
    Find daily peaks (MW) and hour (index) of those peaks

    :param numpy.ndarray HRLOAD: 2D array of hourly load data
                         (0-dim: area index, 1-dim: hour index (1~8760 hr))

    return (*tuple*) -- a tuple of multiple arrays, i.e.,
                    DYLOAD: 2D array, daily peak load amount (MW)
                    MAXHR: 2D array, the hour-index of the daily peak load for each day of each area
                    (in the range of 0 to 8759; note that the python index starts from 0)
                    MAXDAY: 1D array, the day-index of the daily peak load for each area
    """
    NOAREA = HRLOAD.shape[0]
    day_within_year = HRLOAD.shape[1] // hour_within_day
    DYLOAD = np.zeros((NOAREA, day_within_year))
    MAXHR = np.zeros((NOAREA, day_within_year), dtype=int)
    MAXDAY = np.zeros(NOAREA, dtype=int)

    for areaIdx in range(NOAREA):
        for dayIdx in range(day_within_year):
            XMAX = float("-inf")
            for j in range(hour_within_day):
                j1 = dayIdx * hour_within_day + j
                if HRLOAD[areaIdx, j1] <= XMAX:
                    continue
                XMAX = HRLOAD[areaIdx, j1]
                MAXHR[areaIdx, dayIdx] = j1
            DYLOAD[areaIdx, dayIdx] = XMAX

    for areaIdx in range(NOAREA):
        XMAX = float("-inf")
        for dayIdx in range(day_within_year):
            if DYLOAD[areaIdx, dayIdx] > XMAX:
                XMAX = DYLOAD[areaIdx, dayIdx]
                MAXDAY[areaIdx] = dayIdx

    return MAXHR, DYLOAD, MAXDAY


def dpeak(HRLOAD, hour_within_day=24):
    """
    Find daily peaks (MW) and hour (index) of those peaks

    :param numpy.ndarray HRLOAD: 2D array of hourly load data
                         (0-dim: area index, 1-dim: hour index (1~8760 hr))

    return (*tuple*) -- a tuple of multiple arrays, i.e.,
                    DYLOAD: 2D array, daily peak load amount (MW)
                    MAXHR: 2D array, the hour-index of the daily peak load for each day of each area
                    (in the range of 0 to 8759; note that the python index starts from 0)
                    MAXDAY: 1D array, the day-index of the daily peak load for each area
    """
    NOAREA = HRLOAD.shape[0]

    # reshape (area, hour_within_year) to (area, hour_within_day, day_within_year)
    # note: the 'order' parameter should be 'F' to keep the original internal ordering.
    reshaped = HRLOAD.reshape((NOAREA, hour_within_day, -1), order="F")
    day_within_year = reshaped.shape[2]
    #  i.e., HRLOAD .shape[1] / hour_within_day
    DYLOAD = reshaped.max(axis=1)
    MAXHR = reshaped.argmax(axis=1) + hour_within_day * np.arange(day_within_year)
    MAXDAY = DYLOAD.argmax(axis=1)

    return MAXHR, DYLOAD, MAXDAY
