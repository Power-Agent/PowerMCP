import numpy as np

from reliabilityassessment.monte_carlo.tm1 import tm1
from reliabilityassessment.monte_carlo.tm2 import tm2


def transm(
    IFLAG,
    JFLAG,
    CLOCK,
    JHOUR,
    IOI,
    BN,
    BLPA,
    BLP0,
    BB,
    LT,
    ZB,
    LP,
    NR,
    STMULT,
    LNSTAT,
    NLS,
    TRNSFR,
    TRNSFJ,
    SYSCON,
    CAPREQ,
    PLNDST,
    PCTAVL,
):
    """
    The main entry function of the transmsison module used in reliability assessment

    .. note:: 1) For descriptions of input and output variables, please refer to `variable
              descriptions.xlsx` in the project Dropbox folder at:
              https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0
              2) arrays are modified in-place.
    """

    # local variables
    LCLOCK = CLOCK
    JHOUR = JHOUR
    IOI = IOI
    NN = NOAREA = BN.shape[0]
    NL = NLINES = LNSTAT.shape[0]
    BLP = np.zeros((NLINES, 3))  # in original Fortran, np.zeros((100,3))

    if IFLAG != 1:
        BLP[:NL, :3] = BLPA[:NL, :3].copy()
        # CALL TM1(BN,LP,BLP,BLP0,NN,NL,BB,ZB,LT,NR)
        BLP0[:], BB[:, :], LT[:], ZB[:, :] = tm1(BN, LP, BLP, NR)

    L = (LNSTAT[:NL] - 1) * 3  # LNSTAT[i] is 1-based value
    BLP[:NL, 0] = BLPA[range(NL), L]
    BLP[:NL, 1] = BLPA[range(NL), L + 1] * STMULT[:NL, 0]
    BLP[:NL, 2] = BLPA[range(NL), L + 2] * STMULT[:NL, 1]

    # local variable
    BNS = np.zeros((NOAREA, 6))  # in original Fortran, np.zeros((20,6))

    if JFLAG != 1:
        NLST = NLS
        NLS = 1
        for i in range(NN):
            BN[i, 2] = TRNSFR[i] + TRNSFJ[i]
            BN[i, 1] = 0.0
            BNS[i, 0] = BN[i, 2]
            BNS[i, 1] = BN[i, 1]
            BNS[i, 4] = SYSCON[i]
            BNS[i, 5] = CAPREQ[i]
            X = SYSCON[i] - CAPREQ[i]
            X = min(X, 0)
            BN[i, 2] = max(BN[i, 2], X)

        FLOW, INDIC = tm2(
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
        )

        NLS = NLST
        KFLAG = 1

        SADJ = SYSCON[:NN] - CAPREQ[:NN] - BN[:NN, 1]
        KFLAG = int((SADJ[:NN] >= 0).all())

        if KFLAG == 1:
            return JFLAG, FLOW, SADJ

        JFLAG = 1
        CADJ = np.zeros(NN)  # CADJ is locally used
        CADJ[:NN] = BN[:NN, 1] * NLS

    BN[:NN, 2] = SYSCON[:NN] - CAPREQ[:NN] - CADJ[:NN]
    BN[:NN, 1] = CAPREQ[:NN].copy()
    BNS[:NN, [0, 1, 3]] = BN[:NN, [2, 1, 3]]

    if NLS != 0:
        BLP[:NL, 1] -= FLOW[:NL]
        BLP[:NL, 2] += FLOW[:NL]
        BLP[:NL, [1, 2]] = BLP[:NL, [1, 2]].clip(min=0.0)
        BN[LP[:NL, 1], 3] += FLOW[:NL]
        BN[LP[:NL, 1], 4] -= FLOW[:NL]
        BN[LP[:NL, 2], 3] += FLOW[:NL]
        BN[LP[:NL, 2], 4] -= FLOW[:NL]

    FLOW, INDIC = tm2(
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
    )

    BN[:NN, 3] = BNS[:NN, 3].copy()
    BN[:NN, 4] = BNS[:NN, 3].copy()

    SADJ[:NN] = BN[:NN, 1] - SYSCON[:NN] + CAPREQ[:NN] + CADJ[:NN]

    return JFLAG, FLOW, SADJ
