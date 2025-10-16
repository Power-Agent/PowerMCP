from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.conls import conls


def test_conls():
    NX, NR, NLS = 4, 1, 0
    # NL = 5 # not used
    NR -= 1  # 0-based index in Python!

    TEST_DIR = Path(__file__).parent.absolute()

    # -----------------------Test case 1 ----------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/BC")
    BC = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/INJ")
    INJ = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/BLP")
    BLP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/LOD")
    LOD = loadtxt(FileNameAndPath)

    M, N, N1, A, XOB, XOBI, IBAS, BS, B, B1, TAB = conls(
        BC, INJ, NX, NR, LT, BLP, LP, BN, LOD, NLS
    )

    M_true, N_true, N1_true = 35, 53, 48
    assert M == M_true
    assert N == N_true
    assert N1 == N1_true

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/A")
    A_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/XOB")
    XOB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOB, XOB_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/XOBI")
    XOBI_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOBI, XOBI_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/IBAS")
    IBAS_true = loadtxt(FileNameAndPath).astype(int)
    IBAS_true -= 1  # 0-based index in Python!
    IBAS_true = IBAS_true[:M]
    np.testing.assert_array_equal(IBAS, IBAS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/BS")
    BS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BS, BS_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/B")
    B_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(B, B_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/B1")
    B1_true = loadtxt(FileNameAndPath)
    B1_true = B1_true[:M]
    np.testing.assert_array_almost_equal(B1, B1_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case1/TAB")
    TAB_true = loadtxt(FileNameAndPath)
    TAB_true = TAB_true[:M, :N]
    np.testing.assert_array_almost_equal(TAB, TAB_true, decimal=5)

    # -----------------------Test case 2 ----------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/BC")
    BC = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/INJ")
    INJ = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/BLP")
    BLP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/LOD")
    LOD = loadtxt(FileNameAndPath)

    M, N, N1, A, XOB, XOBI, IBAS, BS, B, B1, TAB = conls(
        BC, INJ, NX, NR, LT, BLP, LP, BN, LOD, NLS
    )

    M_true, N_true, N1_true = 35, 53, 48
    assert M == M_true
    assert N == N_true
    assert N1 == N1_true

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/A")
    A_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/XOB")
    XOB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOB, XOB_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/XOBI")
    XOBI_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOBI, XOBI_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/IBAS")
    IBAS_true = loadtxt(FileNameAndPath).astype(int)
    IBAS_true -= 1  # 0-based index in Python!
    IBAS_true = IBAS_true[:M]
    np.testing.assert_array_equal(IBAS, IBAS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/BS")
    BS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BS, BS_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/B")
    B_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(B, B_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/B1")
    B1_true = loadtxt(FileNameAndPath)
    B1_true = B1_true[:M]
    np.testing.assert_array_almost_equal(B1, B1_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case2/TAB")
    TAB_true = loadtxt(FileNameAndPath)
    TAB_true = TAB_true[:M, :N]
    np.testing.assert_array_almost_equal(TAB, TAB_true, decimal=5)

    # -----------------------Test case 3 ----------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/BC")
    BC = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/INJ")
    INJ = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/BLP")
    BLP = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!
    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/LOD")
    LOD = loadtxt(FileNameAndPath)

    M, N, N1, A, XOB, XOBI, IBAS, BS, B, B1, TAB = conls(
        BC, INJ, NX, NR, LT, BLP, LP, BN, LOD, NLS
    )

    M_true, N_true, N1_true = 35, 53, 48
    assert M == M_true
    assert N == N_true
    assert N1 == N1_true

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/A")
    A_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(A, A_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/XOB")
    XOB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOB, XOB_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/XOBI")
    XOBI_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(XOBI, XOBI_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/IBAS")
    IBAS_true = loadtxt(FileNameAndPath).astype(int)
    IBAS_true -= 1  # 0-based index in Python!
    IBAS_true = IBAS_true[:M]
    np.testing.assert_array_equal(IBAS, IBAS_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/BS")
    BS_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BS, BS_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/B")
    B_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(B, B_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/B1")
    B1_true = loadtxt(FileNameAndPath)
    B1_true = B1_true[:M]
    np.testing.assert_array_almost_equal(B1, B1_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_conls/case3/TAB")
    TAB_true = loadtxt(FileNameAndPath)
    TAB_true = TAB_true[:M, :N]
    np.testing.assert_array_almost_equal(TAB, TAB_true, decimal=5)

    return
