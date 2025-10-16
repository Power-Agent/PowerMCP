import numpy as np

from reliabilityassessment.data_processing.smaint import smaint


def pmsc_mock(
    areaIdx,
    ID,
    ITAB,
    RATES,
    PROBG,
    DERATE,
    PKLOAD,
    WPEAK,
    IREPM,
    MINRAN,
    MAXRAN,
    INHBT1,
    INHBT2,
    NAMU,
    NUMP,
):
    ID[:] = np.array([[1, 1, 1, 0, 3, 0, 0, 0], [0, 0, 0, 1, 4, 0, 0, 0]], dtype=int)
    ITAB = 1
    return ITAB


def test_smaint(mocker):
    mocker.patch(
        "reliabilityassessment.data_processing.smaint.pmsc", side_effect=pmsc_mock
    )

    NOAREA = 2
    ID = np.zeros((2, 8), dtype=int)
    NUNITS = ID.shape[0]

    ITAB = 0
    RATES = np.array([[12.0, 12.0, 12.0, 12.0], [12.0, 12.0, 12.0, 12.0]])
    PROBG = np.array([[0.98, 0.98], [0.98, 0.98]])
    DERATE = np.array([1.0, 1.0])
    PKLOAD = np.array([3000.0, 3000.0])
    WPEAK_1 = np.hstack((np.ones(51) * 1.0, 101.0))
    WPEAK_2 = np.hstack((np.ones(51) * 1.0, 101.0))
    WPEAK = np.vstack((WPEAK_1, WPEAK_2))
    IREPM = 1
    MINRAN, MAXRAN = np.array([1, 1], dtype=int), np.array([52, 52], dtype=int)
    INHBT1, INHBT2 = np.array([31, 31], dtype=int), np.array([32, 32], dtype=int)
    NAMU = ["A101", "A201"]
    NUMP = ["01", "01"]

    JPLOUT, ITAB = smaint(
        NOAREA,
        ID,
        ITAB,
        RATES,
        PROBG,
        DERATE,
        PKLOAD,
        WPEAK,
        IREPM,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        NAMU,
        NUMP,
    )

    JPLOUT_true = (-1) * np.ones((52, 1 + NUNITS), dtype=int)
    JPLOUT_true[:, 0] = 0
    JPLOUT_true[:5, 0] = [1, 2, 2, 1, 1]
    JPLOUT_true[:5, 1] = [1, 1, 1, 0, 0]
    JPLOUT_true[1:3, 2] = 0
    ITAB_true = 1

    assert ITAB == ITAB_true
    np.testing.assert_almost_equal(JPLOUT_true, JPLOUT)
