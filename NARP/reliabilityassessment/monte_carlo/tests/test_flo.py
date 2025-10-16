from pathlib import Path

import numpy as np
from numpy import loadtxt

from reliabilityassessment.monte_carlo.flo import flo


def test_flo():
    # NOAREA = 3
    # NLINES = 3
    # SFLOW = np.zeros((NOAREA,))
    # FLOW = np.zeros((NLINES,))
    LP = np.array([[0, 0, 1], [1, 1, 2], [2, 2, 0]], dtype=int)
    BLP = np.array([[-120, 300, 300], [-60, 150, 150], [-80, 100, 100]])
    THET = np.array([0.1, 0.2, 0.3])  # shape: (NOAREA,)

    FLOW_ = np.array([12.0, 6.0, -16.0])
    SFLOW_ = np.array([-28.0, 6.0, 22.0])

    SFLOW, FLOW = flo(LP, BLP, THET)
    np.testing.assert_array_almost_equal(FLOW, FLOW_)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_)

    # NOAREA = 3
    # NLINES = 2
    # SFLOW = np.zeros((NOAREA,))
    # FLOW = np.zeros((NLINES,))
    LP = np.array([[0, 0, 1], [1, 2, 0]], dtype=int)
    BLP = np.array([[-120, 300, 300], [-80, 100, 100]])
    THET = np.array([0.1, 0.2, 0.3])  # shape: (NOAREA,)

    FLOW_ = np.array([12.0, -16.0])
    SFLOW_ = np.array([-28.0, 12.0, 16.0])

    SFLOW, FLOW = flo(LP, BLP, THET)
    np.testing.assert_array_almost_equal(FLOW, FLOW_)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_)

    # ---------------- Extra unit test cases added in Oct. 2022-------------
    # NOAREA = 5
    # NLINES = 5
    # SFLOW = np.zeros((NOAREA,))
    # FLOW = np.zeros((NLINES,))
    TEST_DIR = Path(__file__).parent.absolute()

    # --------------- case 1 --------------
    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case1/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case1/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case1/THET")
    THET = loadtxt(FileNameAndPath)

    SFLOW, FLOW = flo(LP, BLP, THET)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case1/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case1/SFLOW")
    SFLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_true)

    # --------------- case 2 --------------
    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case2/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case2/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case2/THET")
    THET = loadtxt(FileNameAndPath)

    SFLOW, FLOW = flo(LP, BLP, THET)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case2/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case2/SFLOW")
    SFLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_true, decimal=4)

    # --------------- case 3 --------------
    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case3/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case3/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case3/THET")
    THET = loadtxt(FileNameAndPath)

    SFLOW, FLOW = flo(LP, BLP, THET)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case3/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case3/SFLOW")
    SFLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_true, decimal=4)

    # --------------- case 4 --------------
    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case4/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case4/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case4/THET")
    THET = loadtxt(FileNameAndPath)

    SFLOW, FLOW = flo(LP, BLP, THET)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case4/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case4/SFLOW")
    SFLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_true, decimal=4)

    # --------------- case 5 --------------
    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case5/LP")
    LP = loadtxt(FileNameAndPath).astype(int)
    LP -= 1  # 0-based index in python!

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case5/BLP")
    BLP = loadtxt(FileNameAndPath)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case5/THET")
    THET = loadtxt(FileNameAndPath)

    SFLOW, FLOW = flo(LP, BLP, THET)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case5/FLOW")
    FLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(FLOW, FLOW_true, decimal=4)

    FileNameAndPath = Path(TEST_DIR, "testdata_flo/case5/SFLOW")
    SFLOW_true = loadtxt(FileNameAndPath)
    np.testing.assert_array_almost_equal(SFLOW, SFLOW_true, decimal=4)
