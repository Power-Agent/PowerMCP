from pathlib import Path

import numpy as np

from reliabilityassessment.data_processing.readInputB import readInputB


def test_readInputB():
    TEST_DIR = str(Path(__file__).parent.absolute())
    inputB_dict = readInputB(TEST_DIR)

    # assertion for values in ZZMC data card
    assert inputB_dict["ZZMC"]["JSEED"] == 345237
    assert inputB_dict["ZZMC"]["NLS"] == 1
    assert inputB_dict["ZZMC"]["IW1"] == 13
    assert inputB_dict["ZZMC"]["IW2"] == 26
    assert inputB_dict["ZZMC"]["IW3"] == 39
    assert inputB_dict["ZZMC"]["KWHERE"] == 1
    assert inputB_dict["ZZMC"]["KVWHEN"] == 1
    assert inputB_dict["ZZMC"]["KVSTAT"] == 1
    assert inputB_dict["ZZMC"]["KVTYPE"] == 2
    assert inputB_dict["ZZMC"]["KVLOC"] == 1
    assert inputB_dict["ZZMC"]["CVTEST"] == 0.025
    assert inputB_dict["ZZMC"]["FINISH"] == 9999
    assert inputB_dict["ZZMC"]["JSTEP"] == 1
    assert inputB_dict["ZZMC"]["JFREQ"] == 1
    assert inputB_dict["ZZMC"]["MAXEUE"] == 1000
    assert inputB_dict["ZZMC"]["IOI"] == 0
    assert inputB_dict["ZZMC"]["IOJ"] == 0
    assert inputB_dict["ZZMC"]["IREM"] == 1
    assert inputB_dict["ZZMC"]["INTV"] == 5
    assert inputB_dict["ZZMC"]["IREPD"] == 1
    assert inputB_dict["ZZMC"]["IREPM"] == 1

    # assertion for values in ZZLD data card
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["SNRI"], [1, 2])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["NAR"], ["'A1'", "'A2'"])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["RATES"][:, 0], [3000, 3000])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["RATES"][:, 1], [0.0, 0.0])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["RATES"][:, 2], [30000, 30000])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["ID"][:, 0], [1, 1])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["ID"][:, 1], [52, 52])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["ID"][:, 2], [31, 31])
    np.testing.assert_array_equal(inputB_dict["ZZLD"]["ID"][:, 3], [32, 32])

    # assertion for values in ZZUD data card
    np.testing.assert_array_equal(inputB_dict["ZZUD"]["SNRI"], [1, 2])
    np.testing.assert_array_equal(inputB_dict["ZZUD"]["NAT"], ["'A10101'", "'A20101'"])
    np.testing.assert_array_equal(inputB_dict["ZZUD"]["NAR"], ["'A1'", "'A2'"])
    np.testing.assert_array_equal(
        inputB_dict["ZZUD"]["HRLOAD"][:, 0], [12.0, 12.0, 12.0, 12.0, 0.0, 0.02, 0.0]
    )
    np.testing.assert_array_equal(
        inputB_dict["ZZUD"]["HRLOAD"][:, 1], [12.0, 12.0, 12.0, 12.0, 0.0, 0.02, 0.0]
    )
    np.testing.assert_array_equal(
        inputB_dict["ZZUD"]["ID"][0, :], [0.0, 0.0, 0.0, 0.0, 0.0]
    )
    np.testing.assert_array_equal(
        inputB_dict["ZZUD"]["ID"][1, :], [0.0, 0.0, 0.0, 0.0, 0.0]
    )

    # assertion for values in ZZTD data card
    np.testing.assert_array_equal(inputB_dict["ZZTD"]["SNRI"], [1])
    np.testing.assert_array_equal(inputB_dict["ZZTD"]["LineID"], [1])
    np.testing.assert_array_equal(inputB_dict["ZZTD"]["NAR"][0], ["'A1'"])
    np.testing.assert_array_equal(inputB_dict["ZZTD"]["NAE"][0], ["'A2'"])
    np.testing.assert_array_equal(
        inputB_dict["ZZTD"]["ADM"][0, :], [-120.0, -60.0, 0.0, -80.0, -40.0, -20.0]
    )
    np.testing.assert_array_equal(
        inputB_dict["ZZTD"]["CAP"][0, :], [300.0, 150.0, 0.0, 150.0, 100.0, 50.0]
    )
    np.testing.assert_array_equal(
        inputB_dict["ZZTD"]["CAPR"][0, :], [300.0, 150.0, 0.0, 150.0, 100.0, 50.0]
    )
    np.testing.assert_array_equal(
        inputB_dict["ZZTD"]["PROBT"][0, :], [0.9216, 0.0768, 0.0016, 0.0, 0.0, 0.0]
    )
