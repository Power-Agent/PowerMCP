import numpy as np


def admitb(LP, BLP):
    """
    Construct the admittance matrix (B) from the line data array (BLP)

    :param numpy.ndarray LP: 2D array with shape (NLINES, 3)
                             LP[I, 0]: line number, set to I
                             LP[I, 1]: starting node
                             LP[I, 2]: ending node
    :param numpy.ndarray BLP: 2D array with shape (NLINES, 3)
                              BLP[I, 0]: admittance of the line at the Ith entry of LP
                              BLP[I, 1]: capacity (MW)
                              BLP[I, 2]: backward capacity (MW)
    :return: (*numpy.ndarray*) -- BB: 2D array with shape (NOAREA, NOAREA)
        B Matrix in DC power flow
    """

    NLINES = LP.shape[0]
    NOAREA = 1 + LP[:, 1:].max()
    BB = np.zeros((NOAREA, NOAREA))
    for i in range(NLINES):
        j = LP[i, 1]  # from-bus (area) id
        k = LP[i, 2]  # to-bus (area) id
        BB[j, k] += BLP[i, 0] * (-1.0)
        BB[k, j] = BB[j, k]
        BB[j, j] += BLP[i, 0]
        BB[k, k] += BLP[i, 0]

    return BB
