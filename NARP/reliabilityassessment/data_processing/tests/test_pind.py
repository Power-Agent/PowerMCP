from pathlib import Path

import numpy as np

from reliabilityassessment.data_processing.pind import pind
from reliabilityassessment.data_processing.readInputB import readInputB


def test_pind():
    TEST_DIR = str(Path(__file__).parent.absolute())
    inputB_dict = readInputB(TEST_DIR)

    inputB_dict_nameToInt = pind(inputB_dict)

    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZLD"]["NAR"], np.array([0, 1])
    )

    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZUD"]["NAT"], np.array([0, 1])
    )
    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZUD"]["NAR"], np.array([0, 1])
    )

    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZTD"]["LineID"], np.array([0], dtype=int)
    )
    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZTD"]["NAR"], np.array([0], dtype=int)
    )
    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZTD"]["NAE"], np.array([1], dtype=int)
    )

    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZFC"]["NAR"], np.array([], dtype=int)
    )
    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZFC"]["NAE"], np.array([], dtype=int)
    )

    np.testing.assert_array_equal(
        inputB_dict_nameToInt["ZZOD"]["NAT"], np.array([], dtype=int)
    )
