import numpy as np

from reliabilityassessment.data_processing.gsm import gsm


def test_gsm():
    N = 1
    KT = 10
    KP = 0
    P1 = 0.98
    P2 = 0.0
    P3 = 2e-2
    KA = np.zeros(5000, dtype=int)
    PA = np.zeros(5000)
    PA[0] = 1.0

    N_true = 2
    PA_true = np.zeros(5000)
    PA_true[:2] = [1.0, 0.02]
    KA_true = np.zeros(5000, dtype=int)
    KA_true[1] = 10

    N = gsm(N, KT, KP, P1, P2, P3, PA, KA)

    assert N == N_true
    np.testing.assert_array_almost_equal(PA, PA_true)
    np.testing.assert_array_almost_equal(KA, KA_true)
