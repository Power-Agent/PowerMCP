import sys


def remove(NUMINQ, ATRIB, EVNTS, IPOINT):
    """
    Remove an event from event list

    :param int NUMINQ: up-to-date total number of event entries (inquires)
    :param numpy.ndarray ATRIB: events attribute vector of length 2
                                ATRIB[0] -- global simulation clock (in unit: hour)
                                ATRIB[1] -- int, simulation event type
                                 1: hourly
                                 2: weekly
                                 3: quarterly
                                 4: yearly
    :param numpy.ndarray EVNTS: 1D array of events
    :param int IPOINT: pointer of the first (already/previously stored) entry;
        initial value = -1
    :return: (*tuple*) -- MFA: pointer of first available (i.e. empty) slot in the
        event list. IPOINT, NUMINQ: see above

    .. note:: ATRIB and EVNTS are modified in place
    """

    # print("Remove an event from the event list")

    if NUMINQ <= 0:
        print("Error in 'remove', the event list is empty!")
        sys.exit()  # abort the whole program
    elif IPOINT < 0:
        print("Error in 'remove', IPOINT is negative!")
        return  # just return
    else:
        # Remove entry from events array
        ATRIB[0] = EVNTS[IPOINT + 1]
        ATRIB[1] = EVNTS[IPOINT + 2]

        NUMINQ -= 1

        # Update event list pointers...First update MFA
        MFA = IPOINT
        EVNTS[IPOINT + 1] = 0.0
        EVNTS[IPOINT + 2] = 0.0

        # First (still existing) (i.e. unvisited) position pointer;
        # item is always removed from this position (when called)
        IPOINT = int(EVNTS[IPOINT])

        return MFA, NUMINQ, IPOINT
