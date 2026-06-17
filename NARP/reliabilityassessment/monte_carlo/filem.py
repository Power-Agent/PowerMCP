def filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS):
    """
    Append a new event into the event list, maintain chronological order and update
    corresponding pointers

    :param int MFA: pointer of the first available (i.e. empty) entry in the event list
    :param numpy.ndarray ATRIB: events attribute vector of length 2
                                ATRIB[0] -- global simulation clock (in unit: hour)
                                ATRIB[1] -- int, simulation event type
                                 1: hourly
                                 2: weekly
                                 3: quarterly
                                 4: yearly
    :param int NUMINQ: up-to-date total number of event entries (inquires)
    :param int IPOINT: pointer of the first (already/previously stored) entry in the
        event list, defaults to -1 if the list is empty
    :param numpy.ndarray EVNTS: 1D array of events
    :return: (*tuple*) -- updated NUMINQ, MFA and IPOINT

    .. note:: EVNTS is modified in place
    """

    K = 0  # dummy pointer used to record predecessor

    # insert new entry
    NEW = MFA
    EVNTS[NEW + 1] = ATRIB[0]
    EVNTS[NEW + 2] = ATRIB[1]
    NUMINQ = NUMINQ + 1

    # re-define pointer of first available (i.e. empty) entry (position)
    MFA = int(EVNTS[MFA])

    if IPOINT > -1:  # event list 1 contains entries, synchronize
        j = IPOINT

        # new entry goes into middle of event list
        if ATRIB[0] > EVNTS[j + 1]:
            while ATRIB[0] > EVNTS[j + 1]:
                K = j
                j = int(EVNTS[j])
                if j == -1:  # new entry becomes last in event list
                    EVNTS[K] = NEW
                    EVNTS[NEW] = -1
                    return NUMINQ, MFA, IPOINT
            # file into middle - set successor pointer.
            EVNTS[NEW] = j
            # set predecessor's successor pointer
            EVNTS[K] = NEW
            return NUMINQ, MFA, IPOINT
        else:
            # new entry becomes first entry
            # reset first pointer and define successor
            IPOINT = NEW
            EVNTS[NEW] = j
            return NUMINQ, MFA, IPOINT
    else:  # event list is empty, set first pointer to new entry, successor to -1
        IPOINT = NEW
        EVNTS[NEW] = -1
        return NUMINQ, MFA, IPOINT


# def filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS):
#     """
#     Append a new event into the event list, maintain chronological order and update
#     corresponding pointers

#     :param int MFA: pointer of the first available (i.e. empty) entry in the event list
#     :param numpy.ndarray ATRIB: events attribute vector of length 2
#                                 ATRIB[0] -- global simulation clock (in unit: hour)
#                                 ATRIB[1] -- int, simulation type
#                                  0: hourly
#                                  1: weekly
#                                  2: quarterly
#                                  3: yearly
#     :param int NUMINQ: up-to-date total number of event entries (inquires)
#     :param int IPOINT: pointer of the first (already/previously stored) entry in the
#         event list, defaults to -1 if the list is empty
#     :param numpy.ndarray EVNTS: 1D array of events
#     :return: (*tuple*) -- updated NUMINQ, MFA and IPOINT

#     .. note:: EVNTS is modified in place
#     """

#     NUMINQ += 1
#     EVNTS[MFA + 1 : MFA + 3] = ATRIB
#     time_rank = EVNTS[: NUMINQ * 4][1::4].argsort().argsort()
#     # the new event is the first entry in chronological order
#     if time_rank[-1] == 0:
#         EVNTS[MFA] = IPOINT
#         IPOINT = MFA
#     # the new event is the last entry in chronological order
#     elif time_rank[-1] == NUMINQ - 1:
#         EVNTS[MFA] = -1
#         EVNTS[np.where(time_rank == NUMINQ - 2)[0][0] * 4] = MFA
#     # the new event is one of the middle entries in chronological order
#     else:
#         EVNTS[MFA] = np.where(time_rank == time_rank[-1] + 1)[0][0] * 4
#         EVNTS[np.where(time_rank == time_rank[-1] - 1)[0][0] * 4] = MFA
#     MFA += 4

#     return NUMINQ, MFA, IPOINT
