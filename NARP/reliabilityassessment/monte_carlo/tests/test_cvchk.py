from reliabilityassessment.monte_carlo.cvchk import cvchk


def test_cvchk():
    CLOCK = 12.5
    FINISH = 9999 * 8760
    SUM = 3.0
    XLAST = 2.0
    SSQ = 3.0
    IYEAR = 4
    CVTEST = 0.05
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 0
    assert SSQ == 4.0
    assert XLAST == 3.0

    CLOCK = 9999 * 8760 + 1
    FINISH = 9999 * 8760
    SUM = 3.0
    XLAST = 2.0
    SSQ = 3.0
    IYEAR = 4
    CVTEST = 0.05
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 1
    assert SSQ == 4.0
    assert XLAST == 3.0

    CLOCK = 12.5
    FINISH = 9999 * 8760
    SUM = 3.0
    XLAST = 2.0
    SSQ = 3.0
    IYEAR = 5
    CVTEST = 0.05
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 0
    assert SSQ == 4.0
    assert XLAST == 3.0

    CLOCK = 12.5
    FINISH = 9999 * 8760
    SUM = 1.0
    XLAST = 1.0
    SSQ = 0.3
    IYEAR = 5
    CVTEST = 0.5
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 1
    assert SSQ == 0.3
    assert XLAST == 1.0
