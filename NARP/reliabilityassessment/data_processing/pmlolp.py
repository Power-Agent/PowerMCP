import numpy as np

from reliabilityassessment.data_processing.gsm import gsm


def pmlolp(CAPLOS, RD, NGU):
    """
    Computes the capacity outage probability table
    (for computing the 'M' factor used in function 'pmsc')

    Its high-level idea and illustration can be partially found in these slides:
    https://www.dropbox.com/s/krcse3mjuh97i88/module_6-1.pdf?dl=0

    :param numpy.ndarray CAPLOS: 1D array of assumed capacity loss of each gen unit
    :param numpy.ndarray RD: 2D array of mixed information of each gen unit in the
        specific area with shape (NUNITS, 3):
        RD(I,0): exact prob. of the I-th gen unit at its derated capacity
        RD(I,1): exact prob. of the I-th gen unit in total loss (i.e., zero MW)
        RD(I,2): the derated capacity (MW) of the I-th gen unit
        I is the internal ordering of the specific area.
    :param int NGU: total number of gen units in the specific area.
    :return: (*tuple*) -- a tuple of arrays (NGS, KA, PA):
        NGS: int, the total number of generation states after adding a specific gen unit
        KA: 1D array CUT-OFF capacity in the CAP-outage-table
        PA: 1D array CUT-OFF probability in the CAP-outage-table
    """

    INC = 10
    XINC = 5.5

    # (INGS) 5000 : the possible maximum total number of system generation states
    KA = np.zeros(5000)
    PA = np.zeros(5000)

    PA[0] = 1.0
    NGS = 1

    # add units to capacity outage probability table
    for NT in range(NGU):
        # update the system capacity up to this unit
        KT = int(CAPLOS[NT] + XINC)
        KT -= KT % INC

        # compute the derating and round off to 'INC''
        KP = int(KT * RD[NT, 2] + XINC)
        KP -= KP % INC

        P2, P3 = RD[NT, :2]
        P1 = 1 - P2 - P3

        # IRAT = P1 * 10**6  (might go back to this logic)
        # if IRAT != 0:      (might go back to this logic)
        if P1 > 1e-6:
            NGS = gsm(NGS, KT, KP, P1, P2, P3, PA, KA)

    # return when all units have been added
    return NGS, KA, PA
