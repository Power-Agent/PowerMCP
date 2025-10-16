import numpy as np


def ximpar(ZB, ZIJ, NI):
    """
    Modifies ZBUS matrix if impedance ZIJ added between bus NI and REF

    :param numpy.ndarray ZB: the input ZBUS matrix  (dim: areas-by-areas)
    :param int ZIJ: the impedance to be added to the system
    :param int NI: from bus id of the newly added branch
    :return: (*numpy.ndarray*) -- the modified ZBUS matrix (dim: areas-by-areas)
    """

    ZCOL = ZB[:, NI]
    ZN1 = ZB[NI, NI] - ZIJ
    return ZB - np.outer(ZCOL, ZCOL) / ZN1
