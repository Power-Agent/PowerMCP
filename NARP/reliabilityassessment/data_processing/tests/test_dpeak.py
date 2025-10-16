import numpy as np

from reliabilityassessment.data_processing.dpeak import _dpeak, dpeak


def test_dpeak():
    # vanilla version
    HRLOAD = np.array(
        [
            [1.5, 2.5, 3.5, 3.6, 2.6, 1.6],
            [4.5, 5.5, 6.5, 6.6, 5.6, 4.6],
            [7.5, 8.5, 9.5, 9.6, 8.6, 7.6],
            [10.5, 11.5, 12.5, 12.6, 11.6, 10.6],
        ]
    )

    MAXHR, DYLOAD, MAXDAY = _dpeak(HRLOAD, hour_within_day=3)
    np.testing.assert_array_equal(
        MAXHR, np.array([[2, 3], [2, 3], [2, 3], [2, 3]], dtype=int)
    )
    np.testing.assert_array_equal(
        DYLOAD, np.array([[3.5, 3.6], [6.5, 6.6], [9.5, 9.6], [12.5, 12.6]])
    )
    np.testing.assert_array_equal(MAXDAY, np.array([1, 1, 1, 1], dtype=int))

    # vectorized version
    # Note: the dummy input 'hour_within_day' is set for unit test purpose;
    # in real data, it always equals to 24
    MAXHR, DYLOAD, MAXDAY = dpeak(HRLOAD, hour_within_day=3)
    np.testing.assert_array_equal(
        MAXHR, np.array([[2, 3], [2, 3], [2, 3], [2, 3]], dtype=int)
    )
    np.testing.assert_array_equal(
        DYLOAD, np.array([[3.5, 3.6], [6.5, 6.6], [9.5, 9.6], [12.5, 12.6]])
    )
    np.testing.assert_array_equal(MAXDAY, np.array([1, 1, 1, 1], dtype=int))
