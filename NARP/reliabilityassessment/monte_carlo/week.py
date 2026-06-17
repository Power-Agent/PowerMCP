from reliabilityassessment.monte_carlo.filem import filem


def week(CLOCK, ATRIB, MFA, NUMINQ, IPOINT, EVNTS, PLNDST, JHOUR, JPLOUT):
    """
    Schedule weekly simulation events

    :param float CLOCK: global time clock of the sequential Monte Carlo simulation
    :param numpy.ndarray ATRIB: events attribute vector of length 2
                                ATRIB[0] -- global simulation clock (in unit: hour)
                                ATRIB[1] -- int, simulation type
                                 0: hourly
                                 1: weekly
                                 2: quarterly
                                 3: yearly
    :param int MFA: pointer of the first available (i.e. empty) entry in the event list
    :param int NUMINQ: up-to-date total number of event entries (inquires)
    :param int IPOINT: pointer of the first (already/previously stored) entry in the
        event list, defaults to -1 if the list is empty
    :param numpy.ndarray EVNTS: 1D array of events
    :param numpy.ndarray PLNDST: 1D array with shape (NUNITS, ), the on/off status
        (due to planned maintenance) of each unit, i.e., 0/1 indicates off/on.
    :param int JHOUR: index of the current hour
    :param numpy.ndarray JPLOUT: 2D array with shape (52, NUNITS+1), table of planned
        outages of units per week, the first column gives the total number of units
        that are off for each week.
    :return: (*tuple*) -- updated IPOINT, MFA, NUMINQ

    .. note:: ATRIB, PLNDST, EVNTS are modified in place.
    """

    # assigning the event attribute by shifting the clock for a week
    ATRIB[0] = CLOCK + 168

    # place new entry into the event list
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    PLNDST[:] = 1.0

    # in original Fortran code JWEEK = JHOUR/168 + 1 due to 1-based index
    JWEEK = JHOUR // 168
    if JWEEK > 51:
        return IPOINT, MFA, NUMINQ

    # total number of maintenance requests in the JWEEK-th week
    MT = JPLOUT[JWEEK, 0]
    PLNDST[JPLOUT[JWEEK, 1 : MT + 1]] = 0.0

    return IPOINT, MFA, NUMINQ
