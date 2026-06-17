def findld(NFACT, JHOUR, HRLOAD, FCTERR):
    """
    Determine the load needs of each area under the specific load forecast error factor

    :param: int NFACT: the index of the forecast error factor to be used
    :param: int JHOUR: the hour index in the annual load profile
    :param: numpy.ndarray HRLOAD: 2D array with shape (NOAREA, 8760), the hourly
        annual load profile
    :param: numpy.ndarray FCTERR: 2D array with shape shape (NOAREA, 5), the load
        forecast error factors
    :return: (*numpy.ndarray*) -- 1D array with shape (NOAREA, ), the capacity required
        for each area at the hour indexed by JOUHR, i.e. CAPREQ(J) passed to
        transmission module

     .. note:: in the original Fortran code, CAPREQ is annotated as "LOAD IN AREA J"
    """
    return HRLOAD[:, JHOUR] * FCTERR[:, NFACT]
