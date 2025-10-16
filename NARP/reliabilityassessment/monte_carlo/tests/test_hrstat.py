import numpy as np

from reliabilityassessment.monte_carlo.hrstat import _hrstat, hrstat


def test_hrstat():
    np.random.seed(1)

    NST = 1
    MARGIN = np.array([60, -70, 80])
    NOAREA = len(MARGIN)
    LOLTHP = np.random.randint(0, 100, (5,))
    LOLGHP = np.random.randint(0, 100, (5,))
    LOLTHA = np.random.randint(0, 100, (NOAREA, 5))
    MGNTHA = 200 * np.random.rand(NOAREA, 5)
    MGNTHP = 600 * np.random.rand(
        5,
    )

    LOLGHA = np.random.randint(0, 100, (NOAREA, 5))
    MGNGHA = 1000 * np.random.rand(NOAREA, 5)
    MGNGHP = 3000 * np.random.rand(5)

    LSFLG = np.random.randint(0, 100, (NOAREA,))

    _hrstat(
        NST,
        MARGIN,
        LSFLG,
        LOLGHA,
        LOLGHP,
        LOLTHA,
        LOLTHP,
        MGNGHA,
        MGNGHP,
        MGNTHA,
        MGNTHP,
    )

    LSFLG_true = np.array([52, 86, 70], dtype=int)
    np.testing.assert_array_equal(LSFLG, LSFLG_true)

    LOLTHP_true = np.array([37, 13, 72, 9, 75])
    np.testing.assert_array_almost_equal(LOLTHP, LOLTHP_true)

    LOLGHP_true = np.array([5, 79, 64, 16, 1])
    np.testing.assert_array_almost_equal(LOLGHP, LOLGHP_true)

    LOLTHA_true = np.array(
        [[76, 71, 6, 25, 50], [20, 18 + 1, 84, 11, 28], [29, 14, 50, 68, 87]]
    )
    np.testing.assert_array_almost_equal(LOLTHA, LOLTHA_true)

    MGNTHA_true = np.array(
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
    np.testing.assert_array_almost_equal(MGNTHA, MGNTHA_true)

    MGNTHP_true = np.array(
        [
            402.99245845,
            247.07272738 - int(MARGIN[1]),
            118.53053879,
            173.77778433,
            85.27208128,
        ]
    )
    np.testing.assert_array_almost_equal(MGNTHP, MGNTHP_true)

    LOLGHA_true = np.array(
        [[26, 52, 80, 41, 82], [15, 64, 68, 25, 98], [87, 7, 26, 25, 22]]
    )
    np.testing.assert_array_almost_equal(LOLGHA, LOLGHA_true)

    MGNGHA_true = np.array(
        [
            [908.59550309, 293.61414837, 287.77533859, 130.02857212, 19.36695787],
            [678.83553294, 211.628116, 265.54665937, 491.57315928, 53.36254512],
            [574.11760549, 146.72857491, 589.3055369, 699.75836002, 102.33442883],
        ]
    )
    np.testing.assert_array_almost_equal(MGNGHA, MGNGHA_true)

    MGNGHP_true = np.array(
        [1242.16796346, 2083.20047318, 1242.53780858, 149.86037684, 1607.68921775]
    )
    np.testing.assert_array_almost_equal(MGNGHP, MGNGHP_true)

    # ----------------------------------------------------------------
    # test for the vectorized version
    np.random.seed(1)

    NST = 1
    MARGIN = np.array([60, -70, 80])
    NOAREA = len(MARGIN)
    LOLTHP = np.random.randint(0, 100, (5,))
    LOLGHP = np.random.randint(0, 100, (5,))
    LOLTHA = np.random.randint(0, 100, (NOAREA, 5))
    MGNTHA = 200 * np.random.rand(NOAREA, 5)
    MGNTHP = 600 * np.random.rand(
        5,
    )

    LOLGHA = np.random.randint(0, 100, (NOAREA, 5))
    MGNGHA = 1000 * np.random.rand(NOAREA, 5)
    MGNGHP = 3000 * np.random.rand(5)

    LSFLG = np.random.randint(0, 100, (NOAREA,))

    hrstat(
        NST,
        MARGIN,
        LSFLG,
        LOLGHA,
        LOLGHP,
        LOLTHA,
        LOLTHP,
        MGNGHA,
        MGNGHP,
        MGNTHA,
        MGNTHP,
    )

    LSFLG_true = np.array([52, 86, 70], dtype=int)
    np.testing.assert_array_equal(LSFLG, LSFLG_true)

    LOLTHP_true = np.array([37, 13, 72, 9, 75])
    np.testing.assert_array_almost_equal(LOLTHP, LOLTHP_true)

    LOLGHP_true = np.array([5, 79, 64, 16, 1])
    np.testing.assert_array_almost_equal(LOLGHP, LOLGHP_true)

    LOLTHA_true = np.array(
        [[76, 71, 6, 25, 50], [20, 18 + 1, 84, 11, 28], [29, 14, 50, 68, 87]]
    )
    np.testing.assert_array_almost_equal(LOLTHA, LOLTHA_true)

    MGNTHA_true = np.array(
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
    np.testing.assert_array_almost_equal(MGNTHA, MGNTHA_true)

    MGNTHP_true = np.array(
        [
            402.99245845,
            247.07272738 - int(MARGIN[1]),
            118.53053879,
            173.77778433,
            85.27208128,
        ]
    )
    np.testing.assert_array_almost_equal(MGNTHP, MGNTHP_true)

    LOLGHA_true = np.array(
        [[26, 52, 80, 41, 82], [15, 64, 68, 25, 98], [87, 7, 26, 25, 22]]
    )
    np.testing.assert_array_almost_equal(LOLGHA, LOLGHA_true)

    MGNGHA_true = np.array(
        [
            [908.59550309, 293.61414837, 287.77533859, 130.02857212, 19.36695787],
            [678.83553294, 211.628116, 265.54665937, 491.57315928, 53.36254512],
            [574.11760549, 146.72857491, 589.3055369, 699.75836002, 102.33442883],
        ]
    )
    np.testing.assert_array_almost_equal(MGNGHA, MGNGHA_true)

    MGNGHP_true = np.array(
        [1242.16796346, 2083.20047318, 1242.53780858, 149.86037684, 1607.68921775]
    )
    np.testing.assert_array_almost_equal(MGNGHP, MGNGHP_true)
