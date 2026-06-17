def mc(M, IN, TAB, A):
    """
    2D Matrix right-multiplication by a vector, which is a specified column of
    another matrix.

    :param int M: the specified range for the matrix (to be multiplied)
    :param int IN: the specified index of column of matrix A
    :param numpy.ndarray TAB: the input matrix (to be multiplied)
        the row/col size of which could be larger than M.
    :param numpy.ndarray A: the input matrix (to be extracted one specific column)
        the row/col size of which could be larger than M.
    :return: (*numpy.ndarray*) -- the result vector
    """
    return TAB[:M, :M] @ A[:M, IN]
