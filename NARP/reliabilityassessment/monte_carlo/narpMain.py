from pathlib import Path

import numpy as np

from reliabilityassessment.data_processing.dataf1 import dataf1
from reliabilityassessment.monte_carlo.contrl import contrl
from reliabilityassessment.monte_carlo.initfl import initfl
from reliabilityassessment.monte_carlo.initl import initl
from reliabilityassessment.monte_carlo.seeder import seeder


def narpMain(TEST_DIR):
    """
    Main entry function of the whole NARP program

    ..note: This python program is based on a previous Fortran program originally
            developed by Dr. Chanan Singh (Texas A&M) and the Associated  Power Analysts, Inc.
    """
    print("\n NARP Python Version-0,  01/01/2023 \n")
    print("\n call function initfl \n")
    MFA, IPOINT, EVNTS = initfl()

    print("\n call function dataf1 \n")
    filepaths = [
        Path(TEST_DIR),
        Path(TEST_DIR, "LEEI"),
    ]

    (
        QTR,
        NORR,
        NFCST,
        NOAREA,
        PKLOAD,
        FU,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        BN,
        SUSTAT,
        FCTERR,
        CAPCON,
        CAPOWN,
        NOGEN,
        PROBG,
        DERATE,
        JENT,
        INTCH,
        INTCHR,
        LP,
        LINENO,
        PROBL,
        BLPA,
        MXCRIT,
        JCRIT,
        RATES,
        ID,
        HRLOAD,
        MAXHR,
        DYLOAD,
        MAXDAY,
        WPEAK,
        MXPLHR,
        JPLOUT,
        ITAB,
        NLS,
        IOI,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        CVTEST,
        MAXEUE,
        JSTEP,
        JFREQ,
        FINISH,
        INTV,
        INTVT,
        NR,
        NAMA,
    ) = dataf1(filepaths)

    LSTEP = int(MAXEUE // 20)
    NUNITS = PROBG.shape[0]
    NLINES = LP.shape[0]
    NOAREA = HRLOAD.shape[0]
    # seeding:
    JSEED = 123456
    IGSEED, ILSEED = seeder(JSEED, NUNITS, NLINES)
    # ----------------------------Finish data processing part--------------------------

    # ----------------------------Begin Monte Carlo simulation part --------------------------
    ATRIB, CLOCK, IPOINT, MFA, NUMINQ = initl(JSTEP, EVNTS)
    IQ = 0  # initialize the quarter index to be 0 (i.e., the 1st quarter)
    JHOUR = 0  # initialize the hour index
    SSQ = 0.0
    XLAST = 0.0  # initial values for convergence-related quantities
    NHRSYR = 8760
    RFLAG = 0  # initialize the normal return flag
    INDX = 0
    if JSTEP == 24:
        INDX = 1

    HLOLE = np.zeros((NOAREA, 22))
    DPLOLE = np.zeros((NOAREA, 22))
    EUES = np.zeros((NOAREA, 22))
    PLNDST = np.zeros(NUNITS)
    LSFLG = np.zeros(NOAREA)
    LT = np.zeros(NOAREA, dtype=int)
    BB = np.zeros((NOAREA, NOAREA))
    ZB = np.zeros((NOAREA, NOAREA))
    BLP0 = np.zeros(NLINES)
    RATING = np.zeros(NUNITS)

    LOLGHA = np.zeros((NOAREA, 5))
    LOLGPA = np.zeros((NOAREA, 5))
    LOLGHP = np.zeros(5)
    LOLGPP = np.zeros(5)
    LOLTHA = np.zeros((NOAREA, 5))
    LOLTHP = np.zeros(5)
    LOLTPA = np.zeros((NOAREA, 5))
    LOLTPP = np.zeros(5)
    MGNGHA = np.zeros((NOAREA, 5))
    MGNGPA = np.zeros((NOAREA, 5))
    MGNGHP = np.zeros(5)
    MGNGPP = np.zeros(5)
    MGNTHA = np.zeros((NOAREA, 5))
    MGNTHP = np.zeros(5)
    MGNTPA = np.zeros((NOAREA, 5))
    MGNTPP = np.zeros(5)
    SGNGHA = np.zeros((NOAREA, 5))
    SGNGHP = np.zeros(5)
    SGNGPA = np.zeros((NOAREA, 5))
    SGNGPP = np.zeros(5)
    SGNSHA = np.zeros((NOAREA, 5))
    SGNSHP = np.zeros(5)
    SGNSPA = np.zeros((NOAREA, 5))
    SGNSPP = np.zeros(5)
    SGNTHA = np.zeros((NOAREA, 5))
    SGNTHP = np.zeros(5)
    SGNTPA = np.zeros((NOAREA, 5))
    SGNTPP = np.zeros(5)
    SOLGHA = np.zeros((NOAREA, 5))
    SOLGHP = np.zeros(5)
    SOLGPA = np.zeros((NOAREA, 5))
    SOLGPP = np.zeros(5)
    SOLSHA = np.zeros((NOAREA, 5))
    SOLSHP = np.zeros(5)
    SOLSPA = np.zeros((NOAREA, 5))
    SOLSPP = np.zeros(5)
    SOLTHA = np.zeros((NOAREA, 5))
    SOLTHP = np.zeros(5)
    SOLTPA = np.zeros((NOAREA, 5))
    SOLTPP = np.zeros(5)
    SWLGHA = np.zeros(NOAREA)
    SWLGHP = 0
    SWLGPA = np.zeros(NOAREA)
    SWLGPP = 0
    SWLSHA = np.zeros(NOAREA)
    SWLSHP = 0
    SWLSPA = np.zeros(NOAREA)
    SWLSPP = 0
    SWLTHA = np.zeros(NOAREA)
    SWLTHP = 0
    SWLTPA = np.zeros(NOAREA)
    SWLTPP = 0
    SWNGHA = np.zeros(NOAREA)
    SWNGHP = 0
    SWNGPA = np.zeros(NOAREA)
    SWNGPP = 0
    SWNSHA = np.zeros(NOAREA)
    SWNSHP = 0
    SWNSPA = np.zeros(NOAREA)
    SWNSPP = 0
    SWNTHA = np.zeros(NOAREA)
    SWNTHP = 0
    SWNTPA = np.zeros(NOAREA)
    SWNTPP = 0
    XNEWA = np.zeros((NOAREA, 3))
    XNEWP = np.zeros(3)

    contrl(
        RFLAG,
        CLOCK,
        NUMINQ,
        IPOINT,
        EVNTS,
        ATRIB,
        FINISH,
        ITAB,
        INDX,
        SUSTAT,
        DPLOLE,
        EUES,
        HLOLE,
        LSTEP,
        NAMA,
        NFCST,
        PLNDST,
        JHOUR,
        JPLOUT,
        IQ,
        RATES,
        NHRSYR,
        JSTEP,
        JFREQ,
        MXPLHR,
        PROBG,
        RATING,
        DERATE,
        CAPOWN,
        CAPCON,
        PROBL,
        JENT,
        INTCH,
        MXCRIT,
        JCRIT,
        HRLOAD,
        FCTERR,
        LSFLG,
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
        CVTEST,
        SSQ,
        NORR,
        XLAST,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
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
        SGNGHA,
        SGNGHP,
        SGNGPA,
        SGNGPP,
        SGNSHA,
        SGNSHP,
        SGNSPA,
        SGNSPP,
        SGNTHA,
        SGNTHP,
        SGNTPA,
        SGNTPP,
        SOLGHA,
        SOLGHP,
        SOLGPA,
        SOLGPP,
        SOLSHA,
        SOLSHP,
        SOLSPA,
        SOLSPP,
        SOLTHA,
        SOLTHP,
        SOLTPA,
        SOLTPP,
        SWLGHA,
        SWLGHP,
        SWLGPA,
        SWLGPP,
        SWLSHA,
        SWLSHP,
        SWLSPA,
        SWLSPP,
        SWLTHA,
        SWLTHP,
        SWLTPA,
        SWLTPP,
        SWNGHA,
        SWNGHP,
        SWNGPA,
        SWNGPP,
        SWNSHA,
        SWNSHP,
        SWNSPA,
        SWNSPP,
        SWNTHA,
        SWNTHP,
        SWNTPA,
        SWNTPP,
        XNEWA,
        XNEWP,
        IGSEED,
        ILSEED,
    )
