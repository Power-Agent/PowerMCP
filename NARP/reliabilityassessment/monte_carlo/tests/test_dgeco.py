from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.dgeco import dgeco


def test_dgeco():
    TEST_DIR = Path(__file__).parent.absolute()

    # ------ test case 1--------------
    N = 30

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/A1")
    A = loadtxt(FileNameAndPath)

    IPVT = dgeco(A, N)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/IPVT1")
    IPVT_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(IPVT, IPVT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/A1_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true)

    # ------ test case 2--------------
    N = 30

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/A2")
    A = loadtxt(FileNameAndPath)

    IPVT = dgeco(A, N)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/IPVT2")
    IPVT_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(IPVT, IPVT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/A2_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true)

    # ------ test case 3--------------
    N = 30

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/A3")
    A = loadtxt(FileNameAndPath)

    IPVT = dgeco(A, N)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/IPVT3")
    IPVT_true = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!
    np.testing.assert_array_equal(IPVT, IPVT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgeco/A3_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true)
