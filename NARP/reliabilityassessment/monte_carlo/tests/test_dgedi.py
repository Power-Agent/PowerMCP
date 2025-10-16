from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.dgedi import dgedi


def test_dgedi():
    TEST_DIR = Path(__file__).parent.absolute()

    # ------ test case 1--------------
    N = 30

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/A1")
    A = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/IPVT1")
    IPVT = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!

    dgedi(A, N, IPVT)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/A1_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true, decimal=4)

    # ------ test case 2--------------
    N = 30

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/A2")
    A = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/IPVT2")
    IPVT = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!

    dgedi(A, N, IPVT)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/A2_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true, decimal=4)

    # ------ test case 3--------------
    N = 30

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/A3")
    A = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/IPVT3")
    IPVT = -1 + loadtxt(FileNameAndPath).astype(int)  # 0-based index in python!

    dgedi(A, N, IPVT)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgedi/A3_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true, decimal=4)
