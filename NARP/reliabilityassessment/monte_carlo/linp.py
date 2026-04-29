import numpy as np

from reliabilityassessment.monte_carlo.dgeco import dgeco
from reliabilityassessment.monte_carlo.dgedi import dgedi
from reliabilityassessment.monte_carlo.mc import mc
from reliabilityassessment.monte_carlo.rc import rc
from reliabilityassessment.monte_carlo.rm import rm


def linp(M, N, A, XOB, XOBI, IBAS, BS, LCLOCK, N1):
    """
    A customized version of linear programming (LP).

    :param int M: total number of constraints (possibly)
    :param int N: total number of decision variables (possibly)
    :param numpy.ndarray A: coefficient matrix of all constraints (possibly) with
        initial shape (200, 250), the actual size is determined on-the-fly
    :param numpy.ndarray XOB: 1D binary vector with initial shape (250, ), the actual
        size is determined on-the-fly (possibly (N, ))
    :param numpy.ndarray XOBI: 2D binary vector with initial shape (2, 250),
        the actual size is determined on-the-fly (possibly (2, N))
    :param numpy.ndarray IBAS: indices of basis-vector (possibly) with initial shape
        (250, ), the actual size is determined on-the-fly (possibly (M, ))
    :param numpy.ndarray BS: 1D array with initial shape (200, ) the actual size is
        determined on-the-fly (possibly shape (M, ))
    :param float LCLOCK: the simulation time clock
    :param int N1: an integer used in LP-based DCOPF
    :return: (*tuple*) -- updated N and TAB, a matrix used in LP with initial shape
        (200, 250), the actual size is determined on-the-fly

    .. note:: 1. Arrays are modified in place.
              2. Inputs, outputs and internal logic may not be exactly the same as
                 that in standard LP APIs in SciPy/NumPy or MATLAB.
    """

    IBASF = np.zeros(N, dtype=int)  # np.zeros(250, dtype=int) in original Fortran
    CB = np.zeros(M)  # np.zeros(200) in original Fortran
    BS1 = BS[:M].copy()  # np.zeros(200) in original Fortran

    IR = 0
    INV = 0
    XOB[:N] = XOBI[0, :N].copy()

    IPH = 1
    TAB = np.identity(M)  # size was (200, 250) in original Fortran

    IBASF[IBAS[:M]] = 1
    CB[:M] = XOB[IBAS[:M]]

    while True:  # 110  while loop
        N = N1
        PY = rm(M, CB, TAB)

        gotoFlag1000 = False
        while True:  # 111 while loop
            CM = 0.0
            for i in np.where(IBASF[:N] != 1)[0]:
                CC = XOB[i] - rc(M, PY, A, i)
                if abs(CC) < 1e-7:
                    CC = 0.0
                if abs(CC - CM) < 1e-7:
                    continue
                if CC < CM:
                    IND, CM = i, CC

            if CM < 0:
                break  # GO TO 400

            if IR == 1:
                gotoFlag1000 = True
                break  # GO TO 1000

            IMAX = 0
            TABT = A[:M, IBAS[:M]]

            IPVT = dgeco(TABT, M)
            dgedi(TABT, M, IPVT)

            PY = rm(M, CB, TABT)

            for i in np.where(IBASF[:N] != 0)[0]:
                CC = abs(XOB[i] - rc(M, PY, A, i))
                if CC < 1e-08:
                    continue
                IMAX = 500

            if IMAX != 0:  # i.e. == 500
                f = open("extra.txt", "w")
                f.write("\n     INVERSIONS = %2d LCLOCK = %6d\n" % (INV, LCLOCK))
                f.close()
                INV += 1

            BS[:M] = 0.0
            BS[:M] += TABT @ BS1
            TAB = TABT.copy()

            IR = 1
            # GO TO 111 while loop

        # 400 CONTINUE
        if gotoFlag1000 is False:
            IR = 0
            P = mc(M, IND, TAB, A)
            ICOUN = 0

            for i in np.where(P[:M] > 1e-07)[0]:
                BNUM = BS[i] if abs(BS[i]) >= 1e-13 else 0.0
                RAT = BNUM / P[i]
                ICOUN += 1
                if ICOUN == 1:
                    RAT1, IPIV = RAT, i
                    continue
                if RAT < RAT1:
                    RAT1, IPIV = RAT, i
                    continue
                if IPH != 2 and BS[i] == 0 and XOB[IBAS[i]] == 1:
                    IPIV = i

            for i in np.where(P[:M] != 0)[0]:
                if i == IPIV:
                    continue
                TAB[i, :M] -= TAB[IPIV, :M] * P[i] / P[IPIV]
                BS[i] -= BS[IPIV] * P[i] / P[IPIV]

            TAB[IPIV, :M] /= P[IPIV]

            BS[IPIV] /= P[IPIV]
            CB[IPIV] = XOB[IND]
            K1 = IBAS[IPIV]
            IBASF[K1] = 0
            IBASF[IND] = 1
            IBAS[IPIV] = IND
            # GO TO 110 while loop
        else:  # 1000  CONTINUE
            if IPH == 2:
                break  # GO TO 2000 (exit)
            # N -= NXT # this comment exists in the original Fortran code.
            XOB[:N] = XOBI[1, :N].copy()
            CB[:M] = XOB[IBAS[:M]]
            IPH = 2
        # GO TO 110 while loop

    # 2000 (exit)
    return N, TAB
