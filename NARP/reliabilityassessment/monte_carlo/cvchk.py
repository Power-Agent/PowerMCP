def cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ):
    """
    Check the convergence of the sequential Monte Carlo simulation. The formulation of
    convergence criteria refers to the slide in the following directory
    https://www.dropbox.com/s/mbooxvj85jb2oi2/module_4-3.pdf?dl=0, on page 25,
    26 and 31.

    :param int CLOCK: global time clock used in the simulation
    :param int FINISH: number of hours to terminate if fails to converge, typically
        integer multiples of the total hours of a year
    :param int IYEAR: integer index of the year
    :param float CVTEST: threshold value for convergence, defaults to 0.025 if 0 is set
    :param float SUM: cumulative quantities for a specific reliability index
    :param float XLAST: reliability index of the last simulation year
    :param float SSQ: cumulative square error of the specific reliability index
    :return: (*tuple*) -- a tuple of three scalars, RFLAG: an integer indicator of
        “early return or not” and updated SSQ, XLAST

    .. note:: Variable names may not be the same as the ones in the reference slides
    """

    RFLAG = int(CLOCK >= FINISH)

    DIFF = SUM - XLAST
    XLAST = SUM
    SSQ = SSQ + DIFF**2

    # window size for statistics cannot be less than 5 years (simulation runs)
    # assume IYEAR is 0 based here
    if IYEAR < 5:
        return RFLAG, SSQ, XLAST

    XMEAN = SUM / IYEAR

    XX = CVTEST * XMEAN if CVTEST else 0.025 * XMEAN

    STDERR = pow(((SSQ / IYEAR) - XMEAN**2) / IYEAR, 0.5)

    # how many multiples of our "COV" to the given threshold
    XKCPXX = STDERR / XX if XX else 0.0

    print(
        f"{IYEAR}-th REPLICATION; SUM={SUM} NEW={DIFF} MEAN={XMEAN} CONVERGENCE="
        f"{XKCPXX}"
    )

    # edge case, to avoid permanent-loop
    if XMEAN == 0.0:
        return RFLAG, SSQ, XLAST

    # The following part exists in the original Fortran code, but since 'STDERR'
    # will not be negative based on theoretical proof, so we comment here
    # if STDERR < 0.0:
    #     return RFLAG, SSQ, XLAST

    if STDERR < XX:
        RFLAG = 1
        print("**************** SIMULATION CONVERGED ****************")
        print(f"    CLOCK = {CLOCK} STD = {STDERR} TEST = {XX}")

    return RFLAG, SSQ, XLAST


def _cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ):
    """
    Check the convergence of the sequential Monte Carlo simulation. The formulation of
    convergence criteria refers to the slide in the following directory
    https://www.dropbox.com/s/mbooxvj85jb2oi2/module_4-3.pdf?dl=0, on page 25,
    26 and 31.

    :param int CLOCK: global time clock used in the simulation
    :param int FINISH: number of hours to terminate if fails to converge, typically
        integer multiples of the total hours of a year
    :param int IYEAR: integer index of the year
    :param float CVTEST: threshold value for convergence, defaults to 0.025 if 0 is set
    :param float SUM: cumulative quantities for a specific reliability index
    :param float XLAST: reliability index of the last simulation year
    :param float SSQ: cumulative square error of the specific reliability index
    :return: (*tuple*) -- a tuple of three scalars, RFLAG: an integer indicator of
        “early return or not” and updated SSQ, XLAST

    .. note:: Variable names may not be the same as the ones in the reference slides
    """

    RFLAG = 0

    if CLOCK >= FINISH:
        RFLAG = 1

    DIFF = SUM - XLAST
    XLAST = SUM
    SSQ = SSQ + DIFF**2

    if (
        IYEAR < 5
    ):  # window size for statistics cannot be less than 5 years (simulation runs)
        return RFLAG, SSQ, XLAST

    XMEAN = SUM / IYEAR
    if CVTEST == 0.0:
        XX = 0.025 * XMEAN  # 0.025 is a default value for CVTEST
    else:
        XX = CVTEST * XMEAN

    VAR = (SSQ / IYEAR) - (XMEAN**2)
    STD = pow(VAR, 0.5)

    STDERR = STD / (IYEAR**0.5)
    XKCPXX = 0.0
    if XX != 0.0:
        XKCPXX = STDERR / XX  # how many multiples of our "COV" to the given threshold

    print(
        IYEAR,
        " -th REPLICATION; SUM=",
        SUM,
        "  NEW=",
        DIFF,
        "  MEAN=",
        XMEAN,
        "  CONVERGENCE=",
        XKCPXX,
    )

    if XMEAN == 0.0:  # edge case, to avoid permanent-loop
        return RFLAG, SSQ, XLAST

    # The following part exists in the original Fortran code, but since 'STDERR'
    # will not be negative based on theoretical proof, so we comment here
    # if STDERR < 0.0:
    #     return RFLAG, SSQ, XLAST

    if STDERR < XX:
        RFLAG = 1
        print("**************** SIMULATION CONVERGED ****************")
        print("    CLOCK = ", CLOCK, "' STD = ", STDERR, " TEST = ", XX)

    return RFLAG, SSQ, XLAST
