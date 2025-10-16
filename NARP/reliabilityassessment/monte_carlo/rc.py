import numpy as np


def rc(M, PY, A, IND):
    """
    A vector dot-producting a specified column of a matrix

    :param int M: the specified range for the matrix (to be multiplied)
    :param numpy.ndarray PY: the input 1D vector with shape (M, )
    :param numpy.ndarray A: the input matrix (to be multiplied)
        the row/col size of which could be larger than M.
    :param int IND: the specified column index of matrix A
    :return: (*float*) -- the product result
    """
    return np.dot(PY[:M], A[:M, IND])
