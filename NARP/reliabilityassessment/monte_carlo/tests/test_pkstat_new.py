from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.pkstat import pkstat


def test_pkstat_new():
    TEST_DIR = Path(__file__).parent.absolute()

    # ------  case1 --------------
    NST = 1 - 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MARGIN")
    MARGIN = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)

    pkstat(NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLTPP_mod")
    LOLTPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTPP, LOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLGPP_mod")
    LOLGPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGPP, LOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLTPA_mod")
    LOLTPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTPA, LOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNTPA_mod")
    MGNTPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTPA, MGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNTPP_mod")
    MGNTPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTPP, MGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/LOLGPA_mod")
    LOLGPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGPA, LOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNGPA_mod")
    MGNGPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGPA, MGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case1/MGNGPP_mod")
    MGNGPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGPP, MGNGPP_true)

    # ------  case2 --------------
    NST = 1 - 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MARGIN")
    MARGIN = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)

    pkstat(NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLTPP_mod")
    LOLTPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTPP, LOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLGPP_mod")
    LOLGPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGPP, LOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLTPA_mod")
    LOLTPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTPA, LOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNTPA_mod")
    MGNTPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTPA, MGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNTPP_mod")
    MGNTPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTPP, MGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/LOLGPA_mod")
    LOLGPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGPA, LOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNGPA_mod")
    MGNGPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGPA, MGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case2/MGNGPP_mod")
    MGNGPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGPP, MGNGPP_true)

    # ------  case3 --------------
    NST = 1 - 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MARGIN")
    MARGIN = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLTPP")
    LOLTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLGPP")
    LOLGPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLTPA")
    LOLTPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNTPA")
    MGNTPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNTPP")
    MGNTPP = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLGPA")
    LOLGPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNGPA")
    MGNGPA = loadtxt(FileNameAndPath).astype(int)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNGPP")
    MGNGPP = loadtxt(FileNameAndPath).astype(int)

    pkstat(NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLTPP_mod")
    LOLTPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTPP, LOLTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLGPP_mod")
    LOLGPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGPP, LOLGPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLTPA_mod")
    LOLTPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLTPA, LOLTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNTPA_mod")
    MGNTPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTPA, MGNTPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNTPP_mod")
    MGNTPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNTPP, MGNTPP_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/LOLGPA_mod")
    LOLGPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(LOLGPA, LOLGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNGPA_mod")
    MGNGPA_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGPA, MGNGPA_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_pkstat/case3/MGNGPP_mod")
    MGNGPP_true = loadtxt(FileNameAndPath).astype(int)
    np.testing.assert_array_equal(MGNGPP, MGNGPP_true)
