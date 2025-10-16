from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.hrstat import hrstat


def test_hrstat_new():
    TEST_DIR = Path(__file__).parent.absolute()

    # ------  case1 --------------
    NST = 1 - 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MARGIN")
    MARGIN = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)

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

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LSFLG_mod")
    LSFLG_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LSFLG, LSFLG_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLTHP_mod")
    LOLTHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTHP, LOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLGHP_mod")
    LOLGHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGHP, LOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLTHA_mod")
    LOLTHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTHA, LOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNTHA_mod")
    MGNTHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTHA, MGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNTHP_mod")
    MGNTHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTHP, MGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/LOLGHA_mod")
    LOLGHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGHA, LOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNGHA_mod")
    MGNGHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGHA, MGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case1/MGNGHP_mod")
    MGNGHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGHP, MGNGHP_true)

    # ------  case2 --------------
    NST = 1 - 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MARGIN")
    MARGIN = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)

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

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LSFLG_mod")
    LSFLG_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LSFLG, LSFLG_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLTHP_mod")
    LOLTHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTHP, LOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLGHP_mod")
    LOLGHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGHP, LOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLTHA_mod")
    LOLTHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTHA, LOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNTHA_mod")
    MGNTHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTHA, MGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNTHP_mod")
    MGNTHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTHP, MGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/LOLGHA_mod")
    LOLGHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGHA, LOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNGHA_mod")
    MGNGHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGHA, MGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case2/MGNGHP_mod")
    MGNGHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGHP, MGNGHP_true)

    # ------  case3 --------------
    NST = 1 - 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LSFLG")
    LSFLG = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MARGIN")
    MARGIN = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLTHP")
    LOLTHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLGHP")
    LOLGHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLTHA")
    LOLTHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNTHA")
    MGNTHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNTHP")
    MGNTHP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLGHA")
    LOLGHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNGHA")
    MGNGHA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNGHP")
    MGNGHP = loadtxt(FileNameAndPath).astype(int)

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

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LSFLG_mod")
    LSFLG_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LSFLG, LSFLG_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLTHP_mod")
    LOLTHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTHP, LOLTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLGHP_mod")
    LOLGHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGHP, LOLGHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLTHA_mod")
    LOLTHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTHA, LOLTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNTHA_mod")
    MGNTHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTHA, MGNTHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNTHP_mod")
    MGNTHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTHP, MGNTHP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/LOLGHA_mod")
    LOLGHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGHA, LOLGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNGHA_mod")
    MGNGHA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGHA, MGNGHA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_hrstat/case3/MGNGHP_mod")
    MGNGHP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGHP, MGNGHP_true)
