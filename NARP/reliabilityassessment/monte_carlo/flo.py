import numpy as np


def flo(LP, BLP, THET):
    """
    Compute line power flows and bus (power) injection

    :param numpy.ndarray LP: 2D array with shape (NLINES, 3)
                             LP[I, 0]: line number, set to I
                             LP[I, 1]: starting node
                             LP[I, 2]: ending node
    :param numpy.ndarray BLP: 2D array with shape (NLINES, 3)
                              BLP[I, 0]: admittance of the line at the Ith entry of LP
                              BLP[I, 1]: capacity (MW)
                              BLP[I, 2]: backward capacity (MW)
    :param numpy.ndarray THET: bus (area) angle, shape: (NOAREA, )
    :return: (*tuple*)  -- SFLOW: vector of bus (area) injection power (MW), shape:
                                  (NOAREA, )
                           FLOW: vector of line power flows (MW),  shape: (NLINES, )
    """

    NLINES = LP.shape[0]
    NOAREA = len(THET)
    SFLOW = np.zeros((NOAREA,))
    FLOW = np.zeros((NLINES,))

    for i in range(NLINES):
        j = LP[i, 1]  # from bus (area)
        k = LP[i, 2]  # to bus (area)
        FLOW[i] = (THET[j] - THET[k]) * BLP[i, 0]
        SFLOW[k] += FLOW[i]
        SFLOW[j] -= FLOW[i]

    return SFLOW, FLOW
