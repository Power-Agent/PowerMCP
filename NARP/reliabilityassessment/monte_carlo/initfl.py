import numpy as np


def initfl():
    """
    Initialize array EVNTS and several related pointers

    return (*tuple*) -- MFA: pointer of first available (i.e. unoccupied) slot
                             in the event list
                        IPOINT: pointer of the first already occupied slot
                                (i.e. an stored entry) in the event list initial
                                value = -1
                        EVNTS: 1D array of event list
    """

    MFA = 0
    IPOINT = -1
    # this value is predefined and adjustable; it won't change during simulation.
    MXCELL = 100
    EVNTS = np.zeros(MXCELL)

    # array slots starting from MXCELL – 4 (1-based index) are 0 after initialization.
    EVNTS[: MXCELL - 4 : 4] = np.arange(0, MXCELL - 4, 4) + 4

    return MFA, IPOINT, EVNTS
