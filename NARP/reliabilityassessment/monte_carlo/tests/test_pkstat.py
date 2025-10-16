import numpy as np

from reliabilityassessment.monte_carlo.pkstat import _pkstat, pkstat


def test_pkstat():
    np.random.seed(1)

    NST = 1
    MARGIN = np.array([60, -70, 80])
    NOAREA = len(MARGIN)
    LOLTPP = np.random.randint(0, 100, (5,))
    LOLGPP = np.random.randint(0, 100, (5,))
    LOLTPA = np.random.randint(0, 100, (NOAREA, 5))
    MGNTPA = 200 * np.random.rand(NOAREA, 5)
    MGNTPP = 600 * np.random.rand(
        5,
    )
    LOLGPA = np.random.randint(0, 100, (NOAREA, 5))
    MGNGPA = 1000 * np.random.rand(NOAREA, 5)
    MGNGPP = 3000 * np.random.rand(5)

    _pkstat(NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP)

    LOLTPP_true = np.array([37, 13, 72, 9, 75])
    np.testing.assert_array_almost_equal(LOLTPP, LOLTPP_true)

    LOLGPP_true = np.array([5, 79, 64, 16, 1])
    np.testing.assert_array_almost_equal(LOLGPP, LOLGPP_true)

    LOLTPA_true = np.array(
        [[76, 71, 6, 25, 50], [20, 18 + 1, 84, 11, 28], [29, 14, 50, 68, 87]]
    )
    np.testing.assert_array_almost_equal(LOLTPA, LOLTPA_true)

    MGNTPA_true = np.array(
        [
            [91.4409616, 86.13971344, 187.82555788, 155.67784727, 143.19410319],
            [
                160.55150079,
                18.56016173 - int(MARGIN[1]),
                103.63050979,
                173.0040504,
                165.82938147,
            ],
            [165.92067188, 54.60999484, 11.84864026, 134.10560801, 118.61310366],
        ]
    )
    np.testing.assert_array_almost_equal(MGNTPA, MGNTPA_true)

    MGNTPP_true = np.array(
        [
            402.99245845,
            247.07272738 - int(MARGIN[1]),
            118.53053879,
            173.77778433,
            85.27208128,
        ]
    )
    np.testing.assert_array_almost_equal(MGNTPP, MGNTPP_true)

    LOLGPA_true = np.array(
        [[26, 52, 80, 41, 82], [15, 64, 68, 25, 98], [87, 7, 26, 25, 22]]
    )
    np.testing.assert_array_almost_equal(LOLGPA, LOLGPA_true)

    MGNGPA_true = np.array(
        [
            [908.59550309, 293.61414837, 287.77533859, 130.02857212, 19.36695787],
            [678.83553294, 211.628116, 265.54665937, 491.57315928, 53.36254512],
            [574.11760549, 146.72857491, 589.3055369, 699.75836002, 102.33442883],
        ]
    )
    np.testing.assert_array_almost_equal(MGNGPA, MGNGPA_true)

    MGNGPP_true = np.array(
        [1242.16796346, 2083.20047318, 1242.53780858, 149.86037684, 1607.68921775]
    )
    np.testing.assert_array_almost_equal(MGNGPP, MGNGPP_true)

    # -------------------------------------------------------------------------
    # test for the vectorized version
    np.random.seed(1)

    NST = 1
    MARGIN = np.array([60, -70, 80])
    NOAREA = len(MARGIN)
    LOLTPP = np.random.randint(0, 100, (5,))
    LOLGPP = np.random.randint(0, 100, (5,))
    LOLTPA = np.random.randint(0, 100, (NOAREA, 5))
    MGNTPA = 200 * np.random.rand(NOAREA, 5)
    MGNTPP = 600 * np.random.rand(
        5,
    )
    LOLGPA = np.random.randint(0, 100, (NOAREA, 5))
    MGNGPA = 1000 * np.random.rand(NOAREA, 5)
    MGNGPP = 3000 * np.random.rand(5)

    pkstat(NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP)

    LOLTPP_true = np.array([37, 13, 72, 9, 75])
    np.testing.assert_array_almost_equal(LOLTPP, LOLTPP_true)

    LOLGPP_true = np.array([5, 79, 64, 16, 1])
    np.testing.assert_array_almost_equal(LOLGPP, LOLGPP_true)

    LOLTPA_true = np.array(
        [[76, 71, 6, 25, 50], [20, 18 + 1, 84, 11, 28], [29, 14, 50, 68, 87]]
    )
    np.testing.assert_array_almost_equal(LOLTPA, LOLTPA_true)

    MGNTPA_true = np.array(
        [
            [91.4409616, 86.13971344, 187.82555788, 155.67784727, 143.19410319],
            [
                160.55150079,
                18.56016173 - int(MARGIN[1]),
                103.63050979,
                173.0040504,
                165.82938147,
            ],
            [165.92067188, 54.60999484, 11.84864026, 134.10560801, 118.61310366],
        ]
    )
    np.testing.assert_array_almost_equal(MGNTPA, MGNTPA_true)

    MGNTPP_true = np.array(
        [
            402.99245845,
            247.07272738 - int(MARGIN[1]),
            118.53053879,
            173.77778433,
            85.27208128,
        ]
    )
    np.testing.assert_array_almost_equal(MGNTPP, MGNTPP_true)

    LOLGPA_true = np.array(
        [[26, 52, 80, 41, 82], [15, 64, 68, 25, 98], [87, 7, 26, 25, 22]]
    )
    np.testing.assert_array_almost_equal(LOLGPA, LOLGPA_true)

    MGNGPA_true = np.array(
        [
            [908.59550309, 293.61414837, 287.77533859, 130.02857212, 19.36695787],
            [678.83553294, 211.628116, 265.54665937, 491.57315928, 53.36254512],
            [574.11760549, 146.72857491, 589.3055369, 699.75836002, 102.33442883],
        ]
    )
    np.testing.assert_array_almost_equal(MGNGPA, MGNGPA_true)

    MGNGPP_true = np.array(
        [1242.16796346, 2083.20047318, 1242.53780858, 149.86037684, 1607.68921775]
    )
    np.testing.assert_array_almost_equal(MGNGPP, MGNGPP_true)
