def _pkstat(
    NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP
):
    """
    Collect (daily) peak statistics at area level and pool level

    :param int NST: indicating the NST-th load-forecasting level
    :param numpy.ndarray MARGIN: 1D array with shape (NOAREA, ) the (original)
        generation margin of each area after deducting the load in that area
    :param numpy.ndarray LOLTPP to MGNGPP:
                    please refer to the following naming rules for those
                    6-digit statistic-related quantities:

                    The first three digits identify the type of statistic
                        LOL means this is the annual loss of load statistics
                        MGN means this is the annual sum of negative margins, EUE
                        SOL means this is the cumulative sum, all years, LOLE
                        SNG means this is the cumulative sum, all years, EUE

                    The fourth digit identifies the cause of the outage
                        T is transmission
                        G is generation
                        S is the sum of t & g

                     The fifth digit indicates whether the stat is hourly or peak
                         H is for hourly stats
                         P is for peak stats

                     The sixth digit is for area or pool
                         A is area
                         P is pool

                    Examplex:
                        SGNSPA  is the cumulative sum, EUE, total of t&g, peak, area
                        LOLTHP  is the annual loss of load, transmission, hourly, pool

                    LOLTPP, LOLGPP, MGNTPP, MGNGPP: shape (5, )
                    LOLTPA, MGNTPA, LOLGPA, MGNGPA: shape (NOAREA, 5)

    .. note:: LOLTPP, LOLGPP, LOLTPA, MGNTPA, MGNTPP, LOLGPA, MGNGPA, MGNGPP are
        modified in place. Besides, to exactly match the final statistics results of
        the Fortran code in the integration test, "int-conversion" logic is kept
        for now
    """
    SUM = sum(MARGIN)

    # Some area has a loss, else we wouldn't be here
    # Update pool peak LOLE
    if SUM >= 0:
        LOLTPP[NST] += 1
    else:
        LOLGPP[NST] += 1

    for j, X in enumerate(MARGIN):
        if X < 0.0:
            if SUM > 0.0:
                LOLTPA[j, NST] += 1
                MGNTPA[j, NST] -= int(X)
                MGNTPP[NST] -= int(X)
            else:
                LOLGPA[j, NST] += 1
                MGNGPA[j, NST] -= int(X)
                MGNGPP[NST] -= int(X)


def pkstat(NST, MARGIN, LOLGPA, LOLGPP, LOLTPA, LOLTPP, MGNGPA, MGNGPP, MGNTPA, MGNTPP):
    """
    Collect (daily) peak statistics at area level and pool level

    :param int NST: indicating the NST-th load-forecasting level
    :param numpy.ndarray MARGIN: 1D array with shape (NOAREA, ) the (original)
        generation margin of each area after deducting the load in that area
    :param numpy.ndarray LOLTPP to MGNGPP:
                    please refer to the following naming rules for those
                    6-digit statistic-related quantities:

                    The first three digits identify the type of statistic
                        LOL means this is the annual loss of load statistics
                        MGN means this is the annual sum of negative margins, EUE
                        SOL means this is the cumulative sum, all years, LOLE
                        SNG means this is the cumulative sum, all years, EUE

                    The fourth digit identifies the cause of the outage
                        T is transmission
                        G is generation
                        S is the sum of t & g

                     The fifth digit indicates whether the stat is hourly or peak
                         H is for hourly stats
                         P is for peak stats

                     The sixth digit is for area or pool
                         A is area
                         P is pool

                    Examplex:
                        SGNSPA  is the cumulative sum, EUE, total of t&g, peak, area
                        LOLTHP  is the annual loss of load, transmission, hourly, pool

                    LOLTPP, LOLGPP, MGNTPP, MGNGPP: shape (5, )
                    LOLTPA, MGNTPA, LOLGPA, MGNGPA: shape (NOAREA, 5)

    .. note:: LOLTPP, LOLGPP, LOLTPA, MGNTPA, MGNTPP, LOLGPA, MGNGPA, MGNGPP are
        modified in place. Besides, to exactly match the final statistics results of
        the Fortran code in the integration test, "int-conversion" logic is kept
        for now
    """
    SUM = sum(MARGIN)

    # Some area has a loss, else we wouldn't be here
    # Update pool peak LOLE
    if SUM >= 0:
        LOLTPP[NST] += 1
    else:
        LOLGPP[NST] += 1

    if SUM > 0.0:
        LOLTPA[:, NST][MARGIN < 0] += 1
        MGNTPA[:, NST][MARGIN < 0] -= MARGIN[MARGIN < 0].astype(int)
        MGNTPP[NST] -= MARGIN[MARGIN < 0].sum().astype(int)
    else:
        LOLGPA[:, NST][MARGIN < 0] += 1
        MGNGPA[:, NST][MARGIN < 0] -= MARGIN[MARGIN < 0].astype(int)
        MGNGPP[NST] -= MARGIN[MARGIN < 0].sum().astype(int)
