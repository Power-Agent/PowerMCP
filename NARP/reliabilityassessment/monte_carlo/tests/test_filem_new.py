from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.filem import filem


def test_filem_new():
    TEST_DIR = Path(__file__).parent.absolute()

    # --------- case1 --------------
    MFA = 1 - 1  # 0-based index in Python
    NUMINQ = 0
    IPOINT = 0 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case1/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case1/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 5 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 1
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 1 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case1/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # ---------- case2 --------------
    MFA = 5 - 1  # 0-based index in Python
    NUMINQ = 1
    IPOINT = 1 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case2/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case2/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 9 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 2
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 1 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case2/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # ---------- case3 --------------
    MFA = 9 - 1  # 0-based index in Python
    NUMINQ = 2
    IPOINT = 1 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case3/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case3/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 13 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 3
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 1 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case3/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # ---------- case4 --------------
    MFA = 13 - 1  # 0-based index in Python
    NUMINQ = 3
    IPOINT = 1 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case4/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case4/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 17 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 4
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 1 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case4/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # ---------- case5 --------------
    MFA = 17 - 1  # 0-based index in Python
    NUMINQ = 4
    IPOINT = 1 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case5/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case5/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 21 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 5
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 1 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case5/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # ---------- case6 --------------
    MFA = 21 - 1  # 0-based index in Python
    NUMINQ = 5
    IPOINT = 1 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case6/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case6/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 25 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 6
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 21 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case6/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # ---------- case7 --------------
    MFA = 25 - 1  # 0-based index in Python
    NUMINQ = 6
    IPOINT = 21 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case7/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case7/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    MFA_true = 29 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 7
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 21 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_filem/case7/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)
