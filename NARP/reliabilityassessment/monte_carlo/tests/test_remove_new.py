from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.remove import remove


def test_remove_new():
    TEST_DIR = Path(__file__).parent.absolute()

    # --------- case1 --------------
    NUMINQ = 7
    IPOINT = 21 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case1/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case1/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    MFA, NUMINQ, IPOINT = remove(NUMINQ, ATRIB, EVNTS, IPOINT)

    MFA_true = 21 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 6
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 1 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case1/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case1/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # --------- case2 --------------
    NUMINQ = 7
    IPOINT = 1 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case2/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case2/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    MFA, NUMINQ, IPOINT = remove(NUMINQ, ATRIB, EVNTS, IPOINT)

    MFA_true = 1 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 6
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 25 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case2/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case2/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)

    # --------- case3 --------------
    NUMINQ = 7
    IPOINT = 25 - 1  # 0-based index in Python

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case3/ATRIB")
    ATRIB = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case3/EVNTS")
    EVNTS = loadtxt(FileNameAndPath)
    EVNTS = EVNTS[:-3]
    EVNTS[-4] = 0
    EVNTS[0 : 100 - 4 : 4] -= 1  # 0-based index in Python

    MFA, NUMINQ, IPOINT = remove(NUMINQ, ATRIB, EVNTS, IPOINT)

    MFA_true = 25 - 1  # 0-based index in Python
    assert MFA == MFA_true
    NUMINQ_true = 6
    assert NUMINQ == NUMINQ_true
    IPOINT_true = 21 - 1  # 0-based index in Python
    assert IPOINT == IPOINT_true

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case3/ATRIB_mod")
    ATRIB_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(ATRIB, ATRIB_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_remove/case3/EVNTS_mod")
    EVNTS_true = loadtxt(FileNameAndPath)
    EVNTS_true = EVNTS_true[:-3]
    EVNTS_true[-4] = 0
    EVNTS_true[0 : 100 - 4 : 4] -= 1  # 0-based index in Python
    np.testing.assert_array_almost_equal(EVNTS, EVNTS_true)
