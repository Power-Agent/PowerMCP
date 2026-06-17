import numpy as np


def ximpa(ZB, ZIJ, NI, NJ):
    """
    Modifies ZBUS matrix if ZIJ added between bus NI,NJ

    :param numpy.ndarray ZB: the input ZBUS matrix  (dim: areas-by-areas)
    :param int ZIJ: the impedance to be added to the system between bus NI,NJ
    :param int NI: from bus id of the newly added branch (0-based index)
    :param int NJ: to bus id of the newly added branch (0-based index)
    :return: (*numpy.ndarray*) -- the modified ZBUS matrix (dim: areas-by-areas)
    """

    ZCOL = ZB[:, NI] - ZB[:, NJ]
    ZN1 = ZB[NI, NI] + ZB[NJ, NJ] - 2.0 * ZB[NI, NJ] - ZIJ
    return ZB - np.outer(ZCOL, ZCOL) / ZN1
