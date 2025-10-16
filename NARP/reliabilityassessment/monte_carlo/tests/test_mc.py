from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.mc import mc


def test_mc():
    TEST_DIR = Path(__file__).parent.absolute()

    FileNameAndPath = Path(TEST_DIR, "testdata_mc/TAB")
    TAB = loadtxt(FileNameAndPath)
    FileNameAndPath = Path(TEST_DIR, "testdata_mc/A")
    A = loadtxt(FileNameAndPath)

    M = 30
    IN = 3 - 1  # be careful: 0-based index in Python
    CO = mc(M, IN, TAB, A)

    CO_true = np.array(
        [
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.000000,
            0.500000,
            -120.000000,
            0.000000,
            0.000000,
            0.000000,
            -0.500000,
            120.000000,
            0.000000,
            0.000000,
            0.500000,
            -120.500000,
            120.000000,
            0.000000,
            0.000000,
            -0.500000,
            120.500000,
            -120.000000,
            0.000000,
            0.000000,
            0.500000,
            120.500000,
            120.000000,
            0.000000,
            0.000000,
        ]
    )

    np.testing.assert_array_almost_equal(CO, CO_true)
