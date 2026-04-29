from bisect import bisect_left

import numpy as np


def gstate(IGSEED, PROBG, RATING, DERATE, PLNDST):
    """
    It samples the state of available capacity for each generator up to NUNITS

    :param numpy.ndarray IGSEED: list of seeded random numbers for generator state
        sampling
    :param numpy.ndarray PROBG: 2D array of accumulated probability for each capacity
        tier of each unit
    :param numpy.ndarray RATING: array of the fully rated capacity of each unit
    :param numpy.ndarray DERATE: array of the derated capacity of each unit
    :param numpy.ndarray PLNDST: array of the on/off status (due to planned
        maintenance) of each unit
    :return: (*tuple*) -- PCTAVL: array of unadjusted power capacity (in p.u.
        value) of each unit; AVAIL: array of the finalized power capacity (
        in nominal value) of each unit
    .. note:: the purpose of using 'IGSEED' is to mimic the random number generating
        procedure in Fortran to guarantee the same pseudo random sequence being
        generated.
    """
    NUNITS = len(PROBG)
    # print("Enter subroutine gstate, total number of Gen units is %d" % (NUNITS))

    PCTAVL = np.zeros(NUNITS)
    AVAIL = np.zeros(NUNITS)

    for i in range(NUNITS):
        # Draw a random number for each gen unit
        IGSEED[i] *= 65539
        if IGSEED[i] < 0:
            IGSEED[i] += 2147483647
            IGSEED[i] += 1
        YFL = float(IGSEED[i])
        YFL *= 0.4656613e-9
        RANDGi = YFL

        # Determine the State and Available Capacity for Each Generator.
        if RANDGi < PROBG[i, 0]:
            PCTAVL[i] = 1.0  # normalized value for gen. capacity is used here
        elif RANDGi < PROBG[i, 1]:
            PCTAVL[i] = DERATE[i]  # normalized value for gen. capacity is used here
        else:
            PCTAVL[i] = 0

        AVAIL[i] = PCTAVL[i] * RATING[i] * PLNDST[i]

    return PCTAVL, AVAIL


def _gstate(PROBG, RATING, DERATE, PLNDST, rng=np.random.default_rng()):
    """
    Sample the state of available capacity for each generator up to NUNITS

    :param numpy.ndarray PROBG: 2D array of accumulated probability for each capacity
        tier of each unit
    :param numpy.ndarray RATING: array of the fully rated capacity of each unit
    :param numpy.ndarray DERATE: array of the derated capacity of each unit
    :param numpy.ndarray PLNDST: array of the on/off status (due to planned maintenance)
        of each unit
    :return: (*tuple*) -- a pair of numpy.ndarray objects for unadjusted power
        capacity in p.u. of each unit and finalized power capacity in MW of each unit.
    """

    NUNITS = len(PROBG)
    # print("Enter function gstate, total number of Gen units is %d" % (NUNITS))

    PCTAVL = np.zeros((NUNITS, 1))
    AVAIL = np.zeros((NUNITS, 1))

    # Vectorized operation utilizing the bisect API
    aux = {i: {0: 1, 1: d, 2: 0} for i, d in enumerate(DERATE)}
    PCTAVL = np.array(
        [aux[i][bisect_left(PROBG[i], x)] for i, x in enumerate(rng.random(len(PROBG)))]
    )
    AVAIL = (PCTAVL * RATING * PLNDST).reshape(-1, 1)

    return PCTAVL, AVAIL
