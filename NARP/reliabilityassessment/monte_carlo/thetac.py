import numpy as np


def thetac(THET, LT):
    """
    Generate vector of bus angles for all buses including ref bus.

    :param numpy.ndarray THET: angle at every node of the ADM matrix
    :param numpy.ndarray LT: actual node corresponding to node i of the ADM matrix
    :return: (*numpy.ndarray*) -- THETC: angle of actual node corresponding to each
        node of the ADM matrix
    """
    NN = len(THET)
    THETC = np.zeros(NN)

    # last array value is the "reference" bus that ALWAYS has a zero phase angle
    THETC[LT[:-1]] = THET[:-1]
    return THETC
