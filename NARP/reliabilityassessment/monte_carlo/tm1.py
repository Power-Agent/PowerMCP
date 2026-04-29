import numpy as np

from reliabilityassessment.monte_carlo.admitb import admitb
from reliabilityassessment.monte_carlo.admitr import admitr


def tm1(BN, LP, BLP, NR):
    """
    Calculate nodal admittance matrix, Y Matrix (B Matrix in DC power flow), and
    its inverse

    :param numpy.ndarray BN: 2D array with shape (NOAREA, 5)
                             BN[I, 0]: area (i.e., bus) number
                             BN[I, 1]: load (MW) at area I; will be overridden by net
                                       injection after calling :py:func: `tm2`
                             BN[I, 2]: net injection (generation)(MW) at area I; will be
                                       overridden by load curtailment after calling
                                       :py:func: `tm2`
                             BN[I, 3]: max power flow (MW) allowed at area I
                             BN[I, 4]: a helper value to store modified
                                       "constraint on sum of flows" at the area I
    :param numpy.ndarray LP: 2D array with shape (NLINES, 3)
                             LP[I, 0]: line number, set to I
                             LP[I, 1]: starting node
                             LP[I, 2]: ending node
    :param numpy.ndarray BLP: 2D array with shape (NLINES, 3)
                              BLP[I, 0]: admittance of the line at the Ith entry of LP
                              BLP[I, 1]: capacity (MW)
                              BLP[I, 2]: backward capacity (MW)
    :param int NR: index number of the reference node.
    :return: (*tuple*) -- BLP0: 1D array with shape (NLINES, )
                                intermediate copy of the 1st column of BLP
                          BB: 2D array with shape (NOAREA, NOAREA)
                              B Matrix without reference bus in DC power flow
                          LT: 1D array with shape (NOAREA, )
                              original node index of reduced B matrix, ``BB``
                          ZB: 2D array with shape (NOAREA, NOAREA)
                              inverse matrix of reduced B matrix, ``BB``
    """
    NOAREA = BN.shape[0]
    NX = NOAREA - 1
    BLP0 = BLP[:, 0].copy()
    BB = admitb(LP, BLP)  # generate B matrix
    BB, LT = admitr(BB, BN, NR)  # generate B matrix without ref bus

    ZB = np.linalg.inv(BB[:NX, :NX])
    ZB = np.pad(ZB, ((0, 1), (0, 1)))

    return BLP0, BB, LT, ZB
