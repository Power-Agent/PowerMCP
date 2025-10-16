from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.rm import rm


def test_rm():
    TEST_DIR = Path(__file__).parent.absolute()

    FileNameAndPath = Path(TEST_DIR, "testdata_rm/TAB")
    TAB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_rm/CB")
    CB = loadtxt(FileNameAndPath)

    M = 30
    PY = rm(M, CB, TAB)

    PY_true = np.array(
        [
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            1.000000,
            1.000000,
            1.000000,
            1.000000,
            1.000000,
        ]
    )

    np.testing.assert_array_almost_equal(PY, PY_true)
