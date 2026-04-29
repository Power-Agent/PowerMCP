import numpy as np


def conls(BC, INJ, NX, NR, LT, BLP, LP, BN, LOD, NLS):
    """
    Update the coefficient-matrices of constraints, and other quantities, for the LP-based DCOPF
    (load shedding) under the "load-sharing" mode (in short, "LS")

    :param numpy.ndarray BC: shape (NOAREA, NOAREA)
                            the realistic size is determined on-the-fly
                            a matrix used in LP-based DCOPF
    :param numpy.ndarray INJ: shape (NOAREA,)
                            the realistic size is determined on-the-fly
                            a vector used in LP-based DCOPF
                            (possibly) related to the injection at each bus(i.e., "area")
    :param int NX: an integer used in LP-based DCOPF
                   (possibly) related to the variables/constraint dimensions in LP-based DCOPF
    :param int NR: an integer used in LP-based DCOPF
                   (possibly) means the index of the reference bus (area) in power flow computation
    :param numpy.ndarray LT: 1D array with initial shape (NOAREA,)
                              LT[I] contains the actual node index corresponding to node I
                              of the reduced admittance matrix here;
    :param numpy.ndarray BLP: 2D array with shape (NLINES, 3)
                              BLP[I, 0]: admittance of the line at the I-th entry of LP
                              BLP[I, 1]: capacity (MW)
                              BLP[I, 2]: backward capacity (MW)
    :param numpy.ndarray LP: 2D array with shape (NLINES, 3)
                             LP[I, 0]: line number, set to I
                             LP[I, 1]: starting node
                             LP[I, 2]: ending node
    :param numpy.ndarray BN: 2D array with shape (NOAREA, 5)
                             BN[I, 0]: area (bus/node) number
                             BN[I, 1]: area load, overridden by net injection after
                                       calling :py:func: `tm2`
                             BN[I, 2]: area net injection, overridden by load
                                       curtailment after calling :py:func: `tm2`
                             BN[I, 3]: area constraint on total power flow
                             BN[I, 4]: a helper value storing the modified "constraint on
                                       sum of flows at this area"
    :param numpy.ndarray LOD: 1D array with shape (NLINES, 3)
                              vector of loads
    :param int NLS: an indicator of loss sharing mode,
                    0    LOSS SHARING
                    1    NO LOSS SHARING
    :return: (*tuple*) -- a tuple of three scalars, M, N, N1;
                          M: used in linear programming(LP)-based DCOPF
                             (possibly) means the total number of constraints
                          N: used in linear programming(LP)-based DCOPF
                             (possibly) means the total number of "decision variables" in the LP
                          N1: an integer used in LP-based DCOPF
                          A:  array with initial shape (200, 250),
                              the realistic size is determined on-the-fly
                              a matrix used in LP-based DCOPF
                              (possibly) means the  coefficient matrix of all constraints in LP
                          XOB: initial shape (250, )
                               the realistic size is determined on-the-fly
                               a vector used in linear programming(LP)-based DCOPF
                               values are either 0 or 1; 'float' type in original Fortran code.
                          XOBI: initial shape (2, 250)
                                the realistic size is determined on-the-fly
                                a matrix used in linear programming(LP)-based DCOPF
                                values are either 0 or 1; 'float' type in original Fortran code.
                          IBAS: 1D integer array with initial shape (250, ) (possibly (M,))
                                the realistic size is determined on-the-fly
                                a helper vector used in linear programming-based DCOPF
                                (possibly) means the indices of the "basis-vector" used in LP
                          BS: 1D array with initial shape (200, )
                              the realistic size is determined on-the-fly
                              a helper vector used in linear programming-based DCOPF
                          B:  1D array with initial shape (200, )
                              the realistic size is determined on-the-fly
                              a vector used in linear programming(LP)-based DCOPF
                          B1: 1D array with initial shape (200, )  (possibly (M,))
                              the realistic size is determined on-the-fly
                              a helper vector used in linear programming-based DCOPF
                          TAB: initial shape (200, 250) (possibly (M, N))
                               the realistic size is determined on-the-fly
                               a matrix used in linear programming(LP)-based DCOPF
                          And modify several arrays in place.
    """

    NX1 = NX + 1
    NP1 = 3 * NX + 1
    NP = 2 * NX + 1
    NP2 = NP1 + NX1
    NMAX1 = 250
    NMAX2 = 200

    # Index-related array must be initialized "-1"!
    IEQ = (-1) * np.ones(NX + 1, dtype=int)  # originally in Fortran np.zeros(20)
    # maybe also Ok to initialize it by np.zeros(NOAREA) (check later)

    XOB = np.zeros(NMAX1)
    XOBI = np.zeros((2, NMAX1))
    A = np.zeros((NMAX2, NMAX1))
    B = np.zeros(NMAX2)
    BS = np.zeros(NMAX2)

    IEQ[LT[:NX]] = range(NX)

    IEQ[NR] = NX
    NXD = 2 * NX

    for i in range(NX):
        JJ = 0
        for j in range(NX):
            A[i, JJ] = BC[i, j]
            A[i, JJ + 1] = -BC[i, j]
            JJ += 2
        A[i, NXD + i] = -1.0
        j = LT[i]
        B[i] = -LOD[j]
        A[i, NP1 + i] = -1.0

    NX1 = NX + 1
    NL = BLP.shape[0]
    for i in range(NL):
        for j in range(1, 3):
            if LP[i, j] == NR:
                I1 = IEQ[LP[i, 3 - j]] * 2
                A[NX, I1] += BLP[i, 0]
                A[NX, I1 + 1] -= BLP[i, 0]

    A[NX, NX + NP - 1] = 1.0  # A[NX1, NX + NP] in original Fortran
    B[NX] = -LOD[NR]  # B[NX1] in original Fortran
    A[NX, NP1 + NX] = 1.0  # A[NX1, NP1 + NX1] in original Fortran
    A[NX, :NP2] = -A[NX, :NP2]

    NXD = 2 * NX
    XOB[NXD : NXD + NX1] = 1.0

    for i in range(NX1):
        A[i + NX1, NP2 + i] = 1.0
        A[i + NX1, NXD + i] = 1.0
        j = LT[i]
        B[i + NX1] = LOD[j]

    NX2 = 2 * NX1
    NP2 = 2 * NX + 2 * NX1
    for i in range(NX1):
        A[i + NX2, NP1 + i] = 1.0
        A[i + NX2, NP2 + NX1 + i] = 1.0
        j = LT[i]
        B[i + NX2] = LOD[j] + INJ[i]

    NX3 = 3 * NX1
    NP22 = NP2 + 2 * NX1
    NP3 = NP22 + NL

    for i in range(NL):
        I1 = NX3 + i
        I2 = I1 + NL
        J1 = LP[i, 1]
        J2 = LP[i, 2]
        J4 = IEQ[J1]
        J5 = IEQ[J2]
        J42 = J4 * 2 + 1  # J4 * 2 in original Fortran
        J41 = J42 - 1
        J52 = J5 * 2 + 1  # J5 * 2 in original Fortran
        J51 = J52 - 1
        if J4 < NX:  # "if J4 <= NX" in original Fortran
            A[I1, J41] = BLP[i, 0]
            A[I1, J42] = -BLP[i, 0]
            A[I2, J41] = -BLP[i, 0]
            A[I2, J42] = BLP[i, 0]
        if J5 < NX:  # "if J5 <= NX" in original Fortran
            A[I1, J51] = -BLP[i, 0]
            A[I1, J52] = BLP[i, 0]
            A[I2, J51] = BLP[i, 0]
            A[I2, J52] = -BLP[i, 0]
        A[I1, NP22 + i] = 1.0
        A[I2, NP3 + i] = 1.0
        B[I1] = BLP[i, 1]
        B[I2] = BLP[i, 2]

    NXL = NP3 + NL
    NXD1 = NXD + 1
    M = 3 * NX1 + 2 * NL
    N = NXL

    for i in range(NX1):
        for j in range(NXD):
            K = LT[i]
            A[i + M, j] = A[i, j]
            B[i + M] = BN[K, 3]
            A[i + M + NX1, j] = -A[i, j]
            B[i + M + NX1] = BN[K, 4]
        A[i + M, i + N] = 1.0
        A[i + M + NX1, i + N + NX1] = 1.0

    M += 2 * NX1
    N += 2 * NX1

    B1 = np.zeros(
        M
    )  # in Fortran, B1 is by default 'int' type with size 'NMAX2', which is no need here.
    B1[:M] = B[:M]

    B[:NX1] = B[:NX1].clip(max=0.0)

    A[np.where(B[:M] < 0), :N] *= -1
    B[:M] = abs(B[:M])

    # for i in range(NX1):
    #     A[i, i + N] = 1.0
    #     XOBI[0, i + N] = 1.0
    A[tuple([np.arange(NX1), np.arange(N, N + NX1)])] = 1.0
    XOBI[0, N : N + NX1] = 1.0
    XOBI[1, :N] = XOB[:N]

    N += NX1
    NXD2 = NXD1 + 2 * NX1
    II = -1

    # Index-related array must be initialized "-1"!
    IBAS = (-1) * np.ones(M, dtype=int)  # size = NMAX1 in original Fortran

    for i in range(NXD2 - 1, N):
        II += 1
        IBAS[II] = i

    TAB = np.zeros((M, N))  # np.zeros((NMAX2, NMAX1)) in original Fortran

    NX2 = NX1 + 1
    j = -1
    for i in range(NX2 - 1, M):
        j += 1
        TAB[j, :N] = A[i, :N]
        BS[j] = B[i]

    for i in range(NX1):
        j += 1
        TAB[j, :N] = A[i, :N]
        BS[j] = B[i]

    A[:M, :N] = TAB[:M, :N]

    N1 = N - NX1

    return M, N, N1, A, XOB, XOBI, IBAS, BS, B, B1, TAB
