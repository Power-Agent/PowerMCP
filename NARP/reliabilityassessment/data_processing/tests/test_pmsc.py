from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.data_processing.pmsc import pmsc


def test_pmsc():
    TEST_DIR = Path(__file__).parent.absolute()

    # --------------------------case1-------------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/ID")
    ID = loadtxt(FileNameAndPath).astype(int)
    ID[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/RATES")
    RATES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/PROBG")
    PROBG = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/DERATE")
    DERATE = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/PKLOAD")
    PKLOAD = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/WPEAK")
    WPEAK = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/MINRAN")
    MINRAN = loadtxt(FileNameAndPath)
    MINRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/MAXRAN")
    MAXRAN = loadtxt(FileNameAndPath)
    MAXRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/INHBT1")
    INHBT1 = loadtxt(FileNameAndPath)
    INHBT1 -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/INHBT2")
    INHBT2 = loadtxt(FileNameAndPath)
    INHBT2 -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/NAMU")
    NAMU = loadtxt(FileNameAndPath, dtype=str, unpack=False)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/NUMP")
    NUMP = loadtxt(FileNameAndPath, dtype=str, unpack=False)

    IA = 1 - 1  # in Python, 0-based integer index!
    ITAB = 6  # in Python, 0-based integer index!
    IREPM = 1  # this variable does not stands for an integer index.

    ITAB = pmsc(
        IA,
        ID,
        ITAB,
        RATES,
        PROBG,
        DERATE,
        PKLOAD,
        WPEAK,
        IREPM,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        NAMU,
        NUMP,
    )

    ITAB_true = 7
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case1/ID_modified")
    ID_true = loadtxt(FileNameAndPath).astype(int)
    ID_true[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index

    np.testing.assert_array_equal(ID, ID_true)

    # --------------------------case2-------------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/ID")
    ID = loadtxt(FileNameAndPath).astype(int)
    ID[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/RATES")
    RATES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/PROBG")
    PROBG = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/DERATE")
    DERATE = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/PKLOAD")
    PKLOAD = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/WPEAK")
    WPEAK = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/MINRAN")
    MINRAN = loadtxt(FileNameAndPath)
    MINRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/MAXRAN")
    MAXRAN = loadtxt(FileNameAndPath)
    MAXRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/INHBT1")
    INHBT1 = loadtxt(FileNameAndPath)
    INHBT1 -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/INHBT2")
    INHBT2 = loadtxt(FileNameAndPath)
    INHBT2 -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/NAMU")
    NAMU = loadtxt(FileNameAndPath, dtype=str, unpack=False)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/NUMP")
    NUMP = loadtxt(FileNameAndPath, dtype=str, unpack=False)

    IA = 2 - 1  # in Python, 0-based integer index!
    ITAB = 7  # in Python, 0-based integer index!
    IREPM = 1  # this variable does not stands for an integer index.

    ITAB = pmsc(
        IA,
        ID,
        ITAB,
        RATES,
        PROBG,
        DERATE,
        PKLOAD,
        WPEAK,
        IREPM,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        NAMU,
        NUMP,
    )

    ITAB_true = 8
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case2/ID_modified")
    ID_true = loadtxt(FileNameAndPath).astype(int)
    ID_true[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index

    np.testing.assert_array_equal(ID, ID_true)

    # --------------------------case3-------------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/ID")
    ID = loadtxt(FileNameAndPath).astype(int)
    ID[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/RATES")
    RATES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/PROBG")
    PROBG = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/DERATE")
    DERATE = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/PKLOAD")
    PKLOAD = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/WPEAK")
    WPEAK = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/MINRAN")
    MINRAN = loadtxt(FileNameAndPath)
    MINRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/MAXRAN")
    MAXRAN = loadtxt(FileNameAndPath)
    MAXRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/INHBT1")
    INHBT1 = loadtxt(FileNameAndPath)
    INHBT1 -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/INHBT2")
    INHBT2 = loadtxt(FileNameAndPath)
    INHBT2 -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/NAMU")
    NAMU = loadtxt(FileNameAndPath, dtype=str, unpack=False)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/NUMP")
    NUMP = loadtxt(FileNameAndPath, dtype=str, unpack=False)

    IA = 3 - 1  # in Python, 0-based integer index!
    ITAB = 8  # in Python, 0-based integer index!
    IREPM = 1  # this variable does not stands for an integer index.

    ITAB = pmsc(
        IA,
        ID,
        ITAB,
        RATES,
        PROBG,
        DERATE,
        PKLOAD,
        WPEAK,
        IREPM,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        NAMU,
        NUMP,
    )

    ITAB_true = 9
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case3/ID_modified")
    ID_true = loadtxt(FileNameAndPath).astype(int)
    ID_true[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index

    np.testing.assert_array_equal(ID, ID_true)

    # --------------------------case4-------------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/ID")
    ID = loadtxt(FileNameAndPath).astype(int)
    ID[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/RATES")
    RATES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/PROBG")
    PROBG = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/DERATE")
    DERATE = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/PKLOAD")
    PKLOAD = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/WPEAK")
    WPEAK = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/MINRAN")
    MINRAN = loadtxt(FileNameAndPath)
    MINRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/MAXRAN")
    MAXRAN = loadtxt(FileNameAndPath)
    MAXRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/INHBT1")
    INHBT1 = loadtxt(FileNameAndPath)
    INHBT1 -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/INHBT2")
    INHBT2 = loadtxt(FileNameAndPath)
    INHBT2 -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/NAMU")
    NAMU = loadtxt(FileNameAndPath, dtype=str, unpack=False)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/NUMP")
    NUMP = loadtxt(FileNameAndPath, dtype=str, unpack=False)

    IA = 4 - 1  # in Python, 0-based integer index!
    ITAB = 9  # in Python, 0-based integer index!
    IREPM = 1  # this variable does not stands for an integer index.

    ITAB = pmsc(
        IA,
        ID,
        ITAB,
        RATES,
        PROBG,
        DERATE,
        PKLOAD,
        WPEAK,
        IREPM,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        NAMU,
        NUMP,
    )

    ITAB_true = 10
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case4/ID_modified")
    ID_true = loadtxt(FileNameAndPath).astype(int)
    ID_true[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index

    np.testing.assert_array_equal(ID, ID_true)

    # --------------------------case5-------------------------
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/ID")
    ID = loadtxt(FileNameAndPath).astype(int)
    ID[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/RATES")
    RATES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/PROBG")
    PROBG = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/DERATE")
    DERATE = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/PKLOAD")
    PKLOAD = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/WPEAK")
    WPEAK = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/MINRAN")
    MINRAN = loadtxt(FileNameAndPath)
    MINRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/MAXRAN")
    MAXRAN = loadtxt(FileNameAndPath)
    MAXRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/INHBT1")
    INHBT1 = loadtxt(FileNameAndPath)
    INHBT1 -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/INHBT2")
    INHBT2 = loadtxt(FileNameAndPath)
    INHBT2 -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/NAMU")
    NAMU = loadtxt(FileNameAndPath, dtype=str, unpack=False)
    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/NUMP")
    NUMP = loadtxt(FileNameAndPath, dtype=str, unpack=False)

    IA = 5 - 1  # in Python, 0-based integer index!
    ITAB = 10  # in Python, 0-based integer index!
    IREPM = 1  # this variable does not stands for an integer index.

    ITAB = pmsc(
        IA,
        ID,
        ITAB,
        RATES,
        PROBG,
        DERATE,
        PKLOAD,
        WPEAK,
        IREPM,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        NAMU,
        NUMP,
    )

    ITAB_true = 11
    assert ITAB == ITAB_true

    FileNameAndPath = Path(TEST_DIR, "testdata_pmsc/case5/ID_modified")
    ID_true = loadtxt(FileNameAndPath).astype(int)
    ID_true[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index

    np.testing.assert_array_equal(ID, ID_true)
