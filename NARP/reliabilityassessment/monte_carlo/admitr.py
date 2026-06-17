import numpy as np


# vanilla version
def _admitr(BB, BN, NR):
    """
    Remove REF bus (area) from the admittance matrix

    :param numpy.ndarray BB: 2D array with shape (NOAREA, NOAREA) the admittance
        matrix 'B' used in DC power flow, in particular, it contains the entire
        admittance matrix upon input and the REF bus is removed at output
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
    :param int NR: index number of the reference node.
    :return: (*tuple*) -- a pair of numpy arrays, BB and LT
                          BB: 2D array with shape (NOAREA, NOAREA)
                              the 'B matrix without reference bus' in DC power flow
                          LT: 1D array with shape (NOAREA, )
                              array recording the original bus no.
    """

    NN = BB.shape[0]  # total number of buses (i.e., areas)
    NX = NN - 1

    BT = np.zeros((NX, NX))
    LT = np.zeros((NN,), dtype=int)

    ii = 0
    for i in range(NN):
        if i == NR:
            continue
        LT[ii] = BN[i, 0]
        iii = 0
        for j in range(NN):
            if j == NR:
                continue
            BT[ii, iii] = BB[i, j]
            iii += 1
        ii += 1
    LT[NX] = NR

    BB[:NX, :NX] = BT[:, :]
    BB[-1, :] = 0
    BB[0:, -1] = 0

    return BB, LT


# vectorized version
def admitr(BB, BN, NR):
    """
    Remove REF bus (area) from the admittance matrix

    :param numpy.ndarray BB: 2D array with shape (NOAREA, NOAREA) the admittance
        matrix 'B' used in DC power flow, in particular, it contains the entire
        admittance matrix upon input and the REF bus is removed at output
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
    :param int NR: index number of the reference node.
    :return: (*tuple*) -- a pair of numpy arrays, BB and LT
                          BB: 2D array with shape (NOAREA, NOAREA)
                              the 'B matrix without reference bus' in DC power flow
                          LT: 1D array with shape (NOAREA, )
                              array recording the original bus no.
    """
    LT = np.append(np.delete(BN[:, 0], NR), BN[NR, 0]).astype(int)
    BB = np.delete(np.delete(BB, obj=NR, axis=0), obj=NR, axis=1)
    BB = np.pad(BB, ((0, 1), (0, 1)))
    return BB, LT
