import numpy as np


def xldnew(FileNameAndPath, PKLOAD):
    """
    Read and parse raw text data from the input file 'LEEI' (load profile in EEI format)
    and normalize to per unit load profile. Then, re-scale it based on the user-defined
    annual peak of each area.

    :param str FileNameAndPath: full file path for the input file 'LEEI '
    :param np.arrays PKLOAD: array of user-defined annual peak of each area.
    :return: (*np.arrays*) HRLOAD -- 2D array of hourly load data
                                     (0-dim: area index, 1-dim: hour index)

    .. note:: the hardcoded number "8760" is OK in this code package.
        Because for Monte Carlo Simulation in reliability analysis area, researchers does not
        try to simulate "real-life year", but purely for statistic purpose. In fact,
        each reliability index is eventually an averaged number. So, the leap year is not
        a concern in this area.
    """

    # Read file LEEI and parsing
    with open(FileNameAndPath, "r") as f:
        Lines = f.readlines()

    HRLOAD = np.zeros((len(PKLOAD), 8760))

    for line in Lines:
        if line[:4] == "AREA":
            areaIdx = int(line[6]) - 1
            hourIdx = 0
        else:
            HRLOAD[areaIdx, hourIdx : hourIdx + 12] = list(
                map(float, line.strip().split())
            )[-12:]
            hourIdx += 12

    # Normalize and re-scale the annual load data of each area
    HRLOAD = (
        HRLOAD
        / np.amax(HRLOAD, axis=1, initial=0.001)[:, np.newaxis]
        * PKLOAD[:, np.newaxis]
    )

    return HRLOAD
