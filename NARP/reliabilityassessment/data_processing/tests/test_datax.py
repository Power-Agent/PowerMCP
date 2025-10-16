from pathlib import Path

import numpy as np

from reliabilityassessment.data_processing.datax import datax
from reliabilityassessment.data_processing.pind import pind
from reliabilityassessment.data_processing.readInputB import readInputB


def test_datax():
    TEST_DIR = str(Path(__file__).parent.absolute())
    inputB_dict = readInputB(TEST_DIR)
    inputB_dict_nameToInt = pind(inputB_dict)

    (
        QTR,
        NORR,
        NFCST,
        NOAREA,
        PKLOAD,
        FU,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        BN,
        SUSTAT,
        FCTERR,
        CAPCON,
        CAPOWN,
        NOGEN,
        PROBG,
        DERATE,
        JENT,
        INTCH,
        INTCHR,
        LP,
        LINENO,
        PROBL,
        BLPA,
        MXCRIT,
        JCRIT,
        ID,
        NLS,
        IOI,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        CVTEST,
        MAXEUE,
        JSTEP,
        JFREQ,
        FINISH,
        INTV,
        INTVT,
    ) = datax(inputB_dict_nameToInt)

    QTR_ = np.array([13 * 168 + 0.5, 26 * 168 + 0.5, 39 * 168 + 0.5])
    np.testing.assert_array_equal(QTR_, QTR)

    NORR_ = 1 - 1  # 0-based index in Python
    assert NORR_ == NORR
    NFCST_ = 1
    assert NFCST_ == NFCST
    NOAREA_ = 2
    assert NOAREA_ == NOAREA

    PKLOAD_ = np.array([3000.0, 3000.0])
    np.testing.assert_array_equal(PKLOAD_, PKLOAD)

    FU_ = np.array([0.0, 0.0])
    np.testing.assert_array_equal(FU_, FU)

    MINRAN_ = -1 + np.array([1, 1], dtype=int)  # 0-based inbdex in Python!
    np.testing.assert_array_equal(MINRAN_, MINRAN)
    MAXRAN_ = -1 + np.array([52, 52], dtype=int)  # 0-based inbdex in Python!
    np.testing.assert_array_equal(MAXRAN_, MAXRAN)

    INHBT1_ = -1 + np.array([31, 31], dtype=int)  # 0-based inbdex in Python!
    np.testing.assert_array_equal(INHBT1_, INHBT1)
    INHBT2_ = -1 + np.array([32, 32], dtype=int)  # 0-based inbdex in Python!
    np.testing.assert_array_equal(INHBT2_, INHBT2)

    BN_ = np.array([[0, 0, 0, 30000.0, 30000.0], [1, 0, 0, 30000.0, 30000.0]])
    np.testing.assert_array_equal(BN_, BN)

    SUSTAT_ = np.array(
        [[3000.0, 0, 0, 0, 0, 0], [3000.0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]
    )
    np.testing.assert_array_equal(SUSTAT_, SUSTAT)

    FCTERR_ = np.array([[1.0, 1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0, 1.0]])
    np.testing.assert_array_equal(FCTERR_, FCTERR)

    CAPCON_ = np.array([0, 1], dtype=int)
    np.testing.assert_array_equal(CAPCON_, CAPCON)

    CAPOWN_ = np.array([[1, 0], [0, 1]])
    np.testing.assert_array_equal(CAPOWN_, CAPOWN)

    NOGEN_ = np.array([1, 1], dtype=int)
    np.testing.assert_array_equal(NOGEN_, NOGEN)

    PROBG_ = np.array([[0.98, 0.98], [0.98, 0.98]])
    np.testing.assert_array_equal(PROBG_, PROBG)

    DERATE_ = np.array([1.0, 1.0])
    np.testing.assert_array_equal(DERATE_, DERATE)

    JENT_ = np.array([[-1, -1], [-1, -1]], dtype=int)
    np.testing.assert_array_equal(JENT_, JENT)

    INTCH_ = np.zeros((60, 365))  # 60 is the maium posobel conut of fixed contracts
    np.testing.assert_array_equal(INTCH_, INTCH)

    INTCHR_ = np.zeros((60, 2))  # 60 is the maium posobel conut of fixed contracts
    np.testing.assert_array_equal(INTCHR_, INTCHR)

    LP_ = np.array([[0, 0, 1]], dtype=int)
    np.testing.assert_array_equal(LP_, LP)

    LINENO_ = np.array([[-1, 0], [-1, -1]], dtype=int)
    np.testing.assert_array_equal(LINENO_, LINENO)

    PROBL_ = np.array([[0.9216], [0.9984], [1.0], [1.0], [1.0], [1.0]])
    np.testing.assert_array_equal(PROBL_, PROBL)

    BLPA_ = np.array(
        [
            [
                -120.0,
                300.0,
                300.0,
                -60.0,
                150.0,
                150.0,
                -0.5,
                1.0,
                1.0,
                -80.0,
                150.0,
                150.0,
                -40.0,
                100.0,
                100.0,
                -20.0,
                50.0,
                50.0,
            ]
        ]
    )
    np.testing.assert_array_equal(BLPA_, BLPA)

    MXCRIT_ = 0
    assert MXCRIT_ == MXCRIT

    JCRIT_ = []
    np.testing.assert_array_equal(JCRIT_, JCRIT)

    ID_ = np.array([[0, 0, 0, -1, 0, -1, 0, 0], [1, 1, 1, -1, 0, -1, 0, 0]], dtype=int)
    np.testing.assert_array_equal(ID_, ID)

    assert NLS == 1
    assert IOI == 0
    assert IOJ == 0
    assert KVLOC == 1 - 1  # 0-based index in Python;
    assert KVSTAT == 1
    assert KVTYPE == 2
    assert KVWHEN == 1
    assert KWHERE == 1
    assert CVTEST == 0.025
    assert MAXEUE == 1000
    assert JSTEP == 1
    assert JFREQ == 1
    assert FINISH == 9999 * 8760.0
    assert INTV == 5
    assert INTVT == 5
