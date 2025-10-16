from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.data_processing.smaint import smaint


def test_smaint_new():
    TEST_DIR = Path(__file__).parent.absolute()
    # TEST_DIR = "C:\\Users\\zylpa\\Dropbox\\PostdocTAMU\\Code\\PyREL"

    NOAREA = 5
    ITAB, IREPM = 6, 1

    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/ID")
    ID = loadtxt(FileNameAndPath).astype(int)
    ID[:, [0, 1, 2, 3, 5]] -= 1  # 0-based index
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/RATES")
    RATES = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/PROBG")
    PROBG = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/DERATE")
    DERATE = loadtxt(FileNameAndPath).astype(int)
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/PKLOAD")
    PKLOAD = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/WPEAK")
    WPEAK = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/MINRAN")
    MINRAN = loadtxt(FileNameAndPath)
    MINRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/MAXRAN")
    MAXRAN = loadtxt(FileNameAndPath)
    MAXRAN -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/INHBT1")
    INHBT1 = loadtxt(FileNameAndPath)
    INHBT1 -= 1  # 0-based index in Python!
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/INHBT2")
    INHBT2 = loadtxt(FileNameAndPath)
    INHBT2 -= 1  # 0-based index in Python!

    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/NAMU")
    NAMU = loadtxt(FileNameAndPath, dtype=str, unpack=False)
    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/NUMP")
    NUMP = loadtxt(FileNameAndPath, dtype=str, unpack=False)

    JPLOUT, ITAB = smaint(
        NOAREA,
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

    FileNameAndPath = Path(TEST_DIR, "testdata_smaint/JPLOUT")
    JPLOUT_true = loadtxt(FileNameAndPath).astype(int)
    JPLOUT_true[:, 1:] -= 1  # 0-based index
    NUNITS = PROBG.shape[0]
    # the original Fortran version uses a magic size “120” for the 2nd-dim of JPLOUT;
    # which is not as robust as what we used in the Python verison, i.e., NUINTS+1;
    # Thus, a slight adjustment is needed for a fair comparison here.
    JPLOUT_true = np.hstack(
        (JPLOUT_true, -1 * np.ones((52, NUNITS + 1 - 120), dtype=int))
    )
    np.testing.assert_almost_equal(JPLOUT_true, JPLOUT)
