import numpy as np

from reliabilityassessment.monte_carlo.cvchk import cvchk
from reliabilityassessment.monte_carlo.filem import filem
from reliabilityassessment.monte_carlo.intm import intm
from reliabilityassessment.monte_carlo.report import report


def year(
    ATRIB,
    CLOCK,
    CVTEST,
    DPLOLE,
    EUES,
    EVNTS,
    FINISH,
    HLOLE,
    IPOINT,
    MFA,
    NUMINQ,
    RFLAG,
    LSFLG,
    NAMA,
    SSQ,
    SUSTAT,
    XLAST,
    BB,
    LT,
    ZB,
    INTV,
    INTVT,
    IOJ,
    KVLOC,
    KVSTAT,
    KVTYPE,
    KVWHEN,
    KWHERE,
    LSTEP,
    NFCST,
    NORR,
    INDX,
    ITAB,
    LOLGHA,
    LOLGHP,
    LOLGPA,
    LOLGPP,
    LOLTHA,
    LOLTHP,
    LOLTPA,
    LOLTPP,
    MGNGHA,
    MGNGHP,
    MGNGPA,
    MGNGPP,
    MGNTHA,
    MGNTHP,
    MGNTPA,
    MGNTPP,
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
    Update and summarize all reliability statistics when this 'simulation-year' event is triggered

    .. note:: The inputs and outputs are massive scalars, 1D and 2D numpy.ndarrays.
             For descriptions of input and output variables, please refer to `variable descriptions.xlsx.`
             in the project Dropbox folder: https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

             For arrays LOLGHA to WOLTPP:
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
                        S is sum of t & g
                     The fifth digit indicates whether the stat is hourly or peak
                         H is for hourly stats
                         P is for peak stats
                     The sixth digit is for area or pool
                         A is area
                         P is pool

                    Examples	:
                        SGNSPA  is cumulative sum, EUE, total of t&g, peak, area
                        LOLTHP  is annual loss of load, transmission, hourly, pool
    """

    XG, XT, XS, XA = "GC", "TC", "GT", "AV"

    # XPROB = np.zeros((NFCST)); NFCST is 5
    # DATA XPROB /.0668,.2417,.383,.2417,.0668/
    XPROB = np.array([0.0668, 0.2417, 0.383, 0.2417, 0.0668])

    if NFCST == 1:
        XPROB[0] = 1.0

    # Schedule event for next end of year
    ATRIB[0] = CLOCK + 8760
    ATRIB[1] = 4
    NUMINQ, MFA, IPOINT = filem(MFA, ATRIB, NUMINQ, IPOINT, EVNTS)

    IYEAR = int((CLOCK + 1) / 8760)
    NOAREA = EUES.shape[0]

    WGNGHP, WGNGPP, WGNSHP, WGNSPP, WGNTHP, WGNTPP = 6 * [0]
    WOLGHP, WOLGPP, WOLSHP, WOLSPP, WOLTHP, WOLTPP = 6 * [0]
    WGNGHA = np.zeros(NOAREA)
    WGNGPA = np.zeros(NOAREA)
    WGNSHA = np.zeros(NOAREA)
    WGNSPA = np.zeros(NOAREA)
    WGNTHA = np.zeros(NOAREA)
    WGNTPA = np.zeros(NOAREA)
    WOLGHA = np.zeros(NOAREA)
    WOLGPA = np.zeros(NOAREA)
    WOLSHA = np.zeros(NOAREA)
    WOLSPA = np.zeros(NOAREA)
    WOLTHA = np.zeros(NOAREA)
    WOLTPA = np.zeros(NOAREA)

    MGNSHA = np.zeros((NOAREA, NFCST), dtype=int)
    MGNSHP = np.zeros(NFCST, dtype=int)
    MGNSPA = np.zeros((NOAREA, NFCST), dtype=int)
    MGNSPP = np.zeros(NFCST, dtype=int)

    LOLSHA = np.zeros((NOAREA, NFCST), dtype=int)
    LOLSHP = np.zeros(NFCST, dtype=int)
    LOLSPA = np.zeros((NOAREA, NFCST), dtype=int)
    LOLSPP = np.zeros(NFCST, dtype=int)

    # Compute LOLES, sum for final report, take weighted avg
    # Area LOLE is sum of trans & gen LOLES
    LOLSHA[:, :NFCST] = LOLTHA[:, :NFCST] + LOLGHA[:, :NFCST]
    SOLSHA[:, :NFCST] += LOLSHA[:, :NFCST]  # Cumulative sum of hourly area LOLES
    SOLTHA[:, :NFCST] += LOLTHA[
        :, :NFCST
    ]  # Cumulative sum of hourly area LOLES assigned to transmission
    SOLGHA[:, :NFCST] += LOLGHA[:, :NFCST]
    WOLSHA += LOLSHA[:, :NFCST] @ XPROB[:NFCST]
    WOLGHA += LOLGHA[:, :NFCST] @ XPROB[:NFCST]
    WOLTHA += LOLTHA[:, :NFCST] @ XPROB[:NFCST]

    # Compute total magnitudes, sum for final report, take weighted avg
    MGNSHA[:, :NFCST] = MGNTHA[:, :NFCST] + MGNGHA[:, :NFCST]
    SGNSHA[:, :NFCST] += MGNSHA[:, :NFCST]
    SGNTHA[:, :NFCST] += MGNTHA[:, :NFCST]
    SGNGHA[:, :NFCST] += MGNGHA[:, :NFCST]
    WGNSHA += MGNSHA[:, :NFCST] @ XPROB[:NFCST]
    WGNGHA += MGNGHA[:, :NFCST] @ XPROB[:NFCST]
    WGNTHA += MGNTHA[:, :NFCST] @ XPROB[:NFCST]

    SWNGHA += WGNGHA
    SWNTHA += WGNTHA
    SWNSHA += WGNSHA
    SWLGHA += WOLGHA
    SWLTHA += WOLTHA
    SWLSHA += WOLSHA

    # Compute LOLES, sum for final report, take weighted avg
    LOLSPA[:, :NFCST] = LOLTPA[:, :NFCST] + LOLGPA[:, :NFCST]
    SOLSPA[:, :NFCST] += LOLSPA[:, :NFCST]
    SOLTPA[:, :NFCST] += LOLTPA[:, :NFCST]
    SOLGPA[:, :NFCST] += LOLGPA[:, :NFCST]
    WOLGPA += LOLGPA[:, :NFCST] @ XPROB[:NFCST]
    WOLTPA += LOLTPA[:, :NFCST] @ XPROB[:NFCST]
    WOLSPA += LOLSPA[:, :NFCST] @ XPROB[:NFCST]

    # Compute total magnitudes, sum for final report, take weighted avg
    MGNSPA[:, :NFCST] = MGNTPA[:, :NFCST] + MGNGPA[:, :NFCST]
    SGNSPA[:, :NFCST] += MGNSPA[:, :NFCST]
    SGNTPA[:, :NFCST] += MGNTPA[:, :NFCST]
    SGNGPA[:, :NFCST] += MGNGPA[:, :NFCST]
    WGNGPA += MGNGPA[:, :NFCST] @ XPROB[:NFCST]
    WGNTPA += MGNTPA[:, :NFCST] @ XPROB[:NFCST]
    WGNSPA += MGNSPA[:, :NFCST] @ XPROB[:NFCST]

    # POOL STATISTICS, TOTAL, CUMULATE, WEIGHTED AVERAGE
    SWNGPA += WGNGPA
    SWNTPA += WGNTPA
    SWNSPA += WGNSPA
    SWLGPA += WOLGPA
    SWLTPA += WOLTPA
    SWLSPA += WOLSPA

    NOERR = NORR
    for IAR in range(NOAREA):
        IPHOUR = min(22, LOLSHA[IAR, NOERR] + 1)
        IPDP = min(22, LOLSPA[IAR, NOERR] + 1)
        IPEUE = min(22, int(MGNSHA[IAR, NOERR] / LSTEP + 1))
        HLOLE[IAR, IPHOUR - 1] += 1.0
        DPLOLE[IAR, IPDP - 1] += 1.0
        EUES[IAR, IPEUE - 1] += 1.0

    # Compute LOLES, sum for final report, take weighted avg
    LOLSHP[:NFCST] = LOLTHP[:NFCST] + LOLGHP[:NFCST]
    SOLSHP[:NFCST] += LOLSHP[:NFCST]
    SOLTHP[:NFCST] += LOLTHP[:NFCST]
    SOLGHP[:NFCST] += LOLGHP[:NFCST]
    WOLGHP += LOLGHP[:NFCST] @ XPROB[:NFCST]
    WOLTHP += LOLTHP[:NFCST] @ XPROB[:NFCST]
    WOLSHP += LOLSHP[:NFCST] @ XPROB[:NFCST]

    # Compute total magnitudes, sum for final report, take weighted avg
    MGNSHP[:NFCST] = MGNTHP[:NFCST] + MGNGHP[:NFCST]
    SGNSHP[:NFCST] += MGNSHP[:NFCST]
    SGNTHP[:NFCST] += MGNTHP[:NFCST]
    SGNGHP[:NFCST] += MGNGHP[:NFCST]
    WGNGHP += MGNGHP[:NFCST] @ XPROB[:NFCST]
    WGNTHP += MGNTHP[:NFCST] @ XPROB[:NFCST]
    WGNSHP += MGNSHP[:NFCST] @ XPROB[:NFCST]

    SWNGHP += WGNGHP
    SWNTHP += WGNTHP
    SWNSHP += WGNSHP
    SWLGHP += WOLGHP
    SWLTHP += WOLTHP
    SWLSHP += WOLSHP

    # Compute LOLES, sum for final report, take weighted avg
    LOLSPP[:NFCST] = LOLTPP[:NFCST] + LOLGPP[:NFCST]
    SOLSPP[:NFCST] += LOLSPP[:NFCST]
    SOLTPP[:NFCST] += LOLTPP[:NFCST]
    SOLGPP[:NFCST] += LOLGPP[:NFCST]
    WOLGPP += LOLGPP[:NFCST] @ XPROB[:NFCST]
    WOLTPP += LOLTPP[:NFCST] @ XPROB[:NFCST]
    WOLSPP += LOLSPP[:NFCST] @ XPROB[:NFCST]

    # Compute total magnitudes, sum for final report, take weighted avg
    MGNSPP[:NFCST] = MGNTPP[:NFCST] + MGNGPP[:NFCST]
    SGNSPP[:NFCST] += MGNSPP[:NFCST]
    SGNTPP[:NFCST] += MGNTPP[:NFCST]
    SGNGPP[:NFCST] += MGNGPP[:NFCST]
    WGNGPP += MGNGPP[:NFCST] @ XPROB[:NFCST]
    WGNTPP += MGNTPP[:NFCST] @ XPROB[:NFCST]
    WGNSPP += MGNSPP[:NFCST] @ XPROB[:NFCST]

    SWNGPP += WGNGPP
    SWNTPP += WGNTPP
    SWNSPP += WGNSPP
    SWLGPP += WOLGPP
    SWLTPP += WOLTPP
    SWLSPP += WOLSPP

    XNEWA[:NOAREA, 0] += WOLSHA[:NOAREA] ** 2
    XNEWA[:NOAREA, 1] += WGNSHA[:NOAREA] ** 2
    XNEWA[:NOAREA, 2] += WOLSPA[:NOAREA] ** 2

    XNEWP[0] += WOLSHP**2
    XNEWP[1] += WGNSHP**2
    XNEWP[2] += WOLSPP**2

    # Printing part:
    # Print result of annual analysis and reset related intermediate quantities Tto 0
    f = open("output.txt", "a")  # can put earlier

    if IOJ != 0:
        f.write(" \n ")
        ITAB += 1
        f.write(" \n TABLE \n ")
        f.write(" \n RESULTS AFTER %d REPLICATIONS \n" % (IYEAR))

        if INDX != 1:  # maybe 0, need to check later
            f.write(
                " \n  AREA FORECAST    HOURLY STATISTICS     PEAK STATISTICS    REMARKS\n"
            )
            f.write(" \n NO   NO         HLOLE    XLOL     EUE       LOLE       XLOL\n")
            f.write(
                "\n                (HRS/YR)   (MW)      (MWH)     (DAYS/YR)  (MW)\n"
            )
        else:
            f.write("\n  AREA FORECAST    PEAK STATISTICS            REMARKS\n")
            f.write("\n  NO   NO          LOLE       XLOL\n")
            f.write("\n                   (DAYS/YR)   MW\n")

        for J in range(NOAREA):
            for N in range(NFCST):
                if LOLGHA[J, N] > 0:
                    XMGNA = (MGNGHA[J, N]) / (LOLGHA[J, N])
                else:
                    XMGNA = 0.0

                if LOLGPA[J, N] > 0:
                    XMGNP = (MGNGPA[J, N]) / (LOLGPA[J, N])
                else:
                    XMGNP = 0.0

                if INDX != 1:
                    f.write(
                        "\n  %2d  %2d    %4d    %8.2f  %8d     %4d     %8.2f            %s\n"
                        % (
                            J,
                            N,
                            LOLGHA[J, N],
                            XMGNA,
                            MGNGHA[J, N],
                            LOLGPA[J, N],
                            XMGNP,
                            XG,
                        )
                    )
                else:
                    f.write(
                        "\n  %2d  %2d         %8.2f  %8.2f            %s\n"
                        % (J, N, LOLGPA[J, N], XMGNP, XG)
                    )

                if LOLTHA[J, N] > 0:
                    XMGNA = (MGNTHA[J, N]) / (LOLTHA[J, N])
                else:
                    XMGNA = 0.0

                if LOLTPA[J, N] > 0:
                    XMGNP = (MGNTPA[J, N]) / (LOLTPA[J, N])
                else:
                    XMGNP = 0.0

                if INDX != 1:
                    f.write(
                        "\n  %2d  %2d    %4d    %8.2f  %8d     %4d     %8.2f            %s\n"
                        % (
                            J,
                            N,
                            LOLTHA[J, N],
                            XMGNA,
                            MGNTHA[J, N],
                            LOLTPA[J, N],
                            XMGNP,
                            XT,
                        )
                    )
                else:
                    f.write(
                        "\n  %2d  %2d         %8.2f  %8.2f            %s\n"
                        % (J, N, LOLTPA[J, N], XMGNP, XT)
                    )

                if LOLSHA[J, N] > 0:
                    XMGNA = (MGNSHA[J, N]) / (LOLSHA[J, N])
                else:
                    XMGNA = 0.0

                if LOLSPA[J, N] > 0:
                    XMGNP = (MGNSPA[J, N]) / (LOLSPA[J, N])
                else:
                    XMGNP = 0.0

                if INDX != 1:
                    f.write(
                        "\n  %2d  %2d    %4d    %8.2f  %8d     %4d     %8.2f            %s\n"
                        % (
                            J,
                            N,
                            LOLSHA[J, N],
                            XMGNA,
                            MGNSHA[J, N],
                            LOLSPA[J, N],
                            XMGNP,
                            XS,
                        )
                    )
                else:
                    f.write(
                        "\n  %2d  %2d         %8.2f  %8.2f            %s\n"
                        % (J, N, LOLSPA[J, N], XMGNP, XT)
                    )

            if WOLGHA[J] > 0.0:
                XMGNA = WGNGHA[J] / WOLGHA[J]
            else:
                XMGNA = 0.0

            if WOLGPA[J] > 0.0:
                XMGNP = WGNGPA[J] / WOLGPA[J]
            else:
                XMGNP = 0.0

            if INDX != 1:
                f.write(
                    "\n  %2d  %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s\n"
                    % (J, XA, WOLGHA[J], XMGNA, WGNGHA[J], WOLGPA[J], XMGNP, XG)
                )
            else:
                f.write(
                    "\n  %2d  %s         %8.2f  %8.2f            %s\n"
                    % (J, XA, WOLGPA[J], XMGNP, XG)
                )

            if WOLTHA[J] > 0.0:
                XMGNA = WGNTHA[J] / WOLTHA[J]
            else:
                XMGNA = 0.0

            if WOLTPA[J] > 0.0:
                XMGNP = WGNTPA[J] / WOLTPA[J]
            else:
                XMGNP = 0.0

            if INDX != 1:
                f.write(
                    "\n  %2d  %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s\n"
                    % (J, XA, WOLTHA[J], XMGNA, WGNTHA[J], WOLTPA[J], XMGNP, XT)
                )
            else:
                f.write(
                    "\n  %2d  %s         %8.2f  %8.2f            %s\n"
                    % (J, XA, WOLTPA[J], XMGNP, XT)
                )

            if WOLSHA[J] > 0.0:
                XMGNA = WGNSHA[J] / WOLSHA[J]
            else:
                XMGNA = 0.0

            if WOLSPA[J] > 0.0:
                XMGNP = WGNSPA[J] / WOLSPA[J]
            else:
                XMGNP = 0.0

            if INDX != 1:
                f.write(
                    "\n  %2d  %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s\n"
                    % (J, XA, WOLSHA[J], XMGNA, WGNSHA[J], WOLSPA[J], XMGNP, XS)
                )
            else:
                f.write(
                    "\n  %2d  %s         %8.2f  %8.2f            %s\n"
                    % (J, XA, WOLSPA[J], XMGNP, XS)
                )

        # C POOL STATISTICS
        f.write("\n  POOL STATISTICS \n")
        for N in range(NFCST):
            if LOLGHP[N] > 0:
                XMGNH = (MGNGHP[N]) / (LOLGHP[N])
            # else:
            # XMGN = 0.0  # maybe for future usage

            if LOLGPP[N] > 0:
                XMGNP = (MGNGPP[N]) / (LOLGPP[N])
            # else:
            # XMGN = 0.0  # maybe for future usage

            if INDX != 1:
                f.write(
                    "      %2d     %4d     %8.2f  %8d     %4d     %8.2f            %s"
                    % (N, LOLGHP[N], XMGNH, MGNGHP[N], LOLGPP[N], XMGNP, XG)
                )
            else:
                f.write(
                    "      %2d         %8.2f  %8.2f            %s"
                    % (N, LOLGPP[N], XMGNP, XG)
                )

            if LOLTHP[N] > 0:
                XMGNH = (MGNTHP[N]) / (LOLTHP[N])
            else:
                XMGNH = 0.0

            if LOLTPP[N] > 0:
                XMGNP = (MGNTPP[N]) / (LOLTPP[N])
            else:
                XMGNP = 0.0

            if INDX != 1:
                f.write(
                    "      %2d     %4d     %8.2f  %8d     %4d     %8.2f            %s"
                    % (N, LOLTHP[N], XMGNH, MGNTHP[N], LOLTPP[N], XMGNP, XT)
                )
            else:
                f.write(
                    "      %2d         %8.2f  %8.2f            %s"
                    % (N, LOLTPP[N], XMGNP, XT)
                )

            if LOLSHP[N] > 0:
                XMGNH = (MGNSHP[N]) / (LOLSHP[N])
            else:
                XMGNH = 0.0

            if LOLSPP[N] > 0:
                XMGNP = (MGNSPP[N]) / (LOLSPP[N])
            else:
                XMGNP = 0.0

            if INDX != 1:
                f.write(
                    "      %2d     %4d     %8.2f  %8d     %4d     %8.2f            %s"
                    % (N, LOLSHP[N], XMGNH, MGNSHP[N], LOLSPP[N], XMGNP, XS)
                )
            else:
                f.write(
                    "      %2d         %8.2f  %8.2f            %s"
                    % (N, LOLSPP[N], XMGNP, XS)
                )

        if WOLGHP > 0.0:
            XMGNH = WGNGHP / WOLGHP
        else:
            XMGNH = 0.0

        if WOLGPP > 0.0:
            XMGNP = WGNGPP / WOLGPP
        else:
            XMGNP = 0.0

        if INDX != 1:
            f.write(
                "      %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                % (XA, WOLGHP, XMGNH, WGNGHP, WOLGPP, XMGNP, XG)
            )
        else:
            f.write(
                "      %s         %8.2f  %8.2f            %s" % (XA, WOLGPP, XMGNP, XG)
            )

        if WOLTHP > 0.0:
            XMGNH = WGNTHP / WOLTHP
        else:
            XMGNH = 0.0

        if WOLTPP > 0.0:
            XMGNP = WGNTPP / WOLTPP
        else:
            XMGNP = 0.0

        if INDX != 1:
            f.write(
                "      %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                % (XA, WOLTHP, XMGNH, WGNTHP, WOLTPP, XMGNP, XT)
            )
        else:
            f.write(
                "      %s         %8.2f  %8.2f            %s" % (XA, WOLTPP, XMGNP, XT)
            )

        if WOLSHP > 0.0:
            XMGNH = WGNSHP / WOLSHP
        else:
            XMGNH = 0.0

        if WOLSPP > 0.0:
            XMGNP = WGNSPP / WOLSPP
        else:
            XMGNP = 0.0

        if INDX != 1:
            f.write(
                "      %s     %7.2f  %8.2f   %7.0f     %7.2f  %8.2f            %s"
                % (XA, WOLSHP, XMGNH, WGNSHP, WOLSPP, XMGNP, XS)
            )
        else:
            f.write(
                "      %s         %8.2f  %8.2f            %s" % (XA, WOLSPP, XMGNP, XS)
            )

    # Zero out statistics reated arrays and scalars:
    WGNGHA[:NOAREA] = 0.0
    WGNTHA[:NOAREA] = 0.0
    WGNSHA[:NOAREA] = 0.0
    WOLGHA[:NOAREA] = 0.0
    WOLTHA[:NOAREA] = 0.0
    WOLSHA[:NOAREA] = 0.0

    WGNGPA[:NOAREA] = 0.0
    WGNTPA[:NOAREA] = 0.0
    WGNSPA[:NOAREA] = 0.0
    WOLGPA[:NOAREA] = 0.0
    WOLTPA[:NOAREA] = 0.0
    WOLSPA[:NOAREA] = 0.0

    WGNSHP = 0.0
    WOLSHP = 0.0
    WGNSPP = 0.0
    WOLSPP = 0.0
    WGNGHP = 0.0
    WOLGHP = 0.0
    WGNGPP = 0.0
    WOLGPP = 0.0
    WGNTHP = 0.0
    WOLTHP = 0.0
    WGNTPP = 0.0
    WOLTPP = 0.0

    LOLTHA[:NFCST, :NOAREA] = 0
    LOLGHA[:NFCST, :NOAREA] = 0
    MGNTHA[:NFCST, :NOAREA] = 0
    MGNGHA[:NFCST, :NOAREA] = 0
    LOLTPA[:NFCST, :NOAREA] = 0
    LOLGPA[:NFCST, :NOAREA] = 0
    MGNTPA[:NFCST, :NOAREA] = 0
    MGNGPA[:NFCST, :NOAREA] = 0

    LOLTHP[:NFCST] = 0
    LOLGHP[:NFCST] = 0
    MGNTHP[:NFCST] = 0
    MGNGHP[:NFCST] = 0
    LOLTPP[:NFCST] = 0
    LOLGPP[:NFCST] = 0
    MGNTPP[:NFCST] = 0
    MGNGPP[:NFCST] = 0

    if IYEAR <= 5:
        print(
            "\n  KVs = %4d %4d %4d %4d %4d"
            % (KWHERE, KVWHEN, KVSTAT, KVTYPE, KVLOC + 1)
        )

    f.close()  # close the file "output"

    # Begin checking for convergence
    if KWHERE == 1:
        if KVWHEN == 1:
            if KVSTAT == 1:
                # LOOP FOR HOURLY, AREA, LOLE
                if KVTYPE == 1:
                    SUM = SWLSHA[KVLOC]
                else:
                    SUM = SOLSHA[KVLOC, NOERR]
            # KVSTAT = 2, LOOP FOR HOURLY, AREA, EUE
            else:
                if KVTYPE == 1:
                    SUM = SWNSHA[KVLOC]
                else:
                    SUM = SGNSHA[KVLOC, NOERR]
        # KVWHEN = 2, LOOP FOR PEAK, AREA, LOLE
        else:
            if KVSTAT == 1:
                if KVTYPE == 1:
                    SUM = SWLSPA[KVLOC]
                else:
                    SUM = SOLSPA[KVLOC, NOERR]
            # KVWHEN=2, KVSTAT = 2, LOOP FOR PEAK, AREA, EUES
            else:
                if KVTYPE == 1:
                    SUM = SWNSPA[KVLOC]
                else:
                    SUM = SGNSPA[KVLOC, NOERR]
    else:
        if KVWHEN == 1:
            if KVSTAT == 1:
                # LOOP FOR HOURLY, POOL, LOLE
                if KVTYPE == 1:
                    SUM = SWLSHP
                else:
                    SUM = SOLSHP[NOERR]
            # KVSTAT = 2, LOOP FOR HOURLY, POOL, EUE
            else:
                if KVTYPE == 1:
                    SUM = SWNSHP
                else:
                    SUM = SGNSHP[NOERR]
        # KVWHEN = 2, LOOP FOR PEAK, POOL, LOLE
        else:
            if KVSTAT == 1:
                if KVTYPE == 1:
                    SUM = SWLSPP
                else:
                    SUM = SOLSPP[NOERR]
            # KVWHEN=2, KVSTAT = 2, LOOP FOR PEAK, POOL, EUES
            else:
                if KVTYPE == 1:
                    SUM = SWNSPP
                else:
                    SUM = SGNSPP[NOERR]

    RFLAG, SSQ, XLAST = cvchk(CLOCK, FINISH, IYEAR, CVTEST, SUM, XLAST, SSQ)
    NOERR = 1

    if IYEAR == INTVT:
        intm(
            ATRIB,
            CLOCK,
            IPOINT,
            XLAST,
            SSQ,
            MFA,
            NUMINQ,
            ITAB,
            INTVT,
            EVNTS,
            123,  # IGSEED,
            123,  # ILSEED,
            LT,
            BB,
            ZB,
            SOLTHA,
            SOLGHA,
            SOLSHA,
            SGNTHA,
            SGNGHA,
            SGNSHA,
            SOLTPA,
            SOLGPA,
            SOLSPA,
            SGNTPA,
            SGNGPA,
            SGNSPA,
            SWLSHA,
            SWLGHA,
            SWLTHA,
            SWNSHA,
            SWNGHA,
            SWNTHA,
            SWLSPA,
            SWLGPA,
            SWLTPA,
            SWNSPA,
            SWNGPA,
            SWNTPA,
            SOLTHP,
            SOLGHP,
            SOLSHP,
            SGNTHP,
            SGNGHP,
            SGNSHP,
            SOLTPP,
            SOLGPP,
            SOLSPP,
            SGNTPP,
            SGNGPP,
            SGNSPP,
            HLOLE,
            DPLOLE,
            EUES,
            XNEWA,
            XNEWP,
            WOLSHA,
            LSFLG,
        )

        INTVT += INTV

    else:  # if IYEAR != INTVT
        assert type(IYEAR) is int
        IFIN = int(FINISH / 8760)
        if IYEAR == IFIN:
            intm(
                ATRIB,
                CLOCK,
                IPOINT,
                XLAST,
                SSQ,
                MFA,
                NUMINQ,
                ITAB,
                INTVT,
                EVNTS,
                123,  # IGSEED,
                123,  # ILSEED,
                LT,
                BB,
                ZB,
                SOLTHA,
                SOLGHA,
                SOLSHA,
                SGNTHA,
                SGNGHA,
                SGNSHA,
                SOLTPA,
                SOLGPA,
                SOLSPA,
                SGNTPA,
                SGNGPA,
                SGNSPA,
                SWLSHA,
                SWLGHA,
                SWLTHA,
                SWNSHA,
                SWNGHA,
                SWNTHA,
                SWLSPA,
                SWLGPA,
                SWLTPA,
                SWNSPA,
                SWNGPA,
                SWNTPA,
                SOLTHP,
                SOLGHP,
                SOLSHP,
                SGNTHP,
                SGNGHP,
                SGNSHP,
                SOLTPP,
                SOLGPP,
                SOLSPP,
                SGNTPP,
                SGNGPP,
                SGNSPP,
                HLOLE,
                DPLOLE,
                EUES,
                XNEWA,
                XNEWP,
                WOLSHA,
                LSFLG,
            )

    if RFLAG == 1 or CLOCK >= FINISH:
        ITAB = report(
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
        )

    return IPOINT, MFA, NUMINQ, SSQ, XLAST, RFLAG, INTVT, ITAB
