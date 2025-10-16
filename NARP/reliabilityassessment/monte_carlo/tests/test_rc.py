from pathlib import Path

from numpy import loadtxt

from reliabilityassessment.monte_carlo.rc import rc


def test_rc():
    TEST_DIR = Path(__file__).parent.absolute()

    FileNameAndPath = Path(TEST_DIR, "testdata_rc/PY")
    PY = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_rc/A")
    A = loadtxt(FileNameAndPath)

    M = 30
    IND = 1 - 1  # be careful: 0-based index in Python
    PROD = rc(M, PY, A, IND)

    PROD_true = -1.00000
    assert PROD == PROD_true
