from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.data_processing.xldnew import xldnew

TEST_DIR = Path(__file__).parent.absolute()


def test_xldnew():
    PKLOAD = np.array([6000, 9000]).T
    FileNameAndPath = Path(TEST_DIR, "unit_test_input_for_xldnew")
    HRLOAD = xldnew(FileNameAndPath, PKLOAD)
    HRLOAD_truth = loadtxt(Path(TEST_DIR, "ground_truth_for_xldnew.txt"), unpack=False)
    np.testing.assert_array_almost_equal(HRLOAD, HRLOAD_truth.T)
