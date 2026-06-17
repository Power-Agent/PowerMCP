import numpy as np

from reliabilityassessment.monte_carlo.admitm import admitm
from reliabilityassessment.monte_carlo.admref import admref
from reliabilityassessment.monte_carlo.assign import assign
from reliabilityassessment.monte_carlo.conls import conls
from reliabilityassessment.monte_carlo.connls import connls
from reliabilityassessment.monte_carlo.flo import flo
from reliabilityassessment.monte_carlo.linp import linp
from reliabilityassessment.monte_carlo.net import net
from reliabilityassessment.monte_carlo.theta import theta
from reliabilityassessment.monte_carlo.thetac import thetac
from reliabilityassessment.monte_carlo.ximpa import ximpa
from reliabilityassessment.monte_carlo.ximpar import ximpar


def tm2(
    BN,
    LP,
    BLP,
    BLP0,
    BB,
    ZB,
    LT,
    NR,
    NLS,
    BNS,
    LCLOCK,
    JHOUR,
    IOI,
    JFLAG,
    PLNDST,
    PCTAVL,
):
    """
    The core part of the transmission module used in reliability assessment

    :return: (*tuple*) -- FLOW: vector of line power flows (MW),  shape: (NLINES, )
                          INDIC: an integer indicator.
                                 (In fact, not used outside in the original Fortran;
                                 can be removed later.)
    .. note:: 1) For descriptions of input variables, please refer to `variable
              descriptions.xlsx` in the project Dropbox folder at:
              https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0
              2) arrays BN, BB, ZB are modified in-place.
    """

    MULT = 0
    NN = BN.shape[0]  # == BB.shape[0] == ZB.shape[0]
    NL = LP.shape[0]  # == BLP.shape[0] == BLP0.shape[0]
    NX = NN - 1

    NOAREA = LT.shape[0]
    IEQ = np.zeros(NOAREA, dtype=int)

    IEQ[LT[:NX]] = range(NX)
    IEQ[NR] = NX

    INJB = BN[:NN, 2] - BN[:NN, 1] * MULT

    LOD = BN[:NN, 1].copy()
    INJ = INJB[LT[:NN]]
    BT = BB[:NX, :NX].copy()
    ZT = ZB[:NX, :NX].copy()

    for i in range(NL):
        if BLP[i, 0] == BLP0[i]:
            continue

        NI = LP[i, 1]
        NJ = LP[i, 2]

        if not ((NI == NR) or (NJ == NR)):
            NII = IEQ[NI]
            NJJ = IEQ[NJ]
            BIJ = BLP[i, 0]

            if BIJ != 0.0:
                ZIJ = -1 / BIJ
                Z = ximpa(ZB, ZIJ, NII, NJJ)
                admitm(BB, NII, NJJ, BIJ)
                for i1 in range(NX):
                    for j1 in range(NX):
                        ZB[i1, j1] = Z[i1, j1]

            BIJ = -BLP0[i]
            ZIJ = -1 / BIJ

            Z = ximpa(ZB, ZIJ, NII, NJJ)
            admitm(BB, NII, NJJ, BIJ)
            ZB[:NX, :NX] = Z[:NX, :NX].copy()

            continue

        if NI == NR:
            NI = NJ
        NII = IEQ[NI]
        BIJ = BLP[i, 0]

        if BIJ == 0.0:
            continue

        for bij in [BIJ, -BLP0[i]]:
            ZIJ = -1 / bij
            Z = ximpar(ZB, ZIJ, NII)
            admref(BB, NII, BIJ)
            ZB[:NX, :NX] = Z[:NX, :NX].copy()

    # Assigns injections at buses so as to balance
    # positive and negative injections
    INJ1, LODC = assign(INJ, LOD, LT, NN, NLS)

    THET = theta(ZB, INJ1)
    THETC = thetac(THET, LT)
    SFLOW, FLOW = flo(LP, BLP, THETC)

    INDIC = 0

    for i in range(NL):
        if FLOW[i] >= 0:
            if FLOW[i] > BLP[i, 1]:
                INDIC = 1
            continue
        FF = FLOW[i]
        FF = abs(FF)
        DIRF = BLP[i, 2]
        if FF > DIRF:
            INDIC = 1

    for i in range(NN):
        if SFLOW[i] >= 0:
            if SFLOW[i] > BN[i, 3]:
                INDIC = 1
            continue
        FF = SFLOW[i]
        FF = abs(FF)
        DIRF = BN[i, 4]
        if FF > DIRF:
            INDIC = 1

    if INDIC != 1:
        for i in range(NN):
            j = LT[i]
            BN[j, 1] = INJ1[i]
            BN[i, 2] = LODC[i]
        # INL=0 in Fortran, this variable is defined but never used.

        # GO TO 1000
        BB[:NX, :NX] = BT[:NX, :NX].copy()
        ZB[:NX, :NX] = ZT[:NX, :NX].copy()
        return FLOW, INDIC

    RES = np.zeros((250, 3))  # may use "N" as its size (check later)
    NUNITS = len(PLNDST)
    NNTAB = np.zeros(NUNITS)  # in Fortran, np.zeros(600)

    if NLS != 0:
        M, N, N1, A, XOB, XOBI, IBAS, BS, B, B1, TAB = connls(
            BB, INJ, INJB, NX, NR, LT, BLP, LP, BN, LOD, NLS
        )

        # NXT = NX + 1 defined but not used in original Fortran
        N, TAB = linp(M, N, A, XOB, XOBI, IBAS, BS, LCLOCK, N1)
        net(B, B1, RES, IBAS, BS, M, N)

        NXD1 = NX * 2 + 1
        NXD2 = NXD1 + NX

        for i in range(NXD1 - 1, NXD2):
            II = i - NXD1 + 1
            j = LT[II]
            BN[j, 1] = -RES[i, 0]
            BN[j, 2] = -BN[j, 2] + BN[j, 1]
            if BN[j, 2] < 0:
                BN[j, 2] = 0

        NXD1 = 4 * NX + 3
        NXD2 = 4 * NX + 2 + NL

        FLOW[0 : NXD2 - NXD1 + 1] = RES[NXD1 - 1 : NXD2, 0].copy()

        if IOI != 0:
            f = open("traout.txt ", "w")  # maybe 'a' ; need later check
            f.write("\n     %8d  %4d  %1d\n" % (LCLOCK, JHOUR, JFLAG))

            # print table of units on outage or derated to traout file
            # JXX is the unit number on outage, derated, or on planned maintenance.
            # NNTAB[i] is index of unit on outage or on maintenance.
            # if unit is derated, then NNTAB[i] has a “-” sign.

            JXX = 0
            for i in range(NUNITS):
                if PLNDST[i] != 1.0:
                    JXX += 1
                    NNTAB[JXX] = i
                    continue
                if PCTAVL[i] == 1.0:
                    continue
                JXX += 1
                NNTAB[JXX] = i
                if PCTAVL[i] != 0.0:
                    NNTAB[JXX] = -i

            f.write("%4d\n" % (JXX))
            for i in range[JXX]:
                f.write("%4d\n " % (NNTAB[i]))

            if JFLAG != 1:
                for i in range(NN):
                    f.write(
                        "\n     %3.0f  %10.2f  %10.2f  %10.2f  %10.2f  \n "
                        % (BN[i, 0], BNS[i, 0], BN[i, 1], BNS[i, 4], BNS[i, 5])
                    )

            if JFLAG != 0:
                for i in range(NN):
                    f.write(
                        "\n     %3.0f  %8.0f     %8.0f     %8.0f     %8.0f     %8.0f     \n "
                        % (BN[i, 0], BN[i, 1], BN[i, 2], BNS[i, 0], BNS[i, 1], BN[i, 3])
                    )

            for i in range(NL):
                f.write(
                    "\n     %3d  %3d  %3d  %8.0f  %8.0f  %8.0f  %8.0f  \n "
                    % (
                        LP[i, 0],
                        LP[i, 1],
                        LP[i, 2],
                        BLP[i, 0],
                        BLP[i, 1],
                        BLP[i, 2],
                        FLOW[i],
                    )
                )
    else:
        M, N, N1, A, XOB, XOBI, IBAS, BS, B, B1, TAB = conls(
            BB, INJ, INJB, NX, NR, LT, BLP, LP, BN, LOD, NLS
        )

        # NXT = NX + 1 defined but not used in original Fortran
        N, TAB = linp(M, N, A, XOB, XOBI, IBAS, BS, LCLOCK, N1)
        net(B, B1, RES, IBAS, BS, M, N)

        NX1 = NX + 1
        NXD1 = NX * 2 + 2 * NX1 + 1
        NXD2 = NXD1 + NX

        for i in range(NXD1 - 1, NXD2):
            II = i - NXD1 + 1
            j = LT[II]
            BN[j, 2] = RES[i, 0]
            III = i + NX1
            BN[j, 1] = RES[III, 0] - LOD[j] + BN[j, 2]

        NXD1 = 6 * NX1 - 1
        NXD2 = NXD1 - 1 + NL

        FLOW[0 : NXD2 - NXD1 + 1] = RES[NXD1 - 1 : NXD2, 0].copy()

        # This block is very similar to a previous code block,
        # except the JFLAG logic in file writing. Maybe we can put it in a
        # function to reduce duplicated code. (may consider in the future)
        if IOI != 0:
            f = open("traout.txt ", "w")  # maybe 'a' ; need later check
            f.write("\n     %8d  %4d  %1d\n" % (LCLOCK, JHOUR, JFLAG))
            JXX = 0
            for i in range(NUNITS):
                if PLNDST[i] != 1.0:
                    JXX += 1
                    NNTAB[JXX] = i
                    continue
                if PCTAVL[i] == 1.0:
                    continue
                JXX += 1
                NNTAB[JXX] = i
                if PCTAVL[i] != 0.0:
                    NNTAB[JXX] = -i

            f.write("%4d\n" % (JXX))
            for i in range(JXX):
                f.write("%4d\n " % (NNTAB[i]))

            for i in range(NN):
                f.write(
                    "\n     %3.0f  %8.0f     %8.0f     %8.0f     %8.0f     %8.0f     \n "
                    % (BN[i, 0], BN[i, 1], BN[i, 2], BNS[i, 0], BNS[i, 1], BN[i, 3])
                )

            for i in range(NL):
                f.write(
                    "\n     %3d  %3d  %3d  %8.0f  %8.0f  %8.0f  %8.0f  \n "
                    % (
                        LP[i, 0],
                        LP[i, 1],
                        LP[i, 2],
                        BLP[i, 0],
                        BLP[i, 1],
                        BLP[i, 2],
                        FLOW[i],
                    )
                )

    # GO TO 1000
    BB[:NX, :NX] = BT[:NX, :NX].copy()
    ZB[:NX, :NX] = BT[:NX, :NX].copy()

    return FLOW, INDIC
