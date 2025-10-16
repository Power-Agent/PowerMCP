from pathlib import Path

import numpy as np


def test_integration_result_comparison():
    TEST_DIR = Path(__file__).parent.absolute()

    # from reliabilityassessment.monte_carlo.narpMain import narpMain
    # run "narpMain(TEST_DIR)" externally. Then move the output file
    # to this folder (if needed) and rename it as "output_python.txt".
    # read Python output
    python_result_path = Path(TEST_DIR, "output_python.txt")
    f1 = open(python_result_path, "r")

    lole_obs, lole_prob = np.zeros((22, 5)), np.zeros((22, 5))
    hlole_obs, hlole_prob = np.zeros((22, 5)), np.zeros((22, 5))
    eue_obs, eue_prob = np.zeros((22, 5)), np.zeros((22, 5))

    cnt = 1
    k = 0
    while k < 5:
        s = f1.readline()
        while "PROBABILITY DISTRIBUTIONS FOR AREA" not in s.strip():
            s = f1.readline()
            cnt += 1
        while "NUMBER" not in s:
            s = f1.readline()
            cnt += 1
        for i in range(22):
            s = f1.readline().strip().split()
            cnt += 1
            lole_obs[i][k], lole_prob[i][k] = s[1:3]
            hlole_obs[i][k], hlole_prob[i][k] = s[3:5]
            eue_obs[i][k], eue_prob[i][k] = s[6:8]
        k += 1
    f1.close()

    # run "NARP.exe" externally. Then move the output file
    # to this folder (if needed) and rename it as "OUTPUT_fortran".
    # read Fortran output
    fortran_result_path = Path(TEST_DIR, "OUTPUT_fortran")
    f2 = open(fortran_result_path, "r")

    LOLE_OBS, LOLE_PROB = np.zeros((22, 5)), np.zeros((22, 5))
    HLOLE_OBS, HLOLE_PROB = np.zeros((22, 5)), np.zeros((22, 5))
    EUE_OBS, EUE_PROB = np.zeros((22, 5)), np.zeros((22, 5))

    cnt = 1
    k = 0
    while k < 5:
        s = f2.readline()
        while "PROBABILITY DISTRIBUTIONS FOR AREA" not in s.strip():
            s = f2.readline()
            cnt += 1
        while "NUMBER" not in s:
            s = f2.readline()
            cnt += 1
        f2.readline()
        for i in range(22):
            s = f2.readline().strip().split()
            cnt += 1
            LOLE_OBS[i][k], LOLE_PROB[i][k] = s[1:3]
            HLOLE_OBS[i][k], HLOLE_PROB[i][k] = s[3:5]
            EUE_OBS[i][k], EUE_PROB[i][k] = s[6:8]
        k += 1
    f2.close()

    # Compare the values of the probability (PDF) tables :
    sum_LOLE_prob = 0
    sum_HLOLE_prob = 0
    sum_EUE_prob = 0
    for k in range(5):
        sum_LOLE_prob += np.linalg.norm(LOLE_PROB[:, k] - lole_prob[:, k])
        sum_HLOLE_prob += np.linalg.norm(HLOLE_PROB[:, k] - hlole_prob[:, k])
        sum_EUE_prob += np.linalg.norm(EUE_PROB[:, k] - eue_prob[:, k])
    rmse_LOLE_prob = sum_LOLE_prob / 5
    rmse_HLOLE_prob = sum_HLOLE_prob / 5
    rmse_EUE_prob = sum_EUE_prob / 5
    print(rmse_LOLE_prob)
    print(rmse_HLOLE_prob)
    print(rmse_EUE_prob)
    assert rmse_LOLE_prob < 0.1
    assert rmse_HLOLE_prob < 0.1
    assert rmse_EUE_prob < 0.1
