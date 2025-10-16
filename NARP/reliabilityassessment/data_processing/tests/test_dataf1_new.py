from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.data_processing.dataf1 import dataf1

TEST_DIR = Path(__file__).parent.absolute()


def test_dataf1_new():
    filepaths = [
        Path(TEST_DIR, "testdata_input_processing"),
        Path(TEST_DIR, "testdata_input_processing/LEEI"),
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

    NORR_true = 1 - 1  # 0-based index in Python
    NFCST_true = 1
    NOAREA_true = 5
    MXCRIT_true = 0
    ITAB_true = 11

    assert NORR == NORR_true
    assert NFCST == NFCST_true
    assert NOAREA == NOAREA_true
    assert MXCRIT == MXCRIT_true
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/QTR")
    QTR_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(QTR, QTR_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/PKLOAD")
    PKLOAD_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(PKLOAD, PKLOAD_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/FU")
    FU_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FU, FU_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/MINRAN")
    MINRAN_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(MINRAN, MINRAN_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/MAXRAN")
    MAXRAN_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(MAXRAN, MAXRAN_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/INHBT1")
    INHBT1_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(INHBT1, INHBT1_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/INHBT2")
    INHBT2_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(INHBT2, INHBT2_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/BN")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/SUSTAT_RESCA")
    SUSTAT_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SUSTAT, SUSTAT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/FCTERR")
    FCTERR_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FCTERR, FCTERR_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/CAPCON")
    CAPCON_true = loadtxt(FileNameAndPath).astype(int)
    CAPCON_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(CAPCON, CAPCON_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/CAPOWN")
    CAPOWN_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(CAPOWN, CAPOWN_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/NOGEN")
    NOGEN_true = loadtxt(FileNameAndPath).astype(
        int
    )  # total number of gen units of each area
    np.testing.assert_array_equal(NOGEN, NOGEN_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/PROBG")
    PROBG_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(PROBG, PROBG_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/DERATE")
    DERATE_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DERATE, DERATE_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/JENT")
    JENT_true = loadtxt(FileNameAndPath).astype(int)
    JENT_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(JENT, JENT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/INTCH")
    INTCH_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(INTCH, INTCH_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/INTCHR")
    INTCHR_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(INTCHR, INTCHR_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/LP")
    LP_true = loadtxt(FileNameAndPath).astype(int)
    LP_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(LP, LP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/LINENO")
    LINENO_true = loadtxt(FileNameAndPath).astype(int)
    LINENO_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(LINENO, LINENO_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/PROBL")
    PROBL_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(PROBL, PROBL_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/BLPA")
    BLPA_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLPA, BLPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/JCRIT")
    JCRIT_true = (
        np.array([]) if MXCRIT == 0 else -1 + loadtxt(FileNameAndPath).astype(int)
    )  # 0-based index in python!
    np.testing.assert_array_equal(JCRIT, JCRIT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/MAXHR")
    MAXHR_true = loadtxt(FileNameAndPath).astype(int)
    MAXHR_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(MAXHR, MAXHR_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/MAXDAY")
    MAXDAY_true = loadtxt(FileNameAndPath).astype(int)
    MAXDAY_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(MAXDAY, MAXDAY_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/DYLOAD")
    DYLOAD_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(DYLOAD, DYLOAD_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/WPEAK")
    WPEAK_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(WPEAK, WPEAK_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/MXPLHR")
    MXPLHR_true = loadtxt(FileNameAndPath).astype(int)
    MXPLHR_true -= 1  # 0-based index in python!
    np.testing.assert_array_equal(MXPLHR, MXPLHR_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/HRLOAD_XPOS")
    HRLOAD_XPOS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(HRLOAD, HRLOAD_XPOS_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/RATES")
    RATES_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(RATES, RATES_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/ID_modified")
    ID_true = loadtxt(FileNameAndPath).astype(int)
    ID_true[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    np.testing.assert_array_equal(ID, ID_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/JPLOUT")
    JPLOUT_true = loadtxt(FileNameAndPath).astype(int)
    JPLOUT_true[:, 1:] -= 1  # 0-based index
    np.testing.assert_array_equal(JPLOUT, JPLOUT_true)

    assert NLS == 1
    assert IOI == 0
    assert IOJ == 0
    assert KVLOC == 1 - 1  # 0-based index in Python;
    assert KVSTAT == 1
    assert KVTYPE == 2
    assert KVWHEN == 1
    assert KWHERE == 1
    assert CVTEST == 0.025
    assert MAXEUE == 1000
    assert JSTEP == 1
    assert JFREQ == 1
    assert FINISH == 9999 * 8760.0
    assert INTV == 5
    assert INTVT == 5

    assert NR == 1 - 1  # 0-based index

    FileNameAndPath = Path(TEST_DIR, "testdata_input_processing/NAMA")
    with open(FileNameAndPath, "r") as file:
        NAMA_true = [e.strip("\n") for e in file.readlines()]
    assert NAMA == NAMA_true
