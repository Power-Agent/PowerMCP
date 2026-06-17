import numpy as np

from reliabilityassessment.monte_carlo.filem import filem
from reliabilityassessment.monte_carlo.findld import findld
from reliabilityassessment.monte_carlo.findtn import findtn
from reliabilityassessment.monte_carlo.gstate import gstate
from reliabilityassessment.monte_carlo.hrstat import hrstat
from reliabilityassessment.monte_carlo.lstate import lstate
from reliabilityassessment.monte_carlo.pkstat import pkstat
from reliabilityassessment.monte_carlo.sumcap import sumcap
from reliabilityassessment.monte_carlo.transm import transm


def hour(
    ATRIB,
    CLOCK,
    MFA,
    JSTEP,
    JFREQ,
    NUMINQ,
    IPOINT,
    EVNTS,
    MXPLHR,
    PROBG,
    RATING,
    DERATE,
    PLNDST,
    CAPOWN,
    CAPCON,
    PROBL,
    JENT,
    INTCH,
    MXCRIT,
    JCRIT,
    NFCST,
    HRLOAD,
    FCTERR,
    LSFLG,
    LOLGHA,
    LOLGPA,
    LOLGHP,
    LOLGPP,
    LOLTHA,
    LOLTHP,
    LOLTPA,
    LOLTPP,
    MGNGHA,
    MGNGPA,
    MGNGHP,
    MGNGPP,
    MGNTHA,
    MGNTHP,
    MGNTPA,
    MGNTPP,
    LINENO,
    LP,
    LT,
    BB,
    ZB,
    BLP0,
    BLPA,
    IOI,
    BN,
    NR,
    NLS,
    IGSEED,
    ILSEED,
):
    """
    Schedule hourly simulation events

    :return: (*tuple*)
    .. note:: 1) For descriptions of input and output variables, please refer to `variable
              descriptions.xlsx` in the project Dropbox folder at:
              https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0
              2) arrays are modified in-place.
              3) EVNTS is modified in place
    """
    # print("Entering subroutine hour")

    IFLAG, JFLAG = 0, 0

    ATRIB[0] = CLOCK + JSTEP

    # may need modify here: some retun var can be implciit
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    # ..............UPDATE HOUR NUMBER.............
    DXX = 8760
    JHOUR = -1 + int(CLOCK % DXX)  # DMOD(CLOCK,DXX) in original Fortran
    # need to minus 1 due to 0-based index in Python!

    # need to double check
    JDAY = np.floor(JHOUR / 24).astype(
        int
    )  # original Fortran, (JHOUR-.1)/24 + 1, since 1-based

    JHOURT = JHOUR
    if JSTEP == 24:  # if only daily peak stats are collected
        JHOUR = MXPLHR[JDAY]  # MXPLHR stores the pool peak hour

    # ......Draw generator states and sum capacities by area...............
    NOAREA = CAPOWN.shape[0]
    if JHOUR % JFREQ == 0 or JFREQ == 1:
        PCTAVL, AVAIL = gstate(IGSEED, PROBG, RATING, DERATE, PLNDST)
        CAPAVL, SYSOWN, SYSCON, TRNSFJ = sumcap(AVAIL, CAPOWN, CAPCON)
        LNSTAT = lstate(ILSEED, PROBL)
        TRNSFR = findtn(JENT, INTCH, JDAY)

    # STMULT(I,1) IS FORWARD DIRECTION ADJUSTMENT
    # STMULT(I,2) IS BACKWARD DIRECTION ADJUSTMENT
    NLINES = len(LNSTAT)
    STMULT = np.ones((NLINES, 2), dtype=float)

    JPNT = 0  # in original Fortran, 1

    for i in range(MXCRIT):
        if JCRIT[JPNT] == 0:
            JPNT = JPNT + 1
        else:
            NOCRIT = JCRIT[JPNT + 1]
            CRTVAL = 0.0
            for ii in range(NOCRIT):
                if 0 < JCRIT[JPNT + 1 + ii] <= 500 - 1:
                    CRTVAL += AVAIL[JCRIT[JPNT + 1 + ii]]
                else:
                    print("\n Logic error happens regarding the JCRIT array ...\n")

            if CRTVAL == 0.0:
                STMULT[JCRIT[JPNT], 0] = float(JCRIT[JPNT + NOCRIT + 3]) / 100.0
                STMULT[JCRIT[JPNT], 1] = float(JCRIT[JPNT + NOCRIT + 4]) / 100.0

            JPNT += NOCRIT + 5

    for NST in range(NFCST):
        CAPREQ = findld(NST, JHOUR, HRLOAD, FCTERR)

        FLAG = 0
        MARGIN = (SYSCON[:NOAREA] - CAPREQ[:NOAREA]).astype(int)
        FLAG += sum(MARGIN < 0)
        IT = np.where(MARGIN < 0)[0][-1]

        if FLAG == 0:
            # print('Returning: No Loss')
            return (
                NUMINQ,
                MFA,
                IPOINT,
                JHOURT,
            )

        NSHRT = FLAG
        LNCAP = np.zeros(NLINES)

        if NSHRT != NOAREA:
            if FLAG > 1:
                pass  # as the original Fortran logic
            else:
                NEED = abs(MARGIN[IT])
                for j in np.where(MARGIN > 0)[0]:
                    N = LINENO[j, IT]
                    if N > -1:
                        M = (LNSTAT[N] - 1) * 3 + 1
                        XX = BLPA[N, M + (LP[N, 1] != j)]
                        LNCAP[N] = int(XX)
                        MXHELP = min(MARGIN[j], LNCAP[N])
                        NEED -= MXHELP

            TEMPFL = int(any(MARGIN < 0))

            JFLAG = 0
            JFLAG, FLOW, SADJ = transm(
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
            )

            if IFLAG == 0:
                IFLAG = 1
            if JFLAG == 0:
                return (
                    NUMINQ,
                    MFA,
                    IPOINT,
                    JHOURT,
                )
            TEMPFL = 0.0

            MARGIN = (-SADJ[:NOAREA]).astype(int)
            TEMPFL = int(any(MARGIN < 0))

            if TEMPFL == 0:
                return (
                    NUMINQ,
                    MFA,
                    IPOINT,
                    JHOURT,
                )

        hrstat(
            NST,
            MARGIN,
            LSFLG,
            LOLGHA,
            LOLGHP,
            LOLTHA,
            LOLTHP,
            MGNGHA,
            MGNGHP,
            MGNTHA,
            MGNTHP,
        )
        if JHOUR == MXPLHR[JDAY]:
            pkstat(
                NST,
                MARGIN,
                LOLGPA,
                LOLGPP,
                LOLTPA,
                LOLTPP,
                MGNGPA,
                MGNGPP,
                MGNTPA,
                MGNTPP,
            )

    return (
        NUMINQ,
        MFA,
        IPOINT,
        JHOURT,
    )
