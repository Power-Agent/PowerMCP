import numpy as np


# simplified version without redundant variables
def dgedi(A, N, IPVT):
    """
    Computes the determinant and inverse of a matrix using the factors computed by
    :py:func: `dgeco`

    :param numpy.ndarray A: the input matrix
    :param int N: the dimension of matrix A
    :param (*numpy.ndarray*) -- IPVT, an integer vector of pivot indices with shape
        (N, ) from :py:func:`dgeco` or :py:func:`dgefa`

    .. note:: 1. Matrix A is modified in place.
              2. A will be inversed or unchanged based on different situations.
              3. An error will be thrown if trying to inverse the matrix with
              diagonal zeros, which shouldn't happen if :py:func:`dgeco` sets
              RCOND > 0.0 or :py:func:`dgefa` sets INFO == 0.
    """
    # WORK is a local vector of shape (N, )
    WORK = np.zeros(N)

    # Compute "inverse(U)". U is the upper triangular part of LU decomposition,
    # which is implicitly stored “in place” in the original matrix A
    for K in range(N):
        A[K, K] = 1.0 / A[K, K]
        A[:K, K] *= -A[K, K]  # DSCAL[K-1,T,A(1,K),1) in Fortran where T = -A[K, K]

        T = A[K, K + 1 : N].copy()
        A[K, K + 1 : N] = 0.0
        A[: K + 1, K + 1 : N] += np.outer(
            A[: K + 1, K], T
        )  # DAXPY[K,T,A(1,K),1,A(1,J),1) in Fortran

    # Form "inverse(U)*inverse(L)". L is the lower triangular part of LU decomposition.
    # Similar to the above U, L is stored implicitly in A.
    if N > 1:
        for KB in range(1, N):
            K = N - 1 - KB
            WORK[K + 1 : N] = A[K + 1 : N, K]
            A[K + 1 : N, K] = 0.0

            # DAXPY(N,T,A(1,J),1,A(1,K),1) in Fortran
            # where T runs through WORK[K + 1 : N]
            A[:N, K] += (A[:N, K + 1 : N] * WORK[K + 1 : N]).sum(axis=1)
            L = IPVT[K]

            # DSWAP(N,A(1,K),1,A(1,L),1) in Fortran
            if L != K:
                A[:N, [K, L]] = A[:N, [L, K]]


# original version with unused variables such as DET and JOB
def _dgedi(A, N, IPVT, JOB):
    """
    Computes the determinant and inverse of a matrix
    using the factors computed by dgeco

    :param numpy.ndarray A: the matrix to be factored
    :param int N: the order of the matrix  A
    :param numpy.ndarray IPVT: the (integer) pivot vector from dgeco or dgefa
                               shape (N,)

    :param int JOB: 1 both determinant and inverse
                    2 inverse only
                    3 determinant only

    .. note:: 1) arrays are modified in place.
              2) on return, A  will be inverse of the original matrix if requested
                            otherwise unchanged.
              3) DET and WORK are not used outside
                :param float DET: the determinant of the original matrix if requested.
                                  Otherwise not referenced.
                                  determinant = det(1) * 10.0**det(2)
                                  with 1.0 <= abs(det(1)) < 10.0, or det(1) == 0.0
                :param numpy.ndarray WORK: a vector of which the contents will be destroyed.
                               shape (N,)

              4) Error condition: a "division by zero" will occur if the input factor
                                  contains a zero on the diagonal, and the inverse is requested.
                                  It will not occur if the functions are called correctly
                                  and if dgeco has set (achieve?) RCOND > 0.0,
                                  or dgefa has set (achieve?) INFO == 0
    """
    DET = np.zeros(2)
    WORK = np.zeros(N)

    # Compute determinant
    if JOB == 1 or JOB == 3:
        DET[0] = 1.0
        DET[1] = 0.0
        TEN = 10.0
        for i in range(1, N + 1):
            if IPVT[i] != i:
                DET[0] = -DET[0]
            DET[0] = A[i, i] * DET[0]

            if DET[0] == 0.0:
                break

            while abs(DET(1)) < 1.0:
                DET[0] *= TEN
                DET[1] -= 1.0

            while abs(DET(1)) >= TEN:
                DET[0] /= TEN
                DET[1] += 1.0

    # If no need to compute inverse, then return
    if JOB == 3:
        return

    # Compute "inverse(U)". U is the upper triangular part of LU decomposition,
    # which is implicitly stored “in place” in the original matrix A
    for K in range(N):
        A[K, K] = 1.0 / A[K, K]
        T = -A[K, K]
        A[:K, K] *= T  # DSCAL[K-1,T,A(1,K),1) in Fortran
        KP1 = K + 1
        if N > KP1:
            for J in range(KP1, N):  # in original Fortran: from KP1 to N (included)
                T = A[K, J]
                A[K, J] = 0.0
                A[: K + 1, J] += (
                    T * A[: K + 1, K]
                )  # DAXPY[K,T,A(1,K),1,A(1,J),1) in Fortran

    # Form "inverse(U)*inverse(L)". L is the lower triangular part of LU decomposition.
    # Similar to the above U, L is stored implicitly in A.
    if N <= 1:
        return
    for KB in range(1, N):
        K = N - 1 - KB
        KP1 = K + 1
        for i in range(KP1, N):
            WORK[i] = A[i, K]
            A[i, K] = 0.0
        for J in range(KP1, N):
            T = WORK[J]
            A[:N, K] += T * A[:N, J]  # DAXPY(N,T,A(1,J),1,A(1,K),1) in Fortran
        L = IPVT[K]
        if L != K:
            A[:N, K], A[:N, L] = (
                A[:N, L],
                A[:N, K].copy(),
            )  # DSWAP(N,A(1,K),1,A(1,L),1) in Fortran

    return
