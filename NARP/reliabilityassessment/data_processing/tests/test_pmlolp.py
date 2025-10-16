from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.data_processing.pmlolp import pmlolp


def test_pmlolp():
    TEST_DIR = Path(__file__).parent.absolute()

    CAPLOS = np.zeros(500, dtype=int)
    CAPLOS[:32] = np.array(
        [
            12,
            12,
            12,
            12,
            12,
            20,
            20,
            20,
            20,
            50,
            50,
            50,
            50,
            50,
            50,
            76,
            76,
            76,
            76,
            100,
            100,
            100,
            155,
            155,
            155,
            155,
            197,
            197,
            197,
            350,
            400,
            400,
        ],
        dtype=int,
    )

    FileNameAndPath = Path(TEST_DIR, "testdata_pmlolp/RD")
    RD = loadtxt(FileNameAndPath)

    NGS_true = 213

    FileNameAndPath = Path(TEST_DIR, "testdata_pmlolp/PA_modified")
    PA_true = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_pmlolp/KA_modified")
    KA_true = loadtxt(FileNameAndPath, dtype=int)

    NGU = 32

    NGS, KA, PA = pmlolp(CAPLOS, RD, NGU)

    assert NGS == NGS_true
    np.testing.assert_array_almost_equal(KA, KA_true)
    np.testing.assert_array_almost_equal(PA, PA_true, decimal=4)
