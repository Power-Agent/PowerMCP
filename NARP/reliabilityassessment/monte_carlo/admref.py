def admref(BB, NII, BIJ):
    """
    Update a specific diagonal element of the (admittance) matrix BB

    :param numpy.ndarray BB: 2D array with shape (NOAREA, NOAREA), B Matrix (i.e.
        admittance matrix) in DC power flow
    :param int NII: specify the position of the diagonal element
    :param float BIJ: the amount of admittance value to add on

    .. note:: BB is modified in place
    """
    BB[NII, NII] += BIJ
