def rm(M, CB, TAB):
    """
    2D Matrix left-multiplication by a vector within a specified range

    :param int M: the specified range for the matrix (to be multiplied)
    :param numpy.ndarray CB: the input vector (as the be left-multiplier)
        the length of which could be larger than M.
    :param numpy.ndarray TAB: the input matrix (to be multiplied)
        the row/col size of which could be larger than M.
    :return: (*numpy.ndarray*) -- 1D array with shape (M, )
    """
    return CB[:M] @ TAB[:M, :M]
