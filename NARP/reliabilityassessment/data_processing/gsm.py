import numpy as np


def gsm(N, KT, KP, P1, P2, P3, PA, KA):
    """
    Add a 2-state or a 3-state unit model to the generation capacity-outage model
    based on the "unit addition algorithm".

    Its high-level idea and illustration can be partially found in these slides:
    https://www.dropbox.com/s/krcse3mjuh97i88/module_6-1.pdf?dl=0

    :param int N: total number of starting states
    :param int KT: rounded (nearest integer) full capacity of the added gen unit
    :param int KP: rounded (nearest integer) derated capacity of the added gen unit
    :param float P1: exact prob. of the I-th gen unit at its full capacity
    :param float P2: exact prob. of the I-th gen unit at its derated capacity
    :param float P3: exact prob. of the I-th gen unit in total loss (i.e. zero MW)
    :param numpy.ndarray PA: CUT OFF probability in the CAP outage table
    :param numpy.ndarray KA: CUT OFF capacity in the CAP outage table
    :return: (*int*) -- updated total number of states

    .. note:: KA and PA are modified in-place
    .. todo:: Check the physical meaning of input parameter N and update doc strings
    """
    INGS = 5000
    INGS1 = INGS - 50

    # Create outage states after unit addition
    KO = np.zeros((5000, 3), dtype=int)  # for local use only

    KO[:, 0] = KA
    KO[:, 1] = KA + KP
    KO[:, 2] = KA + KT
    P = PA.copy()

    # Possibly, N,NN,NNN represents certain counts of some states,
    # rather than the array "index"
    # NN = N + 1 # NN and NNN may have physical meanings
    # NNN = NN + 1
    KO[N : N + 2, :] = 10**6
    P[N : N + 2] = 0.0

    # Select outage states in ascending order of magnitude and
    # calculate their probabilities and frequencies
    L = 0  # 1 in original Fortran
    KA[0] = 0
    PA[0] = 1.0
    J = np.array([1, KP == 0, 0])
    while J.min() < N and PA[L] > 0.1e-08 and L < INGS1:
        L += 1
        KA[L] = KO[J, [0, 1, 2]].min()
        PA[L] = np.dot(P[J], [P1, P2, P3])
        J[KO[J, [0, 1, 2]] == KO[J, [0, 1, 2]].min()] += 1

    N = L + 1  # =L in original Fortran

    if L >= INGS1:  # > in original Fortran
        print(
            "to prevent array overflow, CUT OFF PROB. "
            "in CAP outage table reduced to %13.6f" % (PA[L])
        )

    PA[N] = 0.0

    return N


def _gsm(N, KT, KP, P1, P2, P3, PA, KA):
    """
    Add a 2-state or a 3-state unit model to the generation capacity-outage model

    Its high-level idea and illustration can be partially found in these slides:
    https://www.dropbox.com/s/krcse3mjuh97i88/module_6-1.pdf?dl=0

    :param int N: total number of starting states
    :param int KT: rounded (nearest integer) full capacity of the added gen unit
    :param int KP: rounded (nearest integer) derated capacity of the added gen unit
    :param float P1: exact prob. of the I-th gen unit at its full capacity
    :param float P2: exact prob. of the I-th gen unit at its derated capacity
    :param float P3: exact prob. of the I-th gen unit in total loss (i.e. zero MW)
    :param numpy.ndarray PA: CUT OFF probability in the CAP outage table
    :param numpy.ndarray KA: CUT OFF capacity in the CAP outage table
    :return: (*int*) -- updated total number of states

    .. note:: KA and PA are modified in-place
    .. todo:: Check the physical meaning of input parameter N and update doc strings
    """
    INGS = 5000
    INGS1 = INGS - 50

    # Create outage states after unit addition
    KO = np.zeros((5000, 3), dtype=int)  # for local use only
    P = np.zeros((5000, 1))  # for local use only

    for i in range(N):
        KO[i, 0] = KA[i]
        KO[i, 1] = KA[i] + KP
        KO[i, 2] = KA[i] + KT
        P[i] = PA[i]

    # Possibly, N,NN,NNN represents certain counts of some states,
    # rather than the array "index"
    NN = N + 1
    NNN = NN + 1

    for i in range(NN - 1, NNN):
        KO[i, 0] = 1000000
        KO[i, 1] = 1000000
        KO[i, 2] = 1000000
        P[i] = 0.0

    # Select outage states in ascending order of magnitude and
    # calculate their probabilities and frequencies
    L = 0  # 1 in original Fortran
    J1 = 1
    J2 = 0
    if KP == 0:
        J2 += 1
    J3 = 0
    KA[L] = 0
    PA[L] = 1.0

    while True:
        L += 1
        KCH = min(KO[J1, 0], KO[J2, 1], KO[J3, 2])
        KA[L] = KCH
        PA[L] = P[J1] * P1 + P[J2] * P2 + P[J3] * P3
        if KCH == KO[J1, 0]:
            J1 += 1
        if KCH == KO[J2, 1]:
            J2 += 1
        if KCH == KO[J3, 2]:
            J3 += 1
        JM = min(J1, J2, J3)

        if JM >= N:  # > in original Fortran
            break

        if PA[L] <= 0.1e-08:
            break

        if L >= INGS1:  # > in original Fortran
            break

    N = L + 1  # =L in original Fortran

    if L >= INGS1:  # > in original Fortran
        print(
            "to prevent array overflow, CUT OFF PROB. "
            "in CAP outage table reduced to %13.6f" % (PA[L])
        )

    NN = N + 1
    PA[NN - 1] = 0.0  # PA[NN] = 0.0 in original Fortran

    return N
