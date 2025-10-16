from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.transm import transm


def test_transm():
    TEST_DIR = Path(__file__).parent.absolute()

    # --------------- case 1 --------------
    IFLAG = 0
    JFLAG = 0
    CLOCK = 212.0
    JHOUR = 212
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case1/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true, decimal=5)

    # --------------- case 2 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 227.0
    JHOUR = 227
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case2/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 3 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 234.0
    JHOUR = 234
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case3/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 4 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 253.0
    JHOUR = 253
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case4/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 5 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 347.0
    JHOUR = 347
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case5/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 6 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 2923.0
    JHOUR = 2923
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=3)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case6/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true, decimal=5)

    # --------------- case 7 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 4073.0
    JHOUR = 4073
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case7/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true, decimal=5)

    # --------------- case 8 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 7103.0
    JHOUR = 7103
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=5)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case8/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 9 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 8730.0
    JHOUR = 8730
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case9/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)

    # --------------- case 10 --------------
    IFLAG = 1
    JFLAG = 0
    CLOCK = 8946.0
    JHOUR = 186
    IOI = 0
    NR = 1 - 1  # 0-based index in Python
    NLS = 1

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BN")
    BN = loadtxt(FileNameAndPath)
    BN[:, 0] -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BLPA")
    BLPA = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BLP0")
    BLP0 = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BB")
    BB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/LT")
    LT = loadtxt(FileNameAndPath).astype(int)
    LT -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/ZB")
    ZB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/STMULT")
    STMULT = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/LNSTAT")
    LNSTAT = loadtxt(FileNameAndPath).astype(int)  # note: no need to -1!

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/TRNSFR")
    TRNSFR = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/TRNSFJ")
    TRNSFJ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/SYSCON")
    SYSCON = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/CAPREQ")
    CAPREQ = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/PLNDST")
    PLNDST = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/PCTAVL")
    PCTAVL = loadtxt(FileNameAndPath)

    JFLAG, FLOW, SADJ = transm(
        IFLAG,
        JFLAG,
        CLOCK,
        JHOUR,
        IOI,
        BN,
        BLPA,
        BLP0,
        BB,
        LT,
        ZB,
        LP,
        NR,
        STMULT,
        LNSTAT,
        NLS,
        TRNSFR,
        TRNSFJ,
        SYSCON,
        CAPREQ,
        PLNDST,
        PCTAVL,
    )

    JFLAG_true = 1
    assert JFLAG == JFLAG_true

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BLP0_mod")
    BLP0_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BLP0, BLP0_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BB_mod")
    BB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(BB, BB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/LT_mod")
    LT_true = loadtxt(FileNameAndPath).astype(int)
    LT_true -= 1  # 0-based index in Python!
    np.testing.assert_array_equal(LT, LT_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/ZB_mod")
    ZB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ZB, ZB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/SADJ")
    SADJ_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SADJ, SADJ_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_transm/case10/BN_mod")
    BN_true = loadtxt(FileNameAndPath)
    BN_true[:, 0] -= 1  # 0-based index in python!
    np.testing.assert_array_almost_equal(BN, BN_true)
