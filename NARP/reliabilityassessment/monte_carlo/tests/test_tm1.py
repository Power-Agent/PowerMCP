from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.tm1 import tm1


def test_tm1():
    # ------------ case 1: artificial test data ------------------------------

    # NOAREA = 3, NLINES = 3
    NR = 1 - 1  # 0-based index in python!
    LP = np.array([[0, 0, 1], [1, 1, 2], [2, 2, 0]], dtype=int)
    BLP = np.array(
        [[-120.0, 300.0, 300.0], [-60.0, 150.0, 150.0], [-80.0, 100.0, 100.0]]
    )
    BN = np.array(
        [
            [0, 50.0, 100.0, 100.0, 0.0],
            [1, 50.0, 100.0, 100.0, 0.0],
            [2, 50.0, 100.0, 100.0, 0.0],
        ]
    )

    BLP0, BB, LT, ZB = tm1(BN, LP, BLP, NR)

    BLP0_true = np.array([-120.0, -60.0, -80.0])

    BB_true = np.array([[-180.0, 60.0, 0.0], [60.0, -140.0, 0.0], [0.0, 0.0, 0.0]])

    LT_true = np.array([1, 2, 0], dtype=int)

    ZB_true = np.array(
        [
            [-0.006481, -0.002778, 0.0],
            [-0.002778, -0.008333, 0.0],
            [0.0, 0.0, 0.0],
        ]
    )

    np.testing.assert_array_almost_equal(BLP0_true, BLP0)
    np.testing.assert_array_almost_equal(BB_true, BB)
    np.testing.assert_array_equal(LT_true, LT)
    np.testing.assert_array_almost_equal(ZB_true, ZB)

    # ------- case 2: test data from actual run of the Fortran program-----

    TEST_DIR = Path(__file__).parent.absolute()

    # NOAREA = 5, NLINES = 4
    NR = 1 - 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/BLP")
    BLP = loadtxt(FileNameAndPath)

    BLP0, BB, LT, ZB = tm1(BN, LP, BLP, NR)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/BLP0")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/BB")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/ZB")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm1/LT")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)
