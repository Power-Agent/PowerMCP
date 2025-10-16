from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.dgefa import dgefa


def test_dgefa():
    TEST_DIR = Path(__file__).parent.absolute()

    # ------ test case 1--------------
    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/A")
    A = loadtxt(FileNameAndPath)

    N = 30
    INFO, IPVT = dgefa(A, N)

    INFO_true = 0
    assert INFO == INFO_true

    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/IPVT")
    IPVT_true = loadtxt(FileNameAndPath).astype(int)
    IPVT_true -= 1  # 0-based index in Python
    np.testing.assert_array_equal(IPVT, IPVT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/A_modified")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true)

    # ------ test case 2--------------
    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/A2")
    A = loadtxt(FileNameAndPath)

    N = 30
    INFO, IPVT = dgefa(A, N)

    INFO_true = 0
    assert INFO == INFO_true

    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/IPVT2")
    IPVT_true = loadtxt(FileNameAndPath).astype(int)
    IPVT_true -= 1  # 0-based index in Python
    np.testing.assert_array_equal(IPVT, IPVT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/A_modified2")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true)

    # ------ test case 3--------------
    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/A3")
    A = loadtxt(FileNameAndPath)

    N = 30
    INFO, IPVT = dgefa(A, N)

    INFO_true = 0
    assert INFO == INFO_true

    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/IPVT3")
    IPVT_true = loadtxt(FileNameAndPath).astype(int)
    IPVT_true -= 1  # 0-based index in Python
    np.testing.assert_array_equal(IPVT, IPVT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_dgefa/A_modified3")
    A_modified_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_modified_true)
