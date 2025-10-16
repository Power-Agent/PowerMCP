import numpy as np

from reliabilityassessment.data_processing.wpeakf import _wpeakf, wpeakf


def test_wpeakf():
    x = np.linspace(1.0, 0.1, 7)
    # array([1.  , 0.85, 0.7 , 0.55, 0.4 , 0.25, 0.1 ])
    y = np.flip(x)
    # array([0.1 , 0.25, 0.4 , 0.55, 0.7 , 0.85, 1.  ])
    x1 = np.hstack((np.tile(x, 52), 101.0))
    y1 = np.hstack((np.tile(y, 52), 101.0))
    DYLOAD = np.vstack((x1, y1))

    WPEAK_truth_1 = np.hstack((np.ones(51) * 1.0, 101.0))
    WPEAK_truth_2 = np.hstack((np.ones(51) * 1.0, 101.0))
    WPEAK_truth = np.vstack((WPEAK_truth_1, WPEAK_truth_2))

    _WPEAK = _wpeakf(DYLOAD)  # vanilla verison
    np.testing.assert_array_equal(_WPEAK, WPEAK_truth)

    WPEAK = wpeakf(DYLOAD)  # vectorized version
    np.testing.assert_array_equal(WPEAK, WPEAK_truth)
