from reliabilityassessment.monte_carlo.dgefa import dgefa


def dgeco(A, N):
    """
    Factors a double precision matrix by Gaussian elimination
    and estimates the matrix's condition number (though not used).

    :param numpy.ndarray A: the matrix to be factored
    :param int N: the dimension of matrix A
    :return: (*numpy.ndarray*) -- IPVT: an integer vector of pivot indices with
        shape (N, )

    .. note:: 1. Matrix A is modified in place.
              2. If `RCOND` is not set, :py:func: `dgefa` is slightly faster.
              3. `RCOND` and `Z` are designed to investigate the root cause of
              potential numerical failures during the matrix factorization (inversion),
              which are not used for now. The logic is kept for references only.

              RCOND: a float to estimate the reciprocal condition of A. For the
              system  A*x = b , relative perturbations in A and b of size epsilon may
              cause relative perturbations in x of size epsilon/RCOND. if RCOND is
              so small that the logical expression 1.0 + RCOND == 1.0 is true,
              then A may be singular to working precision. In particular, RCOND is
              zero if the exact singularity is detected or the estimate underflows.

              Z: a temporal numpy array for intermediate calculation usage. If A is
              close to a singular matrix, then Z is an approximate null vector in the
              sense that Norm(A*Z) = RCOND * norm(A) * norm(Z).
    """
    # Some intermediate variables or original returning variables are never used outside
    # e.g. YNORM, ANORM, RCOND and Z
    # Currently still keep them in case of any special debugging need in the future.

    # Compute 1-norm of A, i.e., is the maximum abs. column sum
    # ANORM = 0.0
    # for j in range(N):
    #     ANORM = max(ANORM, sum(abs(A[:, j])))

    # Factorization by calling dgefa
    # The 1st return parameter 'INFO' is not used anywhere.
    # Currently still keep it as a placeholder for future debugging purposes
    _, IPVT = dgefa(A, N)

    # EK = 1.0
    # Z = np.zeros(N)
    # for k in range(N):
    #     if Z[k] != 0.0:
    #         EK = abs(EK) if Z[k] <= 0 else -abs(EK)
    #     if abs(EK - Z[k]) > abs(A[k, k]):
    #         S = abs(A[k, k]) / abs(EK - Z[k])
    #         Z *= S
    #         EK = S * EK

    #     WK = EK - Z[k]
    #     WKM = -EK - Z[k]
    #     S = abs(WK)
    #     SM = abs(WKM)
    #     if A[k, k] != 0.0:
    #         WK = WK / A[k, k]
    #         WKM = WKM / A[k, k]
    #     else:
    #         WK = 1.0
    #         WKM = 1.0

    #     KP1 = k + 1
    #     if KP1 <= N - 1:
    #         for j in range(KP1, N):  # in original Fortran: from KP1 to N (included)
    #             SM += abs(Z[j] + WKM * A[k, j])
    #             Z[j] += WK * A[k, j]
    #             S += abs(Z[j])
    #         if S < SM:
    #             T = WKM - WK
    #             WK = WKM
    #             # in original Fortran: from KP1 to N (included)
    #             for j in range(KP1, N):
    #                 Z[j] += T * A[k, j]
    #     Z[k] = WK

    # S = 1.0 / sum(Z)
    # Z *= S

    # # L, U stands for the lower and upper-triangular decomposition of A
    # # Y, V are the names for certain intermediate matrices during computation
    # # W stands for (possibly) the "old" /"initial" value of the Z vector

    # # Solve TRANS(L)*Y = W
    # for KB in range(N):
    #     K = N - 1 - KB
    #     if K < N - 1:
    #         Z[K] += np.dot(
    #             A[K + 1 : N, K], Z[K + 1 : N]
    #         )  # DDOT(N-1-K,A(K+1,K),1,Z(K+1),1)
    #     if abs(Z[K]) > 1.0:
    #         S = 1.0 / abs(Z[K])
    #         Z *= S
    #     L = IPVT[K]
    #     Z[L], Z[K] = Z[K], Z[L]

    # S = 1.0 / sum(Z)
    # Z *= S

    # YNORM = 1.0
    # # Solve L*V = Y
    # for K in range(N):
    #     L = IPVT[K]
    #     T = Z[L]
    #     Z[L], Z[K] = Z[K], Z[L]
    #     if K < N - 1:
    #         Z[K + 1 : N] += T * A[K + 1 : N, K]  # DAXPY(N-1-K,T,A(K+1,K),1,Z(K+1),1)
    #     if abs(Z[K]) > 1.0:
    #         S = 1.0 / abs(Z[K])
    #         Z *= S
    #         YNORM = S * YNORM

    # S = 1.0 / sum(Z)
    # Z *= S
    # YNORM = S * YNORM

    # # Solve  U*Z = V
    # for KB in range(N):
    #     K = N - 1 - KB
    #     if abs(Z[K]) > abs(A[K, K]):
    #         S = abs(A[K, K]) / abs(Z[K])
    #         Z *= S
    #         YNORM = S * YNORM
    #     if A[K, K] != 0.0:
    #         Z[K] = Z[K] / A[K, K]
    #     if A[K, K] == 0.0:
    #         Z[K] = 1.0
    #     T = -Z[K]
    #     Z[0:K] += T * A[0:K, K]  # DAXPY(K-1,T,A(1,K),1,Z(1),1)

    # # Make ZNORM = 1.0
    # S = 1.0 / sum(Z)
    # Z *= S
    # YNORM = S * YNORM

    # if ANORM != 0.0:
    #     RCOND = YNORM / ANORM
    # else:
    #     RCOND = 0.0

    return IPVT
