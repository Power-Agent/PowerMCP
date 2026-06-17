from reliabilityassessment.monte_carlo.filem import filem


def quartr(IQ, RATES, CLOCK, ATRIB, NHRSYR, MFA, NUMINQ, IPOINT, EVNTS):
    """
    Schedule quarterly simulation events

    :param int IQ: index of quarters (0, 1, 2, 3)
    :param numpy.ndarray RATES: original rating data of each unit for four seasons with
        shape (NUNITS, 4)
    :param float CLOCK: (global) time clock used in sequential Monte Carlo simulation
    :param numpy.ndarray ATRIB: events attribute vector of length 2
                                ATRIB[0] -- global simulation clock (in unit: hour)
                                ATRIB[1] -- int, simulation type
                                 0: hourly
                                 1: weekly
                                 2: quarterly
                                 3: yearly
    :param int NHRSYR: 8760, number of hours in a typical simulation year
    :param int MFA: pointer of the first available (i.e. empty) entry in the event list
    :param int NUMINQ: up-to-date total number of event entries (inquires)
    :param int IPOINT: pointer of the first (already/previously stored) entry in the
        event list, defaults to -1 if the list is empty
    :param numpy.ndarray EVNTS: 1D array of events
    :return: (*tuple*) -- updated IQ, IPOINT, MFA, NUMINQ and RATING, 1D numpy array
        with shape (NUNITS, ) that gives the actual rating of each unit in Monte
        Carlo simulation

    .. note:: ATRIB, EVNTS are modified in place
    """
    IQ = (IQ + 1) % 4
    RATING = RATES[:, IQ].copy()
    ATRIB[0] = CLOCK + NHRSYR
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    return IQ, IPOINT, MFA, NUMINQ, RATING
