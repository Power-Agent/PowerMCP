from reliabilityassessment.monte_carlo.cvchk import cvchk


def test_cvchk_new():
    # ---- example test case 1 from real run ------
    CLOCK = 8760.0
    FINISH = 87591240.0  # i.e. 9999 * 8760
    SUM = 0.0
    XLAST = 0.0
    SSQ = 0.0
    IYEAR = 1
    CVTEST = 0.025
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 0
    assert SSQ == 0.0
    assert XLAST == 0.0

    # ---- example test case 2 from real run ------
    CLOCK = 43800.0
    FINISH = 87591240.0  # i.e. 9999 * 8760
    SUM = 1.0
    XLAST = 1.0
    SSQ = 1.0
    IYEAR = 5
    CVTEST = 0.025
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 0
    assert SSQ == 1.0
    assert XLAST == 1.0

    # ---- example test case 3 from real run ------
    CLOCK = 52569.0
    FINISH = 87591240.0  # i.e. 9999 * 8760
    SUM = 2.0
    XLAST = 1.0
    SSQ = 1.0
    IYEAR = 6
    CVTEST = 0.025
    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    assert RFLAG == 0
    assert SSQ == 2.0
    assert XLAST == 2.0
