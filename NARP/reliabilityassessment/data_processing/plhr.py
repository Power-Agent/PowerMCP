import numpy as np


def plhr(HRLOAD):
    """
    Find peak hours for all areas.

    :param numpy.ndarray HRLOAD: 2D array of hourly load data (0-dim: area,
        1-dim: hour, 1~8760)
    :return: (*numpy.ndarray*) -- MXPLHR, integer array of peak hour for all areas
        with shape (365,)

    .. note:: Number of days in a year and number of hours for each day is hardcoded
        by 365 and 24, given the Monte Carlo simulation in reliability analysis
        simulates a statistic year and calculates average reliability index,
        which gives a general measure of the studied system.
    """

    # sum across all areas
    summed_load = HRLOAD.sum(axis=0)
    # reshape 8760-length 1D array to N x 24 (N computed automatically)
    reshaped_load = summed_load.reshape((-1, 24))
    # select the index of the greatest value for each day
    daily_peak_hour = reshaped_load.argmax(axis=1)
    # translate hour-of-day to hour-of-year
    MXPLHR = daily_peak_hour + 24 * np.arange(len(daily_peak_hour))

    return MXPLHR
