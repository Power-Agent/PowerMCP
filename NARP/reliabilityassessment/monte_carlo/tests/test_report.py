from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.report import report


def test_report():
    TEST_DIR = Path(__file__).parent.absolute()

    # --------------------- case 1 --------------------------
    IYEAR = 3576  # note: 1-based as the same as in orignal Fortran code
    ITAB = 11
    INDX = 0
    LSTEP = 50  # may need to double check if it is 0- or 1-based
    NFCST = 1  # total number of forecast-tiers

    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SUSTAT")
    SUSTAT = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/DPLOLE")
    DPLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/EUES")
    EUES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/HLOLE")
    HLOLE = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA = [e.strip("\n") for e in file.readlines()]
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNGHA")
    SGNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNGHP")
    SGNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNGPA")
    SGNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNGPP")
    SGNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNSHA")
    SGNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNSHP")
    SGNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNSPA")
    SGNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNSPP")
    SGNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNTHA")
    SGNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNTHP")
    SGNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNTPA")
    SGNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SGNTPP")
    SGNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLGHA")
    SOLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLGHP")
    SOLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLGPA")
    SOLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLGPP")
    SOLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLSHA")
    SOLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLSHP")
    SOLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLSPA")
    SOLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLSPP")
    SOLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLTHA")
    SOLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLTHP")
    SOLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLTPA")
    SOLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SOLTPP")
    SOLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLGHA")
    SWLGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLGHP")
    SWLGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLGPA")
    SWLGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLGPP")
    SWLGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLSHA")
    SWLSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLSHP")
    SWLSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLSPA")
    SWLSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLSPP")
    SWLSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLTHA")
    SWLTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLTHP")
    SWLTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLTPA")
    SWLTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWLTPP")
    SWLTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNGHA")
    SWNGHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNGHP")
    SWNGHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNGPA")
    SWNGPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNGPP")
    SWNGPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNSHA")
    SWNSHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNSHP")
    SWNSHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNSPA")
    SWNSPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNSPP")
    SWNSPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNTHA")
    SWNTHA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNTHP")
    SWNTHP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNTPA")
    SWNTPA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SWNTPP")
    SWNTPP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/XNEWA")
    XNEWA = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/XNEWP")
    XNEWP = loadtxt(FileNameAndPath)

    ITAB = report(
        IYEAR,
        ITAB,
        INDX,
        SUSTAT,
        DPLOLE,
        EUES,
        HLOLE,
        LSTEP,
        NAMA,
        NFCST,
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

    ITAB_true = 18
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_report/case1/SUSTATmod")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true, decimal=5)
