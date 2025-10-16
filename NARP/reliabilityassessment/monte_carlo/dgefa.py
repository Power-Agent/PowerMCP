import numpy as np


# original version
def _dgefa(A, N):
    """
    Factors a double precision matrix by Gaussian elimination.

    :param numpy.ndarray A: the matrix to be factored
    :param int N: the dimension of the matrix A
    :return: (*tuple*) -- INFO: an integer with 0 indicates normal value and K if
        U[K,K] == 0.0, where U is the upper triangular part in the LU decomposition;
        IPVT: an integer vector of pivot indices with shape (N, )

    .. note:: 1. Matrix A is modified in place.
              2. INFO indicates whether :py:func: `dgedi` will have a zero divisor,
              in which case RCOND is used in :py:func: `degco` as a singularity
              indicator. Note that :py:func: `dgefa` is slightly faster if RCOND is
              not set.
              3. A will be modified into an upper triangular matrix with the multipliers
              used to obtain it. The factorization can be written as A = L*U,
              where L is a product of permutation and unit lower triangular matrix
              and U is upper triangular.
              4. A common practice in the realistic implementation of LU decomposition:
              L, U (or LDU with a diagonal matrix D if needed) are not necessarily
              stored explicitly but directly manipulating matrix A so that L and U
              are both stored in modified matrix A.
              5. :py:func: `dgefa` is usually called by :py:func: `dgeco`, but it can be
              called directly to improve the computational performance if RCOND is
              not set. T(dgeco) = (1 + 9/n) * T(dgefa) where T indicates run time.
    """

    IPVT = np.zeros(N, dtype=int)

    #  Gaussian elimination with partial pivoting
    INFO = 0
    for K in range(N - 1):
        KP1 = K + 1

        # Find L = "pivot index"
        L = (
            np.argmax(abs(A[K:N, K])) + K
        )  # L = IDAMAX(N-K+1,A(K,K),1) + K - 1 in Fortran
        # The meaning of "+k-1" means move K-1 steps; since we use a 0-based index here for K,
        # thus, using "+K" here is correct

        IPVT[K] = L

        # zero pivot implies this column is already triangularized
        if A[L, K] != 0.0:
            # interchange if necessary
            if L != K:
                A[L, K], A[K, K] = A[K, K], A[L, K]

            # compute multipliers
            T = -1.0 / A[K, K]
            A[K + 1 : N, K] *= T  # DSCAL(N-K,T,A[K+1,K],1) in Fortran
            # A[K + 1 : N, K] in Fortran

            # row elimination with column indexing
            for J in range(KP1, N):  # in Fortran: from KP1 to N (included)
                T = A[L, J]
                if L != K:
                    A[L, J] = A[K, J]
                    A[K, J] = T
                A[K + 1 : N, J] += (
                    T * A[K + 1 : N, K]
                )  # DAXPY[N-K,T,A[K+1,K],1,A[K+1,J],1) in Fortran
                # A[K + 1 : N, K]in Fortran

        else:
            INFO = K

    IPVT[N - 1] = N - 1  # in original Fortran: IPVT[N] = N
    if A[N - 1, N - 1] == 0.0:  # IN original Fortran A[N,N]
        INFO = N - 1

    return INFO, IPVT


# vectorized version
def dgefa(A, N):
    """
    Factors a double precision matrix by Gaussian elimination.

    :param numpy.ndarray A: the matrix to be factored
    :param int N: the dimension of the matrix A
    :return: (*tuple*) -- INFO: an integer with 0 indicates normal value and K if
        U[K,K] == 0.0, where U is the upper triangular part in the LU decomposition;
        IPVT: an integer vector of pivot indices with shape (N, )

    .. note:: 1. Matrix A is modified in place.
              2. INFO indicates whether :py:func: `dgedi` will have a zero divisor,
              in which case RCOND is used in :py:func: `degco` as a singularity
              indicator. Note that :py:func: `dgefa` is slightly faster if RCOND is
              not set.
              3. A will be modified into an upper triangular matrix with the multipliers
              used to obtain it. The factorization can be written as A = L*U,
              where L is a product of permutation and unit lower triangular matrix
              and U is upper triangular.
              4. A common practice in the realistic implementation of LU decomposition:
              L, U (or LDU with a diagonal matrix D if needed) are not necessarily
              stored explicitly but directly manipulating matrix A so that L and U
              are both stored in modified matrix A.
              5. :py:func: `dgefa` is usually called by :py:func: `dgeco`, but it can be
              called directly to improve the computational performance if RCOND is
              not set. T(dgeco) = (1 + 9/n) * T(dgefa) where T indicates run time.
    """

    IPVT = np.zeros(N, dtype=int)

    # Gaussian elimination with partial pivoting
    INFO = 0
    for K in range(N - 1):
        # Find pivot index L
        L = np.argmax(abs(A[K:N, K])) + K
        # L = IDAMAX(N-K+1, A(K,K), 1) + K - 1 in Fortran, index shifting by K here

        IPVT[K] = L

        # Zero pivot implies no operations are needed to apply
        if A[L, K] != 0.0:
            if L != K:
                A[[L, K], K:] = A[[K, L], K:]
            A[K + 1 : N, K] *= -1.0 / A[K, K]
            A[K + 1 : N, K + 1 : N] += np.outer(A[K + 1 : N, K], A[K, K + 1 : N])

        else:
            INFO = K

    IPVT[N - 1] = N - 1
    if A[N - 1, N - 1] == 0.0:
        INFO = N - 1

    return INFO, IPVT
