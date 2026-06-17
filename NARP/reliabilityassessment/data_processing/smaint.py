import numpy as np

from reliabilityassessment.data_processing.pmsc import pmsc


def smaint(
    NOAREA,
    ID,
    ITAB,
    RATES,
    PROBG,
    DERATE,
    PKLOAD,
    WPEAK,
    IREPM,
    MINRAN,
    MAXRAN,
    INHBT1,
    INHBT2,
    NAMU,
    NUMP,
):
    """
    Obtain the (gen unit) maintenance schedule table ('JPLOUT') for each area

    :param int NOAREA: total number of areas
    :param numpy.ndarray ID:shape (NUNITS, 8)
                         ID(I,K), K=0: unit number (0-based)
                                  K=1: plant number (0-based)
                                  K=2: area of location (0-based)
                                  K=3: starting week of first planned outage (0-based)
                                  K=4: duration of first planned outage in weeks
                                  K=5: starting week of second planned outage (0-based)
                                  K=6: duration of second planned outage in weeks
                                  K=7: 1 if maintenance is pre-scheduled;
                                       0 if set automatically by the program
    :param int ITAB: index number of printed tables in the final output file
    :param numpy.ndarray RATES: original rating data (MW) of each unit for four seasons
        with shape (NUNITS, 4)
    :param numpy.ndarray PROBG: 2D array of accumulated probability for each capacity
        tier of each unit
    :param numpy.ndarray DERATE: array of the derated capacity of each unit
    :param numpy.ndarray PKLOAD: array of the user-defined annual peak of each area.
    :param numpy.ndarray WPEAK: 2D array, weekly peak load amount (MW)
        1st dim: areaIdx, 2nd dim: weekIdx
    :param int IREPM: indicator of printing maintenance result (if exists) or not
    :param int MINRAN: beginning week of the outage window
    :param int MAXRAN: ending week of the outage window
    :param int INHBT1: beginning week of the forbidden period.
    :param int INHBT2: ending week of the forbidden period.
    :param list NAMU: list of strings for generator unit name
    :param list NUMP: list of strings for generator plant name
    :return: (*tuple*) -- JPLOUT: table of planned outages of units, with shape (52,
                                  NUINTS+1) 1-dim: week index; 2-dim: total number
                                  of gen units scheduled for maintenance in the
                                  corresponding week followed by a sequence of 0-based
                                  generator unit numbers
                          ITAB: updated index number of printed tables

    .. note:: ID is modified in place
    """

    NUNITS = ID.shape[0]
    for areaIdx in range(NOAREA):
        # automatic scheduling of planned maintenance
        # for the specified area here; pmsc will update array ID
        ITAB = pmsc(
            areaIdx,
            ID,
            ITAB,
            RATES,
            PROBG,
            DERATE,
            PKLOAD,
            WPEAK,
            IREPM,
            MINRAN,
            MAXRAN,
            INHBT1,
            INHBT2,
            NAMU,
            NUMP,
        )

    JPLOUT = (-1) * np.ones((52, 1 + NUNITS), dtype=int)
    JPLOUT[:, 0] = 0

    for i in range(NUNITS):
        for wi in {3, 5}:
            if ID[i, wi] != -1:
                j1 = ID[i, wi]
                # the index of last week of a simulation year is 51
                j2 = min(51, j1 + ID[i, wi + 1])
                # increase total number of units under maintenance for the weeks
                JPLOUT[j1:j2, 0] += 1
                JPLOUT[np.arange(j1, j2), JPLOUT[j1:j2, 0]] = int(ID[i, 0])

    return JPLOUT, ITAB
