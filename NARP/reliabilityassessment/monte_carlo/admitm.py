def admitm(BB, NII, NJJ, BIJ):
    """
    Modify the admittance matrix by an adding an extra admittance
    on a specified branch

    :param numpy.ndarray BB: 2D array with shape (NOAREA, NOAREA), the admittance
        matrix in DC power flow
    :param int NII: specify the from-bus of the impacted branch
    :param int NJJ: specify the to-bus  of the impacted branch
    :param float BIJ: the amount of admittance value to add on

    .. note:: BB is modified in place
    """
    BB[NII, NJJ] -= BIJ
    BB[NJJ, NII] -= BIJ
    BB[NII, NII] += BIJ
    BB[NJJ, NJJ] += BIJ
