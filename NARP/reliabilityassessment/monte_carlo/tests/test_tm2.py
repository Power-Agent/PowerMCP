from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.tm2 import tm2


def test_tm2():
    TEST_DIR = Path(__file__).parent.absolute()

    # --------------- case 1 --------------
    NR = 1 - 1  # 0-based index in Python!
    NLS = 1
    LCLOCK = 212  # NEED -1? maybe no need
    JHOUR = 212  # NEED -1? maybe no need
    IOI = 0
    JFLAG = 0

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BNS")
    BNS = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    FLOW, INDIC = tm2(
        BN,
        LP,
        BLP,
        BLP0,
        BB,
        ZB,
        LT,
        NR,
        NLS,
        BNS,
        LCLOCK,
        JHOUR,
        IOI,
        JFLAG,
        PLNDST,
        PCTAVL,
    )

    INDIC_true = 0
    assert INDIC == INDIC_true

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case1/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 2 --------------
    NR = 1 - 1  # 0-based index in Python!
    NLS = 1
    LCLOCK = 212  # NEED -1? maybe no need
    JHOUR = 212  # NEED -1? maybe no need
    IOI = 0
    JFLAG = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BNS")
    BNS = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    FLOW, INDIC = tm2(
        BN,
        LP,
        BLP,
        BLP0,
        BB,
        ZB,
        LT,
        NR,
        NLS,
        BNS,
        LCLOCK,
        JHOUR,
        IOI,
        JFLAG,
        PLNDST,
        PCTAVL,
    )

    INDIC_true = 0
    assert INDIC == INDIC_true

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=3)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case2/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true, decimal=5)

    # --------------- case 3 --------------
    NR = 1 - 1  # 0-based index in Python!
    NLS = 1
    LCLOCK = 227  # NEED -1? maybe no need
    JHOUR = 227  # NEED -1? maybe no need
    IOI = 0
    JFLAG = 0

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BNS")
    BNS = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    FLOW, INDIC = tm2(
        BN,
        LP,
        BLP,
        BLP0,
        BB,
        ZB,
        LT,
        NR,
        NLS,
        BNS,
        LCLOCK,
        JHOUR,
        IOI,
        JFLAG,
        PLNDST,
        PCTAVL,
    )

    INDIC_true = 0
    assert INDIC == INDIC_true

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case3/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 4 --------------
    NR = 1 - 1  # 0-based index in Python!
    NLS = 1
    LCLOCK = 227  # NEED -1? maybe no need
    JHOUR = 227  # NEED -1? maybe no need
    IOI = 0
    JFLAG = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BNS")
    BNS = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    FLOW, INDIC = tm2(
        BN,
        LP,
        BLP,
        BLP0,
        BB,
        ZB,
        LT,
        NR,
        NLS,
        BNS,
        LCLOCK,
        JHOUR,
        IOI,
        JFLAG,
        PLNDST,
        PCTAVL,
    )

    INDIC_true = 0
    assert INDIC == INDIC_true

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case4/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 5 --------------
    NR = 1 - 1  # 0-based index in Python!
    NLS = 1
    LCLOCK = 234  # NEED -1? maybe no need
    JHOUR = 234  # NEED -1? maybe no need
    IOI = 0
    JFLAG = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BNS")
    BNS = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    FLOW, INDIC = tm2(
        BN,
        LP,
        BLP,
        BLP0,
        BB,
        ZB,
        LT,
        NR,
        NLS,
        BNS,
        LCLOCK,
        JHOUR,
        IOI,
        JFLAG,
        PLNDST,
        PCTAVL,
    )

    INDIC_true = 0
    assert INDIC == INDIC_true

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_tm2/case5/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)
