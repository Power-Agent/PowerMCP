from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.linp import linp


def test_linp():
    TEST_DIR = Path(__file__).parent.absolute()

    # ------ test case 1--------------
    M, N, N1 = 30, 43, 38
    LCLOCK = 8490  # maybe need to minus 1?

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/A")
    A = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/XOB")
    XOB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/XOBI")
    XOBI = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/IBAS")
    IBAS = loadtxt(FileNameAndPath).astype(int)
    IBAS -= 1  # IBAS stands for cetrian array index
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/BS")
    BS = loadtxt(FileNameAndPath)

    N, TAB = linp(M, N, A, XOB, XOBI, IBAS, BS, LCLOCK, N1)

    N_true = 38
    assert N == N_true

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/IBAS_mod")
    IBAS_true = loadtxt(FileNameAndPath).astype(int)
    IBAS_true -= 1  # IBAS stands for cetrian array index
    np.testing.assert_array_equal(IBAS, IBAS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/XOB_mod")
    XOB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOB, XOB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/BS_mod")
    BS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BS, BS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case1/TAB")
    TAB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(TAB, TAB_true)

    # ------ test case 2--------------
    M, N, N1 = 30, 43, 38
    LCLOCK = 8986  # maybe need to minus 1?

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/A")
    A = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/XOB")
    XOB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/XOBI")
    XOBI = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/IBAS")
    IBAS = loadtxt(FileNameAndPath).astype(int)
    IBAS -= 1  # IBAS stands for cetrian array index
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/BS")
    BS = loadtxt(FileNameAndPath)

    N, TAB = linp(M, N, A, XOB, XOBI, IBAS, BS, LCLOCK, N1)

    N_true = 38
    assert N == N_true

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/IBAS_mod")
    IBAS_true = loadtxt(FileNameAndPath).astype(int)
    IBAS_true -= 1  # IBAS stands for cetrian array index
    np.testing.assert_array_equal(IBAS, IBAS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/XOB_mod")
    XOB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOB, XOB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/BS_mod")
    BS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BS, BS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case2/TAB")
    TAB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(TAB, TAB_true)

    # ------ test case 3--------------
    M, N, N1 = 30, 43, 38
    LCLOCK = 16889  # maybe need to minus 1?

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/A")
    A = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/XOB")
    XOB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/XOBI")
    XOBI = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/IBAS")
    IBAS = loadtxt(FileNameAndPath).astype(int)
    IBAS -= 1  # IBAS stands for cetrian array index
    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/BS")
    BS = loadtxt(FileNameAndPath)

    N, TAB = linp(M, N, A, XOB, XOBI, IBAS, BS, LCLOCK, N1)

    N_true = 38
    assert N == N_true

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/IBAS_mod")
    IBAS_true = loadtxt(FileNameAndPath).astype(int)
    IBAS_true -= 1  # IBAS stands for cetrian array index
    np.testing.assert_array_equal(IBAS, IBAS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/XOB_mod")
    XOB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOB, XOB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/BS_mod")
    BS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BS, BS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_linp/case3/TAB")
    TAB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(TAB, TAB_true)
