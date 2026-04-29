# vanilla version
def _net(B, B1, RES, IBAS, BS, M, N):
    """
    Construct the result array based on the outcome of LP

    :param numpy.ndarray B: 1D array with initial shape (200, )
                            the realistic size is determined on-the-fly
                            a vector used in linear programming(LP)-based DCOPF
    :param numpy.ndarray B1: 1D array with initial shape (200, )
                            the realistic size is determined on-the-fly
                            a helper vector used in linear programming-based DCOPF
    :param numpy.ndarray RES: 2D array with shape (250, 3)
                            a helper array used in linear programming-based DCOPF
                            means the result from the (LP)-based DCOPF
                            [:,0]: the load curtailments (based on the LP outcome)
                            [:,1]: unknown
                            [:,2]: defined not used in the Fortran code
    :param numpy.ndarray IBAS: 1D array with initial shape (250, )
                            the realistic size is determined on-the-fly
                            a helper vector used in linear programming-based DCOPF
                            (possibly) means the indices of the "basis-vector" used in LP
    :param numpy.ndarray BS: 1D array with initial shape (200, )
                            the realistic size is determined on-the-fly
                            a helper vector used in linear programming-based DCOPF
    :param int M: used in linear programming(LP)-based DCOPF
                  (possibly) means the total number of constraints
    :param int N: used in linear programming(LP)-based DCOPF
                  (possibly) means the total number of "decision variables" in the LP
    """

    NX1 = N - M  # NX1 is local

    for i in range(N):
        for j in range(3):
            RES[i, j] = 0

    for i in range(M):
        k = IBAS[i]
        if k > NX1:
            RES[k, 0] = -BS[i]
            continue
        RES[k, 0] = BS[i]

    for i in range(M):
        i1 = i + NX1
        if B1[i] < 0:
            RES[i1, 1] = 1.0
        RES[i1, 0] += B[i]


def net(B, B1, RES, IBAS, BS, M, N):
    """
    Construct the result array based on the outcome of LP

    :param numpy.ndarray B: 1D array with initial shape (200, )
                            the realistic size is determined on-the-fly
                            a vector used in linear programming(LP)-based DCOPF
    :param numpy.ndarray B1: 1D array with initial shape (200, )
                            the realistic size is determined on-the-fly
                            a helper vector used in linear programming-based DCOPF
    :param numpy.ndarray RES: 2D array with shape (250, 3)
                            a helper array used in linear programming-based DCOPF
                            means the result from the (LP)-based DCOPF
                            [:,0]: the load curtailments (based on the LP outcome)
                            [:,1]: unknown
                            [:,2]: defined not used in the Fortran code
    :param numpy.ndarray IBAS: 1D array with initial shape (250, )
                            the realistic size is determined on-the-fly
                            a helper vector used in linear programming-based DCOPF
                            (possibly) means the indices of the "basis-vector" used in LP
    :param numpy.ndarray BS: 1D array with initial shape (200, )
                            the realistic size is determined on-the-fly
                            a helper vector used in linear programming-based DCOPF
    :param int M: used in linear programming(LP)-based DCOPF
                  (possibly) means the total number of constraints
    :param int N: used in linear programming(LP)-based DCOPF
                  (possibly) means the total number of "decision variables" in the LP
    """

    RES[:N, :3] = 0

    RES[IBAS[:M], 0] = BS[:M]
    RES[IBAS[:M][IBAS[:M] > N - M], 0] *= -1

    RES[N - M : N, 1][B1[:M] < 0] = 1
    RES[N - M : N, 0] += B[:M]
