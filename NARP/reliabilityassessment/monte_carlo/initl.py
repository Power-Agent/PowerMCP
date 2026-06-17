import numpy as np

from reliabilityassessment.monte_carlo.filem import filem


def _initl(JSTEP, EVNTS, IPOINT, MFA, NUMINQ, QTR):
    """
    Initialization for the Monte Carlo Simulation

    :param int JSTEP: frequency of simulation statistics collection, 1: hourly 24:
        daily, i.e. only peak stats are collected
    :param numpy.ndarray EVNTS: 1D array of events
    :param int IPOINT: pointer of the first (already/previously stored) entry in the
        event list, defaults to -1 if the list is empty
    :param int MFA: pointer of the first available (i.e. empty) entry in the event list
    :param int NUMINQ: up-to-date total number of event entries (inquires)
    :param numpy.ndarray QTR: first hour index of the last three quarters of a year
                              i.e. [13*168+0.5, 13*2*168+0.5, 13*3*168+0.5]
    :return: (*tuple*) -- ATRIB: events attribute vector of length 2
                                 ATRIB[0] -- global simulation clock (in unit: hour)
                                 ATRIB[1] -- int, simulation event type
                                 1: hourly
                                 2: weekly
                                 3: quarterly
                                 4: yearly
                          CLOCK: global time clock used in sequential Monte Carlo
                                 simulation
                          updated IPOINT, MFA, and NUMINQ

    .. note:: EVNTS is modified in place
    """

    print("Entering function initl")
    CLOCK = 0.0

    # Schedule all quarterly state changes
    ATRIB = np.zeros(2)
    ATRIB[1] = 3
    ATRIB[0] = 0.5
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    ATRIB[0] = QTR[0]
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    ATRIB[0] = QTR[1]
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    ATRIB[0] = QTR[2]
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    # Do Not Put Anything Between These Two 'filem' calls. Need The 8760.
    # Schedule First Call To Year (comment by Dr. Singh)
    ATRIB[0] = 8760.0
    ATRIB[1] = 4
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    # Schedule First Call To SBRTNE Week To Schedule Planned Outage
    ATRIB[0] = 0.5
    ATRIB[1] = 2
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    # Schedule First Monte Carlo Draw
    ATRIB[1] = 1
    ATRIB[0] = JSTEP
    # Call the entry point function of Monte Carlo simulation
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    return ATRIB, CLOCK, IPOINT, MFA, NUMINQ


def initl(JSTEP, EVNTS):
    """
    Initialization for the Monte Carlo Simulation

    :param int JSTEP: frequency of simulation statistics collection, 1: hourly 24:
        daily, i.e. only peak stats are collected
    :param numpy.ndarray EVNTS: 1D array of events
    :return: (*tuple*) -- ATRIB: events attribute vector of length 2
                                 ATRIB[0] -- global simulation clock (in unit: hour)
                                 ATRIB[1] -- int, simulation type
                                 0: hourly
                                 1: weekly
                                 2: quarterly
                                 3: yearly
                          CLOCK: global time clock used in sequential Monte Carlo
                                 simulation
                          IPOINT: pointer of the first (already/previously stored) entry
                                  in the event list, defaults to -1 if the list is empty
                          MFA: pointer of the first available (i.e. empty) entry in the
                               event list
                          NUMINQ: up-to-date total number of event entries (inquires)

    .. note:: EVNTS is modified in place
    """
    # fmt: off
    EVNTS[:28] = np.array(
        [
            24,   0.5,    3, 0.0,  # noqa: E241 1st quarterly state change
            8.0,  2184.5, 3, 0.0,  # noqa: E241 2nd quarterly state change
            12.0, 4368.5, 3, 0.0,  # noqa: E241 3rd quarterly state change
            16.0, 6552.5, 3, 0.0,  # noqa: E241 4th quarterly state change
            -1.0, 8760.0, 4, 0.0,  # noqa: E241 first call to subroutine "year"
            0,    0.5,    2, 0.0,  # noqa: E241 first call to subroutine "week"
            4.0,  JSTEP,  1, 0.0,  # noqa: E241 first Monte Carlo draw
        ]
    )
    # fmt: on
    ATRIB = np.array([JSTEP, 1.0])
    CLOCK = 0.0
    IPOINT = 20
    MFA = 28
    NUMINQ = 7

    return ATRIB, CLOCK, IPOINT, MFA, NUMINQ
