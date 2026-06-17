import numpy as np


def lstate(ILSEED, PROBL):
    """Establishes the line state according the probability of the line being in
    each particular state. This implementation assumes the lines can be in up to 6
    states overall.

    :param array ILSEED: list of seeded random numbers for line state sampling
    :param numpy.ndarray PROBL: array of the cumulative capacity probability of
        each line
    :return: (*numpy.ndarray*) -- array of line state value (in integer) of each line
    .. note:: the purpose of using 'ILSEED' is to mimic the random number generating
        procedure in Fortran to guarantee the same pseudo random sequence being
        generated.
    """

    if not isinstance(PROBL, np.ndarray):
        raise TypeError("PROBL must be a numpy array")

    NLINES = PROBL.shape[1]
    LNSTAT = np.zeros(NLINES, dtype=np.int32)

    for i in range(NLINES):
        # Draw a random number for each line
        ILSEED[i] *= 65539
        if ILSEED[i] < 0:
            ILSEED[i] += 2147483647
            ILSEED[i] += 1
        YFL = float(ILSEED[i])
        YFL *= 0.4656613e-9
        RANDLi = YFL

        # Determine the State of each line.
        if RANDLi <= PROBL[0, i]:
            LNSTAT[i] = 1
        elif RANDLi <= PROBL[1, i]:
            LNSTAT[i] = 2
        elif RANDLi <= PROBL[2, i]:
            LNSTAT[i] = 3
        elif RANDLi <= PROBL[3, i]:
            LNSTAT[i] = 4
        elif RANDLi <= PROBL[4, i]:
            LNSTAT[i] = 5
        else:
            LNSTAT[i] = 6

    return LNSTAT
