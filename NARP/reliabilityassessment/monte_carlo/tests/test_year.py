from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.year import year


def test_year():
    TEST_DIR = Path(__file__).parent.absolute()

    # ----------------------- case 1 --------------------------------------
    CLOCK = 8760.0
    FINISH = 87591240.0
    XLAST = 0.000
    SSQ = 0.000
    CVTEST = 0.025
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 1 - 1  # 0-based index in Python
    RFLAG = 0
    ITAB = 11
    INDX = 0
    INTV = 5
    INTVT = 5
    IOJ = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers
    NORR = 1 - 1  # be used as array index in the original Fortran code
    KVLOC = 1 - 1  # index of the area (used only if KWHERE=1) for convergence checking
    KVSTAT = 1
    KVTYPE = 2
    KVWHEN = 1
    KWHERE = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/ZB")
    ZB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB = year(
        ATRIB,
        CLOCK,
        CVTEST,
        DPLOLE,
        EUES,
        EVNTS,
        FINISH,
        HLOLE,
        IPOINT,
        MFA,
        NUMINQ,
        RFLAG,
        LSFLG,
        NAMA,
        SSQ,
        SUSTAT,
        XLAST,
        BB,
        LT,
        ZB,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        LSTEP,
        NFCST,
        NORR,
        INDX,
        ITAB,
        LOLGHA,
        LOLGHP,
        LOLGPA,
        LOLGPP,
        LOLTHA,
        LOLTHP,
        LOLTPA,
        LOLTPP,
        MGNGHA,
        MGNGHP,
        MGNGPA,
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
    )

    XLAST_true = 0.000
    SSQ_true = 0.000
    MFA_true = 1 - 1  # 0-based index in Python
    NUMINQ_true = 7
    IPOINT_true = 1 - 1  # 0-based index in Python
    RFLAG_true = 0
    ITAB_true = 11
    INTVT_true = 5

    assert XLAST_true == XLAST
    assert SSQ_true == SSQ
    assert MFA_true == MFA
    assert NUMINQ_true == NUMINQ
    assert IPOINT_true == IPOINT
    assert RFLAG_true == RFLAG
    assert ITAB_true == ITAB
    assert INTVT_true == INTVT

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/DPLOLE_mod")
    DPLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DPLOLE, DPLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/EUES_mod")
    EUES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(EUES, EUES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/HLOLE_mod")
    HLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HLOLE, HLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SUSTAT_mod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGHA_mod")
    SGNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHA, SGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGHP_mod")
    SGNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHP, SGNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGPA_mod")
    SGNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPA, SGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNGPP_mod")
    SGNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPP, SGNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSHA_mod")
    SGNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHA, SGNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSHP_mod")
    SGNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHP, SGNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSPA_mod")
    SGNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPA, SGNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNSPP_mod")
    SGNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPP, SGNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTHA_mod")
    SGNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHA, SGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTHP_mod")
    SGNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHP, SGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTPA_mod")
    SGNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPA, SGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SGNTPP_mod")
    SGNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPP, SGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGHA_mod")
    SOLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHA, SOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGHP_mod")
    SOLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHP, SOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGPA_mod")
    SOLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPA, SOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLGPP_mod")
    SOLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPP, SOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSHA_mod")
    SOLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHA, SOLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSHP_mod")
    SOLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHP, SOLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSPA_mod")
    SOLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPA, SOLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLSPP_mod")
    SOLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPP, SOLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTHA_mod")
    SOLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHA, SOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTHP_mod")
    SOLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHP, SOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTPA_mod")
    SOLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPA, SOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SOLTPP_mod")
    SOLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPP, SOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGHA_mod")
    SWLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHA, SWLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGHP_mod")
    SWLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHP, SWLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGPA_mod")
    SWLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPA, SWLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLGPP_mod")
    SWLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPP, SWLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSHA_mod")
    SWLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHA, SWLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSHP_mod")
    SWLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHP, SWLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSPA_mod")
    SWLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPA, SWLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLSPP_mod")
    SWLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPP, SWLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTHA_mod")
    SWLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHA, SWLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTHP_mod")
    SWLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHP, SWLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTPA_mod")
    SWLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPA, SWLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWLTPP_mod")
    SWLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPP, SWLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGHA_mod")
    SWNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHA, SWNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGHP_mod")
    SWNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHP, SWNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGPA_mod")
    SWNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPA, SWNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNGPP_mod")
    SWNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPP, SWNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSHA_mod")
    SWNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHA, SWNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSHP_mod")
    SWNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHP, SWNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSPA_mod")
    SWNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPA, SWNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNSPP_mod")
    SWNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPP, SWNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTHA_mod")
    SWNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHA, SWNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTHP_mod")
    SWNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHP, SWNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTPA_mod")
    SWNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPA, SWNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/SWNTPP_mod")
    SWNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPP, SWNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/XNEWA_mod")
    XNEWA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWA, XNEWA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case1/XNEWP_mod")
    XNEWP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWP, XNEWP_true)

    # ----------------------- case 2 --------------------------------------
    CLOCK = 2 * 8760.0
    FINISH = 87591240.0
    XLAST = 0.000
    SSQ = 0.000
    CVTEST = 0.025
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 1 - 1  # 0-based index in Python
    RFLAG = 0
    ITAB = 11
    INDX = 0
    INTV = 5
    INTVT = 5
    IOJ = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers
    NORR = 1 - 1  # be used as array index in the original Fortran code
    KVLOC = 1 - 1  # index of the area (used only if KWHERE=1) for convergence checking
    KVSTAT = 1
    KVTYPE = 2
    KVWHEN = 1
    KWHERE = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/ZB")
    ZB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB = year(
        ATRIB,
        CLOCK,
        CVTEST,
        DPLOLE,
        EUES,
        EVNTS,
        FINISH,
        HLOLE,
        IPOINT,
        MFA,
        NUMINQ,
        RFLAG,
        LSFLG,
        NAMA,
        SSQ,
        SUSTAT,
        XLAST,
        BB,
        LT,
        ZB,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        LSTEP,
        NFCST,
        NORR,
        INDX,
        ITAB,
        LOLGHA,
        LOLGHP,
        LOLGPA,
        LOLGPP,
        LOLTHA,
        LOLTHP,
        LOLTPA,
        LOLTPP,
        MGNGHA,
        MGNGHP,
        MGNGPA,
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
    )

    XLAST_true = 1.000
    SSQ_true = 1.000
    MFA_true = 1 - 1  # 0-based index in Python
    NUMINQ_true = 7
    IPOINT_true = 1 - 1  # 0-based index in Python
    RFLAG_true = 0
    ITAB_true = 11
    INTVT_true = 5

    assert XLAST_true == XLAST
    assert SSQ_true == SSQ
    assert MFA_true == MFA
    assert NUMINQ_true == NUMINQ
    assert IPOINT_true == IPOINT
    assert RFLAG_true == RFLAG
    assert ITAB_true == ITAB
    assert INTVT_true == INTVT

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/DPLOLE_mod")
    DPLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DPLOLE, DPLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/EUES_mod")
    EUES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(EUES, EUES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/HLOLE_mod")
    HLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HLOLE, HLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SUSTAT_mod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGHA_mod")
    SGNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHA, SGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGHP_mod")
    SGNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHP, SGNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGPA_mod")
    SGNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPA, SGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNGPP_mod")
    SGNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPP, SGNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSHA_mod")
    SGNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHA, SGNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSHP_mod")
    SGNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHP, SGNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSPA_mod")
    SGNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPA, SGNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNSPP_mod")
    SGNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPP, SGNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTHA_mod")
    SGNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHA, SGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTHP_mod")
    SGNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHP, SGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTPA_mod")
    SGNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPA, SGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SGNTPP_mod")
    SGNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPP, SGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGHA_mod")
    SOLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHA, SOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGHP_mod")
    SOLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHP, SOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGPA_mod")
    SOLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPA, SOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLGPP_mod")
    SOLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPP, SOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSHA_mod")
    SOLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHA, SOLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSHP_mod")
    SOLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHP, SOLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSPA_mod")
    SOLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPA, SOLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLSPP_mod")
    SOLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPP, SOLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTHA_mod")
    SOLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHA, SOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTHP_mod")
    SOLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHP, SOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTPA_mod")
    SOLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPA, SOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SOLTPP_mod")
    SOLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPP, SOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGHA_mod")
    SWLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHA, SWLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGHP_mod")
    SWLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHP, SWLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGPA_mod")
    SWLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPA, SWLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLGPP_mod")
    SWLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPP, SWLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSHA_mod")
    SWLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHA, SWLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSHP_mod")
    SWLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHP, SWLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSPA_mod")
    SWLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPA, SWLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLSPP_mod")
    SWLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPP, SWLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTHA_mod")
    SWLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHA, SWLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTHP_mod")
    SWLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHP, SWLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTPA_mod")
    SWLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPA, SWLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWLTPP_mod")
    SWLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPP, SWLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGHA_mod")
    SWNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHA, SWNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGHP_mod")
    SWNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHP, SWNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGPA_mod")
    SWNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPA, SWNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNGPP_mod")
    SWNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPP, SWNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSHA_mod")
    SWNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHA, SWNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSHP_mod")
    SWNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHP, SWNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSPA_mod")
    SWNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPA, SWNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNSPP_mod")
    SWNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPP, SWNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTHA_mod")
    SWNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHA, SWNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTHP_mod")
    SWNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHP, SWNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTPA_mod")
    SWNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPA, SWNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/SWNTPP_mod")
    SWNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPP, SWNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/XNEWA_mod")
    XNEWA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWA, XNEWA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case2/XNEWP_mod")
    XNEWP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWP, XNEWP_true)

    # ----------------------- case 3 --------------------------------------
    CLOCK = 26280.0
    FINISH = 87591240.0
    XLAST = 1.000
    SSQ = 1.000
    CVTEST = 0.025
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 1 - 1  # 0-based index in Python
    RFLAG = 0
    ITAB = 11
    INDX = 0
    INTV = 5
    INTVT = 5
    IOJ = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers
    NORR = 1 - 1  # be used as array index in the original Fortran code
    KVLOC = 1 - 1  # index of the area (used only if KWHERE=1) for convergence checking
    KVSTAT = 1
    KVTYPE = 2
    KVWHEN = 1
    KWHERE = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/ZB")
    ZB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB = year(
        ATRIB,
        CLOCK,
        CVTEST,
        DPLOLE,
        EUES,
        EVNTS,
        FINISH,
        HLOLE,
        IPOINT,
        MFA,
        NUMINQ,
        RFLAG,
        LSFLG,
        NAMA,
        SSQ,
        SUSTAT,
        XLAST,
        BB,
        LT,
        ZB,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        LSTEP,
        NFCST,
        NORR,
        INDX,
        ITAB,
        LOLGHA,
        LOLGHP,
        LOLGPA,
        LOLGPP,
        LOLTHA,
        LOLTHP,
        LOLTPA,
        LOLTPP,
        MGNGHA,
        MGNGHP,
        MGNGPA,
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
    )

    XLAST_true = 1.000
    SSQ_true = 1.000
    MFA_true = 1 - 1  # 0-based index in Python
    NUMINQ_true = 7
    IPOINT_true = 1 - 1  # 0-based index in Python
    RFLAG_true = 0
    ITAB_true = 11
    INTVT_true = 5

    assert XLAST_true == XLAST
    assert SSQ_true == SSQ
    assert MFA_true == MFA
    assert NUMINQ_true == NUMINQ
    assert IPOINT_true == IPOINT
    assert RFLAG_true == RFLAG
    assert ITAB_true == ITAB
    assert INTVT_true == INTVT

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/DPLOLE_mod")
    DPLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DPLOLE, DPLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/EUES_mod")
    EUES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(EUES, EUES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/HLOLE_mod")
    HLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HLOLE, HLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SUSTAT_mod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGHA_mod")
    SGNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHA, SGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGHP_mod")
    SGNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHP, SGNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGPA_mod")
    SGNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPA, SGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNGPP_mod")
    SGNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPP, SGNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSHA_mod")
    SGNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHA, SGNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSHP_mod")
    SGNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHP, SGNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSPA_mod")
    SGNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPA, SGNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNSPP_mod")
    SGNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPP, SGNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTHA_mod")
    SGNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHA, SGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTHP_mod")
    SGNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHP, SGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTPA_mod")
    SGNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPA, SGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SGNTPP_mod")
    SGNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPP, SGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGHA_mod")
    SOLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHA, SOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGHP_mod")
    SOLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHP, SOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGPA_mod")
    SOLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPA, SOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLGPP_mod")
    SOLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPP, SOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSHA_mod")
    SOLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHA, SOLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSHP_mod")
    SOLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHP, SOLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSPA_mod")
    SOLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPA, SOLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLSPP_mod")
    SOLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPP, SOLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTHA_mod")
    SOLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHA, SOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTHP_mod")
    SOLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHP, SOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTPA_mod")
    SOLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPA, SOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SOLTPP_mod")
    SOLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPP, SOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGHA_mod")
    SWLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHA, SWLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGHP_mod")
    SWLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHP, SWLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGPA_mod")
    SWLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPA, SWLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLGPP_mod")
    SWLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPP, SWLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSHA_mod")
    SWLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHA, SWLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSHP_mod")
    SWLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHP, SWLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSPA_mod")
    SWLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPA, SWLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLSPP_mod")
    SWLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPP, SWLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTHA_mod")
    SWLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHA, SWLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTHP_mod")
    SWLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHP, SWLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTPA_mod")
    SWLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPA, SWLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWLTPP_mod")
    SWLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPP, SWLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGHA_mod")
    SWNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHA, SWNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGHP_mod")
    SWNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHP, SWNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGPA_mod")
    SWNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPA, SWNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNGPP_mod")
    SWNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPP, SWNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSHA_mod")
    SWNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHA, SWNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSHP_mod")
    SWNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHP, SWNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSPA_mod")
    SWNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPA, SWNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNSPP_mod")
    SWNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPP, SWNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTHA_mod")
    SWNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHA, SWNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTHP_mod")
    SWNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHP, SWNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTPA_mod")
    SWNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPA, SWNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/SWNTPP_mod")
    SWNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPP, SWNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/XNEWA_mod")
    XNEWA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWA, XNEWA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case3/XNEWP_mod")
    XNEWP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWP, XNEWP_true)

    # ----------------------- case 4 --------------------------------------
    CLOCK = 35040.0
    FINISH = 87591240.0
    XLAST = 1.000
    SSQ = 1.000
    CVTEST = 0.025
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 1 - 1  # 0-based index in Python
    RFLAG = 0
    ITAB = 11
    INDX = 0
    INTV = 5
    INTVT = 5
    IOJ = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers
    NORR = 1 - 1  # be used as array index in the original Fortran code
    KVLOC = 1 - 1  # index of the area (used only if KWHERE=1) for convergence checking
    KVSTAT = 1
    KVTYPE = 2
    KVWHEN = 1
    KWHERE = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/ZB")
    ZB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB = year(
        ATRIB,
        CLOCK,
        CVTEST,
        DPLOLE,
        EUES,
        EVNTS,
        FINISH,
        HLOLE,
        IPOINT,
        MFA,
        NUMINQ,
        RFLAG,
        LSFLG,
        NAMA,
        SSQ,
        SUSTAT,
        XLAST,
        BB,
        LT,
        ZB,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        LSTEP,
        NFCST,
        NORR,
        INDX,
        ITAB,
        LOLGHA,
        LOLGHP,
        LOLGPA,
        LOLGPP,
        LOLTHA,
        LOLTHP,
        LOLTPA,
        LOLTPP,
        MGNGHA,
        MGNGHP,
        MGNGPA,
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
    )

    XLAST_true = 1.000
    SSQ_true = 1.000
    MFA_true = 1 - 1  # 0-based index in Python
    NUMINQ_true = 7
    IPOINT_true = 1 - 1  # 0-based index in Python
    RFLAG_true = 0
    ITAB_true = 11
    INTVT_true = 5

    assert XLAST_true == XLAST
    assert SSQ_true == SSQ
    assert MFA_true == MFA
    assert NUMINQ_true == NUMINQ
    assert IPOINT_true == IPOINT
    assert RFLAG_true == RFLAG
    assert ITAB_true == ITAB
    assert INTVT_true == INTVT

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/DPLOLE_mod")
    DPLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DPLOLE, DPLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/EUES_mod")
    EUES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(EUES, EUES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/HLOLE_mod")
    HLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HLOLE, HLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SUSTAT_mod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGHA_mod")
    SGNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHA, SGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGHP_mod")
    SGNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHP, SGNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGPA_mod")
    SGNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPA, SGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNGPP_mod")
    SGNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPP, SGNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSHA_mod")
    SGNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHA, SGNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSHP_mod")
    SGNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHP, SGNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSPA_mod")
    SGNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPA, SGNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNSPP_mod")
    SGNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPP, SGNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTHA_mod")
    SGNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHA, SGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTHP_mod")
    SGNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHP, SGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTPA_mod")
    SGNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPA, SGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SGNTPP_mod")
    SGNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPP, SGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGHA_mod")
    SOLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHA, SOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGHP_mod")
    SOLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHP, SOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGPA_mod")
    SOLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPA, SOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLGPP_mod")
    SOLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPP, SOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSHA_mod")
    SOLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHA, SOLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSHP_mod")
    SOLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHP, SOLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSPA_mod")
    SOLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPA, SOLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLSPP_mod")
    SOLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPP, SOLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTHA_mod")
    SOLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHA, SOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTHP_mod")
    SOLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHP, SOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTPA_mod")
    SOLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPA, SOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SOLTPP_mod")
    SOLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPP, SOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGHA_mod")
    SWLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHA, SWLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGHP_mod")
    SWLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHP, SWLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGPA_mod")
    SWLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPA, SWLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLGPP_mod")
    SWLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPP, SWLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSHA_mod")
    SWLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHA, SWLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSHP_mod")
    SWLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHP, SWLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSPA_mod")
    SWLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPA, SWLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLSPP_mod")
    SWLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPP, SWLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTHA_mod")
    SWLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHA, SWLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTHP_mod")
    SWLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHP, SWLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTPA_mod")
    SWLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPA, SWLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWLTPP_mod")
    SWLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPP, SWLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGHA_mod")
    SWNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHA, SWNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGHP_mod")
    SWNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHP, SWNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGPA_mod")
    SWNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPA, SWNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNGPP_mod")
    SWNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPP, SWNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSHA_mod")
    SWNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHA, SWNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSHP_mod")
    SWNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHP, SWNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSPA_mod")
    SWNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPA, SWNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNSPP_mod")
    SWNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPP, SWNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTHA_mod")
    SWNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHA, SWNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTHP_mod")
    SWNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHP, SWNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTPA_mod")
    SWNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPA, SWNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/SWNTPP_mod")
    SWNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPP, SWNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/XNEWA_mod")
    XNEWA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWA, XNEWA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case4/XNEWP_mod")
    XNEWP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWP, XNEWP_true)

    # ----------------------- case 5 --------------------------------------
    CLOCK = 122640.0
    FINISH = 87591240.0
    XLAST = 7.000
    SSQ = 9.000
    CVTEST = 0.025
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 21 - 1  # 0-based index in Python
    RFLAG = 0
    ITAB = 11
    INDX = 0
    INTV = 5
    INTVT = 15
    IOJ = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers
    NORR = 1 - 1  # be used as array index in the original Fortran code
    KVLOC = 1 - 1  # index of the area (used only if KWHERE=1) for convergence checking
    KVSTAT = 1
    KVTYPE = 2
    KVWHEN = 1
    KWHERE = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/ZB")
    ZB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB = year(
        ATRIB,
        CLOCK,
        CVTEST,
        DPLOLE,
        EUES,
        EVNTS,
        FINISH,
        HLOLE,
        IPOINT,
        MFA,
        NUMINQ,
        RFLAG,
        LSFLG,
        NAMA,
        SSQ,
        SUSTAT,
        XLAST,
        BB,
        LT,
        ZB,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        LSTEP,
        NFCST,
        NORR,
        INDX,
        ITAB,
        LOLGHA,
        LOLGHP,
        LOLGPA,
        LOLGPP,
        LOLTHA,
        LOLTHP,
        LOLTPA,
        LOLTPP,
        MGNGHA,
        MGNGHP,
        MGNGPA,
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
    )

    XLAST_true = 7.000
    SSQ_true = 9.000
    MFA_true = 21 - 1  # 0-based index in Python
    NUMINQ_true = 7
    IPOINT_true = 21 - 1  # 0-based index in Python
    RFLAG_true = 0
    ITAB_true = 11
    INTVT_true = 15

    assert XLAST_true == XLAST
    assert SSQ_true == SSQ
    assert MFA_true == MFA
    assert NUMINQ_true == NUMINQ
    assert IPOINT_true == IPOINT
    assert RFLAG_true == RFLAG
    assert ITAB_true == ITAB
    assert INTVT_true == INTVT

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/DPLOLE_mod")
    DPLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DPLOLE, DPLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/EUES_mod")
    EUES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(EUES, EUES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/HLOLE_mod")
    HLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HLOLE, HLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SUSTAT_mod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGHA_mod")
    SGNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHA, SGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGHP_mod")
    SGNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHP, SGNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGPA_mod")
    SGNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPA, SGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNGPP_mod")
    SGNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPP, SGNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSHA_mod")
    SGNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHA, SGNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSHP_mod")
    SGNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHP, SGNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSPA_mod")
    SGNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPA, SGNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNSPP_mod")
    SGNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPP, SGNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTHA_mod")
    SGNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHA, SGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTHP_mod")
    SGNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHP, SGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTPA_mod")
    SGNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPA, SGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SGNTPP_mod")
    SGNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPP, SGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGHA_mod")
    SOLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHA, SOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGHP_mod")
    SOLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHP, SOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGPA_mod")
    SOLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPA, SOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLGPP_mod")
    SOLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPP, SOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSHA_mod")
    SOLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHA, SOLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSHP_mod")
    SOLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHP, SOLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSPA_mod")
    SOLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPA, SOLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLSPP_mod")
    SOLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPP, SOLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTHA_mod")
    SOLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHA, SOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTHP_mod")
    SOLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHP, SOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTPA_mod")
    SOLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPA, SOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SOLTPP_mod")
    SOLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPP, SOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGHA_mod")
    SWLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHA, SWLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGHP_mod")
    SWLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHP, SWLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGPA_mod")
    SWLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPA, SWLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLGPP_mod")
    SWLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPP, SWLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSHA_mod")
    SWLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHA, SWLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSHP_mod")
    SWLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHP, SWLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSPA_mod")
    SWLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPA, SWLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLSPP_mod")
    SWLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPP, SWLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTHA_mod")
    SWLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHA, SWLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTHP_mod")
    SWLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHP, SWLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTPA_mod")
    SWLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPA, SWLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWLTPP_mod")
    SWLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPP, SWLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGHA_mod")
    SWNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHA, SWNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGHP_mod")
    SWNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHP, SWNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGPA_mod")
    SWNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPA, SWNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNGPP_mod")
    SWNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPP, SWNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSHA_mod")
    SWNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHA, SWNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSHP_mod")
    SWNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHP, SWNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSPA_mod")
    SWNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPA, SWNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNSPP_mod")
    SWNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPP, SWNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTHA_mod")
    SWNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHA, SWNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTHP_mod")
    SWNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHP, SWNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTPA_mod")
    SWNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPA, SWNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/SWNTPP_mod")
    SWNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPP, SWNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/XNEWA_mod")
    XNEWA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWA, XNEWA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case5/XNEWP_mod")
    XNEWP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWP, XNEWP_true)

    # ----------------------- case 6 --------------------------------------
    CLOCK = 31325760.0
    FINISH = 87591240.0
    XLAST = 1617.000
    SSQ = 2367.000
    CVTEST = 0.025
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 1 - 1  # 0-based index in Python
    RFLAG = 0
    ITAB = 11
    INDX = 0
    INTV = 5
    INTVT = 3580
    IOJ = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers
    NORR = 1 - 1  # be used as array index in the original Fortran code
    KVLOC = 1 - 1  # index of the area (used only if KWHERE=1) for convergence checking
    KVSTAT = 1
    KVTYPE = 2
    KVWHEN = 1
    KWHERE = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/ZB")
    ZB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB = year(
        ATRIB,
        CLOCK,
        CVTEST,
        DPLOLE,
        EUES,
        EVNTS,
        FINISH,
        HLOLE,
        IPOINT,
        MFA,
        NUMINQ,
        RFLAG,
        LSFLG,
        NAMA,
        SSQ,
        SUSTAT,
        XLAST,
        BB,
        LT,
        ZB,
        INTV,
        INTVT,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        LSTEP,
        NFCST,
        NORR,
        INDX,
        ITAB,
        LOLGHA,
        LOLGHP,
        LOLGPA,
        LOLGPP,
        LOLTHA,
        LOLTHP,
        LOLTPA,
        LOLTPP,
        MGNGHA,
        MGNGHP,
        MGNGPA,
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
    )

    XLAST_true = 1618.000
    SSQ_true = 2368.000
    MFA_true = 1 - 1  # 0-based index in Python
    NUMINQ_true = 7
    IPOINT_true = 1 - 1  # 0-based index in Python
    RFLAG_true = 1
    ITAB_true = 18
    INTVT_true = 3580

    assert XLAST_true == XLAST
    assert SSQ_true == SSQ
    assert MFA_true == MFA
    assert NUMINQ_true == NUMINQ
    assert IPOINT_true == IPOINT
    assert RFLAG_true == RFLAG
    assert ITAB_true == ITAB
    assert INTVT_true == INTVT

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/DPLOLE_mod")
    DPLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DPLOLE, DPLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/EUES_mod")
    EUES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(EUES, EUES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/HLOLE_mod")
    HLOLE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HLOLE, HLOLE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SUSTAT_mod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGHA_mod")
    SGNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHA, SGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGHP_mod")
    SGNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGHP, SGNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGPA_mod")
    SGNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPA, SGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNGPP_mod")
    SGNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNGPP, SGNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSHA_mod")
    SGNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHA, SGNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSHP_mod")
    SGNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSHP, SGNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSPA_mod")
    SGNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPA, SGNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNSPP_mod")
    SGNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNSPP, SGNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTHA_mod")
    SGNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHA, SGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTHP_mod")
    SGNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTHP, SGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTPA_mod")
    SGNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPA, SGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SGNTPP_mod")
    SGNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SGNTPP, SGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGHA_mod")
    SOLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHA, SOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGHP_mod")
    SOLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGHP, SOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGPA_mod")
    SOLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPA, SOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLGPP_mod")
    SOLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLGPP, SOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSHA_mod")
    SOLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHA, SOLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSHP_mod")
    SOLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSHP, SOLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSPA_mod")
    SOLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPA, SOLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLSPP_mod")
    SOLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLSPP, SOLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTHA_mod")
    SOLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHA, SOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTHP_mod")
    SOLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTHP, SOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTPA_mod")
    SOLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPA, SOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SOLTPP_mod")
    SOLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SOLTPP, SOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGHA_mod")
    SWLGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHA, SWLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGHP_mod")
    SWLGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGHP, SWLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGPA_mod")
    SWLGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPA, SWLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLGPP_mod")
    SWLGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLGPP, SWLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSHA_mod")
    SWLSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHA, SWLSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSHP_mod")
    SWLSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSHP, SWLSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSPA_mod")
    SWLSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPA, SWLSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLSPP_mod")
    SWLSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLSPP, SWLSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTHA_mod")
    SWLTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHA, SWLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTHP_mod")
    SWLTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTHP, SWLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTPA_mod")
    SWLTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPA, SWLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWLTPP_mod")
    SWLTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWLTPP, SWLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGHA_mod")
    SWNGHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHA, SWNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGHP_mod")
    SWNGHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGHP, SWNGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGPA_mod")
    SWNGPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPA, SWNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNGPP_mod")
    SWNGPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNGPP, SWNGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSHA_mod")
    SWNSHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHA, SWNSHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSHP_mod")
    SWNSHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSHP, SWNSHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSPA_mod")
    SWNSPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPA, SWNSPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNSPP_mod")
    SWNSPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNSPP, SWNSPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTHA_mod")
    SWNTHA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHA, SWNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTHP_mod")
    SWNTHP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTHP, SWNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTPA_mod")
    SWNTPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPA, SWNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/SWNTPP_mod")
    SWNTPP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SWNTPP, SWNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/XNEWA_mod")
    XNEWA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWA, XNEWA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_year/case6/XNEWP_mod")
    XNEWP_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XNEWP, XNEWP_true)
