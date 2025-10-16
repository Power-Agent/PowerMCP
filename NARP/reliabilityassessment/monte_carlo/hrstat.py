def hrstat(
    NST, MARGIN, LSFLG, LOLGHA, LOLGHP, LOLTHA, LOLTHP, MGNGHA, MGNGHP, MGNTHA, MGNTHP
):
    """
    Collect hourly statistics at area level and pool level

    :param int NST: indicating the NST-th load-forecasting level
    :param numpy.ndarray MARGIN: 1D array with shape (NOAREA, ), the (original)
        generation margin of each area after deducting the load in that area
    :param numpy.ndarray LSFLG: 1D array with shape (NOAREA, ), the total count of
        (hourly) events that "generation < load" happened in each area
    :param numpy.ndarray LOLTHP to MGNGHP:
                    please refer to the following naming rules for those
                    6-digit statistic-related quantities:

                    The first three digits identify the type of statistic
                        LOL means this is annual loss of load statistic of some type
                        MGN means this is annual sum of negative margins (EUE)
                        SOL means this is the cumulative sum, all years, LOLE
                        SNG means this is the cumulative sum, all years, EUE

                    The fourth digit identifies the cause of an outage
                        T is transmission
                        G is generation
                        S is sum of t & g

                     The fifth digit indicates whether the stat is hourly or peak
                        H is for hourly stats
                        P is for peak stats

                     The sixth digit is for area or pool
                        A is area
                        P is pool

                    Examples:
                        SGNSPA  is the cumulative sum, EUE, total of t&g, peak, area
                        LOLTHP  is the annual loss of load, transmission, hourly, pool

                    LOLTHP, LOLGHP, MGNTHP,  MGNGHP: shape (5, )
                    LOLTHA, MGNTHA, LOLGHA,  MGNGHA: shape (NOAREA, 5)

    .. note:: LOLTPP, LOLGPP, LOLTPA, MGNTPA, MGNTPP, LOLGPA, MGNGPA, MGNGPP are
        modified in place. Besides, to exactly match the final statistics results of
        the Fortran code in the integration test, "int-conversion" logic is kept
        for now
    """
    SUM = sum(MARGIN)

    # Somebody has a loss, else we wouldn't be here
    # Update pool peak LOLE
    if SUM >= 0.0:
        LOLTHP[NST] += 1
    else:
        LOLGHP[NST] += 1

    for j, X in enumerate(MARGIN):
        if X < 0.0:
            LSFLG[j] += 1
            if SUM > 0.0:
                LOLTHA[j, NST] += 1
                MGNTHA[j, NST] += int(-X)
                MGNTHP[NST] += int(-X)
            else:
                LOLGHA[j, NST] += 1
                MGNGHA[j, NST] += int(-X)
                MGNGHP[NST] += int(-X)


def _hrstat(
    NST, MARGIN, LSFLG, LOLGHA, LOLGHP, LOLTHA, LOLTHP, MGNGHA, MGNGHP, MGNTHA, MGNTHP
):
    """
    Collect hourly statistics at area level and pool level

    :param int NST: indicating the NST-th load-forecasting level
    :param numpy.ndarray MARGIN: 1D array with shape (NOAREA, ), the (original)
        generation margin of each area after deducting the load in that area
    :param numpy.ndarray LSFLG: 1D array with shape (NOAREA, ), the total count of
        (hourly) events that "generation < load" happened in each area
    :param numpy.ndarray LOLTHP to MGNGHP:
                    please refer to the following naming rules for those
                    6-digit statistic-related quantities:

                    The first three digits identify the type of statistic
                        LOL means this is annual loss of load statistic of some type
                        MGN means this is annual sum of negative margins (EUE)
                        SOL means this is the cumulative sum, all years, LOLE
                        SNG means this is the cumulative sum, all years, EUE

                    The fourth digit identifies the cause of an outage
                        T is transmission
                        G is generation
                        S is sum of t & g

                     The fifth digit indicates whether the stat is hourly or peak
                        H is for hourly stats
                        P is for peak stats

                     The sixth digit is for area or pool
                        A is area
                        P is pool

                    Examples:
                        SGNSPA  is the cumulative sum, EUE, total of t&g, peak, area
                        LOLTHP  is the annual loss of load, transmission, hourly, pool

                    LOLTHP, LOLGHP, MGNTHP,  MGNGHP: shape (5, )
                    LOLTHA, MGNTHA, LOLGHA,  MGNGHA: shape (NOAREA, 5)

    .. note:: LOLTPP, LOLGPP, LOLTPA, MGNTPA, MGNTPP, LOLGPA, MGNGPA, MGNGPP are
        modified in place. Besides, to exactly match the final statistics results of
        the Fortran code in the integration test, "int-conversion" logic is kept
        for now
    """
    SUM = sum(MARGIN)

    # Somebody has a loss, else we wouldn't be here
    # Update pool peak LOLE
    if SUM >= 0.0:
        LOLTHP[NST] += 1
    else:
        LOLGHP[NST] += 1

    LSFLG[MARGIN < 0] += 1
    if SUM > 0.0:
        LOLTHA[:, NST][MARGIN < 0] += 1
        MGNTHA[:, NST][MARGIN < 0] -= MARGIN[MARGIN < 0].astype(int)
        MGNTHP[NST] -= int(MARGIN[MARGIN < 0].sum())
    else:
        LOLGHA[:, NST][MARGIN < 0] += 1
        MGNGHA[:, NST][MARGIN < 0] -= MARGIN[MARGIN < 0].astype(int)
        MGNGHP[NST] -= int(MARGIN[MARGIN < 0].sum())
