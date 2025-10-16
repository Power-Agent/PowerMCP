import numpy as np

from reliabilityassessment.monte_carlo.admitb import admitb


def test_admitb():
    LP = np.array([[0, 0, 1], [1, 1, 2], [2, 2, 0]], dtype=int)
    BLP = np.array([[-120, 300, 300], [-60, 150, 150], [-80, 100, 100]])
    BB_ = np.array([[-200.0, 120, 80], [120, -180, 60], [80, 60, -140]])
    BB = admitb(LP, BLP)
    np.testing.assert_array_almost_equal(BB, BB_)
