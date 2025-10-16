import numpy as np


def theta(Z, INJ):
    """
    Compute node angles for nodes of ZBus impedance matrix.

    :param numpy.ndarray Z: Zbus impedence matrix
    :param numpy.ndarray INJ:  bus injection vector
    :return: (*numpy.ndarray*) -- THET: node angles vector
    """
    THET = np.dot(Z, INJ)
    return THET
