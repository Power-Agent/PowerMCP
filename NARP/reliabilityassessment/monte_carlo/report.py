import numpy as np


def report(
    IYEAR,
    ITAB,
    INDX,
    SUSTAT,
    DPLOLE,
    EUES,
    HLOLE,
    LSTEP,
    NAMA,
    NFCST,
    SGNGHA,
    SGNGHP,
    SGNGPA,
    SGNGPP,
    SGNSHA,
    SGNSHP,
    SGNSPA,
    SGNSPP,
    SGNTHA,
    SGNTHP,
    SGNTPA,
    SGNTPP,
    SOLGHA,
    SOLGHP,
    SOLGPA,
    SOLGPP,
    SOLSHA,
    SOLSHP,
    SOLSPA,
    SOLSPP,
    SOLTHA,
    SOLTHP,
    SOLTPA,
    SOLTPP,
    SWLGHA,
    SWLGHP,
    SWLGPA,
    SWLGPP,
    SWLSHA,
    SWLSHP,
    SWLSPA,
    SWLSPP,
    SWLTHA,
    SWLTHP,
    SWLTPA,
    SWLTPP,
    SWNGHA,
    SWNGHP,
    SWNGPA,
    SWNGPP,
    SWNSHA,
    SWNSHP,
    SWNSPA,
    SWNSPP,
    SWNTHA,
    SWNTHP,
    SWNTPA,
    SWNTPP,
    XNEWA,
    XNEWP,
):
    """
    Post-process the simulation results and write to the final output file

    .. note:: 1. The inputs and outputs are massive scalars, 1D and 2D numpy.ndarrays.
             For descriptions of input and output variables, please refer to `variable descriptions.xlsx.`
             in the project Dropbox folder: https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0
             2. Modify array SUSTAT in-place
             3. For arrays LOLGHA to WOLTPP:
                    please refer to the following naming rules for those
                    6-digit statistic-related quantities:
                    The first three digits identify the type of statistic
                        LOL means this is an annual loss of load statistic of some type
                        MGN means this is the annual sum of negative margins (EUE)
                        SOL means this is the cumulative sum, all years, LOLE
                        SNG means this is the cumulative sum, all years, EUE
                    The fourth digit identifies the cause of the outage
                        T is transmission
                        G is generation
                        S is sum statistics of T & G
                     The fifth digit indicates whether the stat is hourly or peak
                         H is for hourly stats
                         P is for peak stats
                     The sixth digit is for area or pool
                         A is area
                         P is pool
                    Examples:
                        SGNSPA  is the cumulative sum, EUE, total of T & G, peak, area
                        LOLTHP  is the annual loss of load, transmission, hourly, pool
    """

    XG, XT, XS, XA, FH, SH = "GC", "TC", "GT", "AV", "ERCO", "T"

    f = open("output.txt", "a")

    ITAB += 1
    f.write("\n                        TABLE %d\n" % (ITAB))

    f.write("\n\t\t\t FINAL RESULTS AFTER %d REPLICATIONS \n" % (IYEAR))

    if INDX != 1:
        f.write(
            "\n  AREA FORECAST    HOURLY STATISTICS            PEAK STATISTICS           REMARKS"
        )
        f.write("\n  NO   NO        HLOLE    XLOL       EUE       LOLE      XLOL")
        f.write("\n                (HRS/YR)  (MW)      (MWH)     (DAYS/YR)  (MW)")
    else:
        f.write("\n  AREA FORECAST    PEAK STATISTICS           REMARKS")
        f.write("\n  NO   NO        LOLE       XLOL")
        f.write("\n                   (DAYS/YR)   MW")

    XYEAR = IYEAR
    NOAREA = SUSTAT.shape[0] - 1
    SSQA = np.zeros((NOAREA, 3))
    for J in range(NOAREA):
        if NFCST != 1:
            for N in range(NFCST):
                if SOLGHA[J, N] > 0:
                    XMGN = SGNGHA[J, N] / SOLGHA[J, N]
                else:
                    XMGN = 0.0

                XLOL = SOLGHA[J, N] / XYEAR
                EUE = SGNGHA[J, N] / XYEAR
                if SOLGPA[J, N] > 0:
                    XMGNP = SGNGPA[J, N] / SOLGPA[J, N]
                else:
                    XMGNP = 0.0

                XLOLP = SOLGPA[J, N] / XYEAR
                # EUEP = SGNGPA[J,N]/XYEAR # may have future usage
                if INDX != 1:
                    f.write(
                        "\n  %2d  %2d     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                        % (J + 1, N + 1, XLOL, XMGN, EUE, XLOLP, XMGNP, XG)
                    )
                else:
                    f.write(
                        "\n  %2d  %2d         %8.2f  %8.2f            %s"
                        % (J + 1, N + 1, XLOLP, XMGNP, XG)
                    )

                if SOLTHA[J, N] > 0:
                    XMGN = SGNTHA[J, N] / SOLTHA[J, N]
                else:
                    XMGN = 0.0

                XLOL = SOLTHA[J, N] / XYEAR
                EUE = SGNTHA[J, N] / XYEAR
                if SOLTPA[J, N] > 0:
                    XMGNP = SGNTPA[J, N] / SOLTPA[J, N]
                else:
                    XMGNP = 0.0

                XLOLP = SOLTPA[J, N] / XYEAR
                # EUEP = SGNTPA[J,N]/XYEAR # may have future usage
                if INDX != 1:
                    f.write(
                        "\n  %2d  %2d     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                        % (J + 1, N + 1, XLOL, XMGN, EUE, XLOLP, XMGNP, XT)
                    )
                else:
                    f.write(
                        "\n  %2d  %2d         %8.2f  %8.2f            %s"
                        % (J + 1, N + 1, XLOLP, XMGNP, XT)
                    )

                if SOLSHA[J, N] > 0.0:
                    XMGN = SGNSHA[J, N] / SOLSHA[J, N]
                else:
                    XMGN = 0.0

                XLOL = SOLSHA[J, N] / XYEAR
                EUE = SGNSHA[J, N] / XYEAR

                if SOLSPA[J, N] > 0:
                    XMGNP = SGNSPA[J, N] / SOLSPA[J, N]
                else:
                    XMGNP = 0.0

                XLOLP = SOLSPA[J, N] / XYEAR
                # EUEP = SGNSPA[J,N]/XYEAR # may have future usage
                if INDX != 1:
                    f.write(
                        "\n  %2d  %2d     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                        % (J + 1, N + 1, XLOL, XMGN, EUE, XLOLP, XMGNP, XS)
                    )
                else:
                    f.write(
                        "\n  %2d  %2d         %8.2f  %8.2f            %s"
                        % (J + 1, N + 1, XLOLP, XMGNP, XS)
                    )

        if SWLGHA[J] > 0.0:
            XMGN = SWNGHA[J] / SWLGHA[J]
        else:
            XMGN = 0.0

        XLOL = SWLGHA[J] / XYEAR
        EUE = SWNGHA[J] / XYEAR

        if SWLGPA[J] > 0.0:
            XMGNP = SWNGPA[J] / SWLGPA[J]
        else:
            XMGNP = 0.0

        XLOLP = SWLGPA[J] / XYEAR
        # EUEP = SWNGPA[J]/XYEAR # may have future usage
        if INDX != 1:
            f.write(
                "\n  %2d  %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                % (J + 1, XA, XLOL, XMGN, EUE, XLOLP, XMGNP, XG)
            )
        else:
            f.write(
                "\n  %2d  %s         %8.2f  %8.2f            %s"
                % (J + 1, XA, XLOLP, XMGNP, XG)
            )

        if SWLTHA[J] > 0.0:
            XMGN = SWNTHA[J] / SWLTHA[J]
        else:
            XMGN = 0.0

        XLOL = SWLTHA[J] / XYEAR
        EUE = SWNTHA[J] / XYEAR

        if SWLTPA[J] > 0.0:
            XMGNP = SWNTPA[J] / SWLTPA[J]
        else:
            XMGNP = 0.0

        XLOLP = SWLTPA[J] / XYEAR
        # EUEP = SWNTPA[J]/XYEAR # may have future usage

        if INDX != 1:
            f.write(
                "\n  %2d  %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                % (J + 1, XA, XLOL, XMGN, EUE, XLOLP, XMGNP, XT)
            )
        else:
            f.write(
                "\n  %2d  %s         %8.2f  %8.2f            %s"
                % (J + 1, XA, XLOLP, XMGNP, XT)
            )

        if SWLSHA[J] > 0.0:
            XMGN = SWNSHA[J] / SWLSHA[J]
        else:
            XMGN = 0.0

        XLOL = SWLSHA[J] / XYEAR
        SSQA[J, 0] = XNEWA[J, 0] / XYEAR - XLOL**2
        EUE = SWNSHA[J] / XYEAR
        SSQA[J, 1] = XNEWA[J, 1] / XYEAR - EUE**2

        if SWLSPA[J] > 0.0:
            XMGNP = SWNSPA[J] / SWLSPA[J]
        else:
            XMGNP = 0.0

        XLOLP = SWLSPA[J] / XYEAR
        SSQA[J, 2] = XNEWA[J, 2] / XYEAR - XLOLP**2
        # EUEP = SWNSPA[J]/XYEAR # may have future usage

        if INDX != 1:
            f.write(
                "\n  %2d  %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                % (J + 1, XA, XLOL, XMGN, EUE, XLOLP, XMGNP, XS)
            )
        else:
            f.write(
                "\n  %2d  %s         %8.2f  %8.2f            %s"
                % (J + 1, XA, XLOLP, XMGNP, XS)
            )

        f.write("\n")

        SUSTAT[J, 3] = XLOL
        SUSTAT[J, 4] = XLOLP
        SUSTAT[J, 5] = EUE

    # Then, for Pool Statistics:
    f.write("\n\n           POOL STATISTICS \n")
    if NFCST != 1:
        for N in range(NFCST):
            if SOLGHP[N] > 0:
                XMGN = SGNGHP[N] / SOLGHP[N]
            else:
                XMGN = 0.0
            XLOL = SOLGHP[N] / XYEAR
            EUE = SGNGHP[N] / XYEAR
            if SOLGPP[N] > 0:
                XMGNP = SGNGPP[N] / SOLGPP[N]
            else:
                XMGNP = 0.0

            XLOLP = SOLGPP[N] / XYEAR
            # EUEP =  0.0 # may have future usage

            if INDX != 1:
                f.write(
                    "\n      %2d     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                    % (N + 1, XLOL, XMGN, EUE, XLOLP, XMGNP, XG)
                )
            else:
                f.write(
                    "\n      %2d         %8.2f  %8.2f            %s"
                    % (N + 1, XLOLP, XMGNP, XG)
                )

            if SOLTHP[N] > 0:
                XMGN = SGNTHP[N] / SOLTHP[N]
            else:
                XMGN = 0.0

            XLOL = SOLTHP[N] / XYEAR
            EUE = SGNTHP[N] / XYEAR

            if SOLTPP[N] > 0:
                XMGNP = SGNTPP[N] / SOLTPP[N]
            else:
                XMGNP = 0.0

            XLOLP = SOLTPP[N] / XYEAR
            # EUEP =  0.0 # may have future usage

            if INDX != 1:
                f.write(
                    "\n      %2d     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                    % (N + 1, XLOL, XMGN, EUE, XLOLP, XMGNP, XT)
                )
            else:
                f.write(
                    "\n      %2d         %8.2f  %8.2f            %s"
                    % (N + 1, XLOLP, XMGNP, XT)
                )

            if SOLSHP[N] > 0:
                XMGN = SGNSHP[N] / SOLSHP[N]
            else:
                XMGN = 0.0

            XLOL = SOLSHP[N] / XYEAR
            EUE = SGNSHP[N] / XYEAR

            if SOLSPP[N] > 0:
                XMGNP = SGNSPP[N] / SOLSPP[N]
            else:
                XMGNP = 0.0

            XLOLP = SOLSPP[N] / XYEAR
            # EUEP = 0.0  # may have future usage

            if INDX != 1:
                f.write(
                    "\n      %2d     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                    % (N + 1, XLOL, XMGN, EUE, XLOLP, XMGNP, XS)
                )
            else:
                f.write(
                    "\n      %2d         %8.2f  %8.2f            %s"
                    % (N + 1, XLOLP, XMGNP, XS)
                )

    if SWLGHP > 0.0:
        XMGN = SWNGHP / SWLGHP
    else:
        XMGN = 0.0

    XLOL = SWLGHP / XYEAR
    EUE = SWNGHP / XYEAR

    if SWLGPP > 0.0:
        XMGNP = SWNGPP / SWLGPP
    else:
        XMGNP = 0.0

    XLOLP = SWLGPP / XYEAR
    # EUEP = 0.0 # may have future usage

    if INDX != 1:
        f.write(
            "\n      %s     %7.3f  %8.2f   %7.0f     %7.3f  %8.2f            %s"
            % (XA, XLOL, XMGN, EUE, XLOLP, XMGNP, XG)
        )
    else:
        f.write(
            "\n      %s         %8.2f  %8.2f            %s" % (XA, XLOLP, XMGNP, XG)
        )

    if SWLTHP > 0.0:
        XMGN = SWNTHP / SWLTHP
    else:
        XMGN = 0.0

    XLOL = SWLTHP / XYEAR
    EUE = SWNTHP / XYEAR

    if SWLTPP > 0:
        XMGNP = SWNTPP / SWLTPP
    else:
        XMGNP = 0.0

    XLOLP = SWLTPP / XYEAR
    # EUEP = 0.0 # may have future usage

    if INDX != 1:
        f.write(
            "\n      %s     %7.3f  %8.2f   %7.0f     %7.3f  %8.2f            %s"
            % (XA, XLOL, XMGN, EUE, XLOLP, XMGNP, XT)
        )
    else:
        f.write(
            "\n      %s         %8.2f  %8.2f            %s" % (XA, XLOLP, XMGNP, XT)
        )

    if SWLSHP > 0.0:
        XMGN = SWNSHP / SWLSHP
    else:
        XMGN = 0.0

    XLOL = SWLSHP / XYEAR
    SSQP = np.zeros((3,))
    SSQP[0] = XNEWP[0] / XYEAR - XLOL**2
    EUE = SWNSHP / XYEAR
    SSQP[1] = XNEWP[1] / XYEAR - EUE**2

    if SWLSPP > 0.0:
        XMGNP = SWNSPP / SWLSPP
    else:
        XMGNP = 0.0

    XLOLP = SWLSPP / XYEAR
    SSQP[2] = XNEWP[2] / XYEAR - XLOLP**2
    # EUEP = 0.0 # may have future usage

    if INDX != 1:
        f.write(
            "\n      %s     %7.3f  %8.2f   %7.0f     %7.3f  %8.2f            %s"
            % (XA, XLOL, XMGN, EUE, XLOLP, XMGNP, XS)
        )
    else:
        f.write(
            "\n      %s         %8.2f  %8.2f            %s" % (XA, XLOLP, XMGNP, XS)
        )

    for IAR in range(NOAREA):
        for J in range(3):
            SSQA[IAR, J] = (SSQA[IAR, J] / XYEAR) ** 0.5

    for J in range(3):
        SSQP[J] = (SSQP[J] / XYEAR) ** 0.5

    SUSTAT[NOAREA, 3] = XLOL
    SUSTAT[NOAREA, 4] = XLOLP
    SUSTAT[NOAREA, 5] = EUE

    ITAB += 1
    f.write("\n\n\t\t\t\t                            TABLE %4d \n" % (ITAB))
    f.write("\n \t\t\t\t\t\t\t\t\t\t SUMMARY OF RESULTS \n\n")

    if INDX != 1:
        f.write(
            "          AREA       PEAK        INSTALLED   AREA           HLOLE                   EUE                LOLE\n"
        )
        f.write(
            "                                                       ----------------        ----------------     ----------------\n"
        )
        f.write(
            "                                 CAPACITY    PCT RES   MAGN      PCT SD        MAGN      PCT SD     MAGN      PCT SD"
        )

    else:
        f.write("          AREA       PEAK        INSTALLED   AREA   ")
        f.write(
            "                                                       ----------------\n"
        )
        f.write(
            "                                 CAPACITY    PCT RES     MAGN       PCT SD"
        )

    for i in range(NOAREA):
        if SUSTAT[i, 0] > 0:
            SUSTAT[i, 2] = (SUSTAT[i, 1] - SUSTAT[i, 0]) / SUSTAT[i, 0] * 100

        if INDX != 1:
            SSHL = 0.0
            SSEU = 0.0
            SSLO = 0.0
            if SUSTAT[i, 3] > 0:
                SSHL = SSQA[i, 0] / SUSTAT[i, 3] * 100
            if SUSTAT[i, 5] > 0:
                SSEU = SSQA[i, 1] / SUSTAT[i, 5] * 100
            if SUSTAT[i, 4] > 0:
                SSLO = SSQA[i, 2] / SUSTAT[i, 4] * 100

            f.write(
                "\n          %s     %7.0f     %8.0f     %5.1f     %7.3f    %7.3f    %8.0f   %8.0f   %7.3f   %7.3f"
                % (
                    NAMA[i],
                    SUSTAT[i, 0],
                    SUSTAT[i, 1],
                    SUSTAT[i, 2],
                    SUSTAT[i, 3],
                    SSHL,
                    SUSTAT[i, 5],
                    SSEU,
                    SUSTAT[i, 4],
                    SSLO,
                )
            )
        else:
            SSLO = 0
            if SUSTAT[i, 4] > 0:
                SSLO = SSQA[i, 2] / SUSTAT[i, 4] * 100
            f.write(
                "\n          %s     %7.0f     %8.0f     %5.1f     %7.3f   %7.3f"
                % (
                    NAMA[i],
                    SUSTAT[i, 0],
                    SUSTAT[i, 1],
                    SUSTAT[i, 2],
                    SUSTAT[i, 4],
                    SSLO,
                )
            )

        NO1 = NOAREA
        SUSTAT[NO1, 0] += SUSTAT[i, 0]
        SUSTAT[NO1, 1] += SUSTAT[i, 1]

    if SUSTAT[i, 0] > 0:
        SUSTAT[NO1, 2] = (SUSTAT[i, 1] - SUSTAT[i, 0]) / SUSTAT[i, 0] * 100

    if INDX != 1:
        SSHL = 0.0
        SSEU = 0.0
        SSLO = 0.0
        if SUSTAT[NO1, 3] > 0:
            SSHL = SSQP[0] / SUSTAT[NO1, 3] * 100.0
        if SUSTAT[NO1, 5] > 0:
            SSEU = SSQP[1] / SUSTAT[NO1, 5] * 100.0
        if SUSTAT[NO1, 4] > 0:
            SSLO = SSQP[2] / SUSTAT[NO1, 4] * 100.0
        f.write(
            "\n\n          %s%s    %7.0f     %8.0f     %5.1f     %7.3f    %7.3f    %8.0f   %8.0f   %7.3f   %7.3f"
            % (
                FH,
                SH,
                SUSTAT[NO1, 0],
                SUSTAT[NO1, 1],
                SUSTAT[NO1, 2],
                SUSTAT[NO1, 3],
                SSHL,
                SUSTAT[NO1, 5],
                SSEU,
                SUSTAT[NO1, 4],
                SSLO,
            )
        )
    else:
        SSLO = 0.0
        if SUSTAT[NO1, 4] > 0:
            SSLO = SSQP[2] / SUSTAT[NO1, 4] * 100.0
        f.write(
            "\n\n          %s%s    %7.0f     %8.0f     %5.1f     %7.3f    %7.3f"
            % (
                FH,
                SH,
                SUSTAT[NO1, 0],
                SUSTAT[NO1, 1],
                SUSTAT[NO1, 2],
                SUSTAT[NO1, 4],
                SSLO,
            )
        )

    SUMHL, SUMDP, SUMEUE = np.zeros(NOAREA), np.zeros(NOAREA), np.zeros(NOAREA)
    for j in range(22):
        for i in range(NOAREA):
            SUMHL[i] += HLOLE[i, j]
            SUMDP[i] += DPLOLE[i, j]
            SUMEUE[i] += EUES[i, j]

    PHL, PDP, PEUE = (
        np.zeros((NOAREA, 22)),
        np.zeros((NOAREA, 22)),
        np.zeros((NOAREA, 22)),
    )
    for j in range(22):
        for i in range(NOAREA):
            PHL[i, j] = HLOLE[i, j] / SUMHL[i]
            PDP[i, j] = DPLOLE[i, j] / SUMHL[i]
            PEUE[i, j] = EUES[i, j] / SUMEUE[i]

    for i in range(NOAREA):
        ITAB += 1
        f.write(
            "\n\n\t\t\t\t\t\t\t\t\t\t\t TABLE %5d\n\n"
            "\t\t\t\t\t\t\t\t PROBABILITY DISTRIBUTIONS FOR AREA %3d\n\n\n"
            "\t\t DAILY PEAK LOLES PER YEAR \t\t\t HOURLY LOLES PER YEAR \t\t\t\t ANNUAL UNSERVED ENERGY (MWH)\n\n"
            "NUMBER\t OBSERVATIONS\t PROBABILITY"
            "\t OBSERVATIONS\t PROBABILITY\t"
            "LIMIT (MWH)\t OBSERVATIONS\t PROBABILITY \n" % (ITAB, i + 1)
        )
        for j in range(22):
            LIMIT = j * LSTEP
            f.write(
                "%4d\t\t%6.0f\t\t\t%5.3f\t\t\t%6.0f\t\t\t%5.3f\t\t\t%6d\t\t%6.0f\t\t\t %6.4f\n"
                % (
                    j,
                    DPLOLE[i, j],
                    PDP[i, j],
                    HLOLE[i, j],
                    PHL[i, j],
                    LIMIT,
                    EUES[i, j],
                    PEUE[i, j],
                )
            )

    f.close()  # close "output" file
    return ITAB
