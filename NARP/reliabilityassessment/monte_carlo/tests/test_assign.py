import numpy as np

from reliabilityassessment.monte_carlo.assign import assign


def test_assign():
    # --------------- test case-1 -----------
    NN, NLS = 5, 1

    INJ = np.zeros(20)
    LOD = np.zeros(20)

    LT = np.zeros(20, dtype=int)
    LT[:5] = [2, 3, 4, 5, 1]
    LT[:5] -= 1  # be careful: 0-based index in Python

    INJ1, LODC = assign(INJ, LOD, LT, NN, NLS)

    INJ1_true = np.zeros(5)

    np.testing.assert_array_almost_equal(INJ1, INJ1_true)

    LODC_true = np.zeros(5)

    np.testing.assert_array_almost_equal(LODC, LODC_true)

    # --------------- test case-2 -----------
    NN, NLS = 5, 1

    INJ = np.zeros(20)
    INJ[:NN] = [-162.00, 814.00, 414.00, 314.00, 432.00]

    LOD = np.zeros(20)
    LOD[:NN] = [2591.00, 2591.00, 2591.00, 2591.00, 2591.00]

    LT = np.zeros(20, dtype=int)
    LT[:5] = [2, 3, 4, 5, 1]
    LT[:5] -= 1  # be careful: 0-based index in Python

    INJ1, LODC = assign(INJ, LOD, LT, NN, NLS)

    INJ1_true = np.array([-162.000000, 66.802429, 33.975685, 25.768997, 35.452888])

    np.testing.assert_array_almost_equal(INJ1, INJ1_true, decimal=5)

    LODC_true = np.zeros(5)

    np.testing.assert_array_almost_equal(LODC, LODC_true, decimal=5)

    # --------------- test case-3 -----------
    NN, NLS = 5, 1

    INJ = np.zeros(20)
    INJ[:NN] = [620.00, -40.000000, 668.00, 495.000000, 845.00]

    LOD = np.zeros(20)
    LOD[:NN] = [2540.00, 2540.00, 2540.00, 2540.00, 2540.00]

    LT = np.zeros(20, dtype=int)
    LT[:5] = [2, 3, 4, 5, 1]
    LT[:5] -= 1  # be careful: 0-based index in Python

    INJ1, LODC = assign(INJ, LOD, LT, NN, NLS)

    INJ1_true = np.array(
        [
            9.436834,
            -40.000000,
            10.167428,
            7.534246,
            12.861491,
        ]
    )

    np.testing.assert_array_almost_equal(INJ1, INJ1_true, decimal=5)

    LODC_true = np.zeros(5)

    np.testing.assert_array_almost_equal(LODC, LODC_true, decimal=5)
