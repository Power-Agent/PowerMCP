from reliabilityassessment.data_processing.xporta import xporta


def xports(JENT, INTCH, HRLOAD):
    """
    Remove power interchanges in contracts from hourly load for each area

    :param numpy.ndarray JENT: 2D array of contract number with shape (NOAREA, NOAREA)
        the (i,j)-th element specifies the contract number between area-i and area-j.
    :param numpy.ndarray INTCH: 2D array of the contract content with shape
        (total number of contracts, 365). (``JENT[i,j]``, k)-th element means the
        contracted power (MW) on the kth day from area-i to area-j.
    :param numpy.ndarray HRLOAD: 2D array of hourly load (MW) with shape (NOAREA, 8760)

    .. note:: All input arrays are modified in-place;
              Contracts always specify daily power transfer from high-indexed area
              to low-indexed area.
    """
    # Undo operations in function `xporta` simply by passing reversed contracts instead
    xporta(JENT, -INTCH, HRLOAD)
