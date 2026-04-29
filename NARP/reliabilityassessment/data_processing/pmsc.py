import numpy as np

from reliabilityassessment.data_processing.pmlolp import pmlolp


def pmsc(
    IA,
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
    Automatic schedule of planned maintenance

    :param int IA: integer index of a specific area
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
    :param int ITAB: the table index (created so far)
    :param numpy.ndarray RATES: original rating data of each unit for four seasons with
        shape (NUNITS, 4)
    :param numpy.ndarray PROBG: 2D array of accumulated probability for each capacity
        tier of each unit
    :param numpy.ndarray DERATE: array of the derated capacity of each unit
    :param np.ndarray PKLOAD: array of user-defined annual peak of each area.
    :param numpy.ndarray WPEAK: 2D array, weekly peak load amount (MW)
        1st dim: areaIdx, 2nd dim: weekIdx
    :param int IREPM: indicator for whether printing the reuslt of maintenance not
    :param numpy.ndarray MINRAN: beginning week of the maintenance (outage) window of
        each area with shape (NOAREA,)
    :param numpy.ndarray MAXRAN: ending week of maintenance (outage) window of
        each area with shape (NOAREA,)
    :param numpy.ndarray INHBT1: beginning week of the forbidden (inhibt) period of
        each area with shape (NOAREA,)
    :param numpy.ndarray INHBT2: ending week of the forbidden (inhibt) period of
        each area with shape (NOAREA,)
    :param numpy.ndarray NAMU: name string of each generator unit with shape (NUNITS,)
        (in Fortran, it is double-typed as also 'int' but not used)
    :param numpy.ndarray NUMP: name string of each generator plant with shape (NUNITS,)
        (in Fortran, it is double-typed as also 'int' but not used)
    :return: (*int*) -- ITAB

    .. note:: 1. Global array 'ID' is modified in-place
              2. Annotations for certain intermediate (local) variables/arrays:
                    SCHLOS   SCHEDULED LOSS DUE TO MAINTENANCE
                    DURLOS   LOSS DUE TO MAINTENANCE
                    SDLOLP   SCHEDULED LOSS X DURATION X PROB. OF FORCED OUT
                    LOCREW   LOCATION & CREW
                    LOAD     WEEKLY PEAK LOAD
                    WEEKS    ASSIGNED TIME FOR MAINTENANCE
                    CULOLP   CUMMLOLP
    """

    ITC = ITAB
    INUO = 500  # the possible maximum number of units
    INPO = 150  # the possible maximum number of plants

    N = 0  # N is the highest plant number

    NUNITS = ID.shape[0]

    # Below are all local arrays created for the conveneice in intermedaite computation
    INDEX = np.zeros((INUO, 2))  # maybe use "-1" for intialization
    INDEX1 = np.zeros(INUO)  # maybe use "-1" for intialization
    P = np.ones(INUO)
    NR0 = np.zeros(NUNITS, dtype=int)
    ID1 = np.zeros((1 + NUNITS, 8), dtype=int)
    CAPLOS = np.zeros(NUNITS)
    RD = np.zeros((NUNITS, 3))
    DURLOS = np.zeros((NUNITS, 2))
    LOCREW = np.zeros(NUNITS)
    IDT = np.zeros((NUNITS, 8))
    RDT = np.zeros((NUNITS, 3))
    CAPLO = np.zeros(NUNITS)
    DURLO = np.zeros((NUNITS, 2))
    LOCRE = np.zeros(NUNITS)
    WEEKS = [""] * 52
    A = "AA"
    B = ".."
    AB = "PP"
    CHECK = np.zeros((INPO, 52))
    LOAD = np.zeros(52)
    EFLOAD = np.zeros(52)
    MWTOT = np.zeros(NUNITS)
    MWI = np.zeros(NUNITS)
    MWEEK = np.zeros(NUNITS)
    NPSU = np.zeros(NUNITS)
    SCHLOS = np.zeros(NUNITS)  # SCHEDULED LOSS DUE TO MAINTENANCE;

    # Note that 'NGU' means the total number of gen units used in this function
    # but 0 in original Fortran code, it also uses sometimes as "index" for arrays
    # since Fortran is 1-based indexing.
    NGU = -1

    for i in range(NUNITS):
        if ID[i, 2] != IA:
            continue

        NGU += 1
        N = max(N, ID[i, 1])

        NR0[NGU] = ID[i, 0]
        ID1[NGU, 0] = NGU
        ID1[NGU, 1:8] = ID[i, 1:8]

        CAPLOS[NGU] = max(RATES[i, :4])
        RD[NGU, 1] = 1.0 - PROBG[i, 1]
        RD[NGU, 0] = PROBG[i, 1] - PROBG[i, 0]
        RD[NGU, 2] = 1 - DERATE[i]

    NGU += 1  # restoring its literal meaning, i.e.the total number of gen units used in this function

    if NGU == 0:
        return ITAB

    DURLOS[:NGU, :2] = ID1[:NGU, [4, 6]].copy()
    ID1[:NGU, [4, 6]] *= 168
    ID1[:NGU, [3, 5]] = ID1[:NGU, [3, 5]] * 168 - 168
    LOCREW[:NGU] = ID1[:NGU, 1].copy()

    # G: approximately peak load. This number is used to ensure that load plus capacity on planned maintenance
    # does not exceed this value during any week of the year
    # CAP1, CAP2:    these values of capacity are used to compute the slope of the capacity outage probability table
    # IOPT:          0 if departure rates are used
    # 	             1 if dfor and for are used
    #                >1 if dafor is used

    CAP = sum(CAPLOS[:NGU])
    CAP1 = CAP / 20
    CAP2 = CAP / 5
    G = PKLOAD[IA]
    M = NGU  # M is the total number of generating units considerred in this function
    i1 = 0
    # arrange the sequence of units such that for a given plant the units are
    # arranged in the descending order of capacity*planned maintenance duration
    for i in range(N):
        while True:
            IC = 0  # (possibly) a flag varaiable
            CMAX = -5.0

            for j in np.where(ID1[:M, 1] == i)[0]:
                IC = 1
                CDUR = CAPLOS[j] * max(DURLOS[j, :2])
                if CDUR > CMAX:
                    CMAX, JT = CDUR, j

            if IC == 0:
                break

            i1 += 1
            IDT[i1, :8] = ID1[JT, :8].copy()

            ID1[JT, 1] = -1  # plant index
            RDT[i1, :3] = RD[JT, :3].copy()

            CAPLO[i1] = CAPLOS[JT]
            DURLO[i1, 0] = DURLOS[JT, 0]
            DURLO[i1, 1] = DURLOS[JT, 1]
            LOCRE[i1] = LOCREW[JT]

    ID1[:M, :8] = IDT[:M, :8].copy()
    RD[:M, :3] = RDT[:M, :3].copy()
    CAPLOS[:M] = CAPLO[:M].copy()
    DURLOS[:M, :2] = DURLO[:M, :2].copy()
    LOCREW[:M] = LOCRE[:M].copy()

    ID1[M, 0] = 2000

    # call subroutine pmlolp to create capacity outage probability table
    NGS, KA, PA = pmlolp(CAPLOS, RD, NGU)

    # calculate the 'M factor' ,ie, the slope of capacity outage probability table
    for i in range(NGS):
        if KA[i] >= CAP1:
            break

    UL = PA[i]
    CAP1 = KA[i]

    for i in range(NGS):
        if KA[i] >= CAP2:
            break

    XLL = PA[i]
    CAP2 = KA[i]

    XM = 5000  # the "M factor"
    if XLL >= 0.0000001:
        DENOM = np.log(UL / XLL)
        if DENOM >= 0.0000001:
            XM = (CAP2 - CAP1) / DENOM  # XM is the so-called 'M factor'
    # print("M factor = %f\n"%(XM))

    # Read scheduled loss, duration loss, previous maint. weeks, minimum range,
    # max. range, weekly predicted max. load, inhbted periods.
    # To save computing time the data is arranged by maintenance-crew units.
    # All generating units in a particular location-crew is arranged
    # in sequence based on the largest schedule maintenance x duration
    WEEKS[:52] = B
    CHECK[:INPO, :52] = 0.0
    LOAD[:52] = WPEAK[IA, :52].copy()
    EFLOAD[:52] = LOAD[:52].copy()

    MWTOT[:N] = 0
    MWEEK[:M] = 0

    f = open("output.txt", "a")  # can put earlier
    if IREPM != 0:
        f.write("\n WEEKLY PEAK LOAD BEFORE MAINTENANCE SCHEDULING \n")
        for i in range(52):
            if i % 13 == 0:
                f.write("\n")
            f.write(" %.4f" % (LOAD[i]))

    NPS = -1  # 0 in Fortran
    for i in range(M):
        if ID1[i, 7] == 0:
            break
        NPS += 1
        NPSU[NPS] = ID1[i, 0]
    NPS += 1  # restoring the meainig of certain length

    i = -1  # 0 in Fortran
    LTEM = 0
    for j in range(M):  # goto flag #52
        R = 1 - P[j] + P[j] * np.exp(CAPLOS[j] / XM)
        SCHLOS[j] = CAPLOS[j] - XM * np.log(R)
        if SCHLOS[j] <= 0:
            SCHLOS[j] = CAPLOS[j]
        if LTEM != LOCREW[j]:
            i += 1
            LTEM = LOCREW[j]
            MWTOT[j] = 0
            MWI[j] = LOCREW[j]

        if NPS > 0:  # in Fortran " NPS != 0 "
            gotoflag11 = False
            for ii in range(NPS):
                IN1 = NPSU[ii]
                if ID1[j, 0] == IN1:
                    gotoflag11 = True
                    break

            if gotoflag11 is False:
                MWEEK[j] = SCHLOS[j] * (DURLOS[j, 0] + DURLOS[j, 1])
                MWTOT[i] += MWEEK[j]
                continue

            if ID1[j, 0] != IN1:
                MWEEK[j] = SCHLOS[j] * (DURLOS[j, 0] + DURLOS[j, 1])
                MWTOT[i] += MWEEK[j]
                continue

            if ID1[j, 3] != -1 or ID1[j, 4] != 0:  # ID1[j, 3] != 0 in Fotran
                M1 = (
                    ID1[j, 3] // 168 + 1
                )  # maybe remvoe "+1" here; ID1[j, 3] / 168 + 1 in Fortran
                M2 = M1 + DURLOS[j, 0] - 1
                IPN = i
                M2 = min(M2, 51)  # maybe 52; need to check
                if M2 != -1:  # originally in Fortran "if M2 != 0"
                    CHECK[IPN, M1 : M2 + 1] = LOCREW[j]
                    EFLOAD[M1 : M2 + 1] += SCHLOS[j]
                    LOAD[M1 : M2 + 1] += CAPLOS[j]
                    INDEX[j, 0] = M1
                    INDEX1[j] = 0  # originally in Fortran "1"
            else:
                INDEX1[j] = 0  # originally in Fortran "1"

            if ID1[j, 5] != -1 or ID1[j, 6] != 0:
                M3 = (
                    ID1[j, 5] // 168 + 1
                )  # maybe remvoe "+1" here; ID1[j, 5] / 168 + 1 in Fortran
                M4 = M3 + DURLOS[j, 1] - 1
                M4 = min(M4, 51)  # maybe 52; need to check
                if M4 != -1:  # originally in Fortran "if M4 != 0"
                    CHECK[IPN, M3 : M4 + 1] = LOCREW[j]
                    EFLOAD[M3 : M4 + 1] += SCHLOS[j]
                    LOAD[M3 : M4 + 1] += CAPLOS[j]
                    INDEX[j, 1] = M3
            continue

        MWEEK[j] = SCHLOS[j] * (DURLOS[j, 0] + DURLOS[j, 1])
        MWTOT[i] += MWEEK[j]

    ITC += 1  # increase the table no. by one

    f = open("output.txt", "a")  # can put earlier

    if IREPM != 0:
        # 323
        f.write("\n ")
        for _ in range(50):
            f.write(" ")
        f.write(
            " \n\t\t\t\t\t\t\t\t\t\t\t\t PLANNED MAINTENANCE SCHEDULE FOR AREA %3d \n"
            % (IA + 1)
        )
        f.write("\n")

        # 523
        f.write("\n ")
        for _ in range(51):
            f.write(" ")
        for _ in range(32):
            f.write("-")
        f.write("\n")

        # 190
        f.write("\n ")
        for _ in range(63):
            f.write(" ")
        f.write("TABLE %4d \n\n" % (ITC))

        # 801
        f.write("\n  ")
        for _ in range(123):
            f.write("-")
        f.write("\n  |      |      |")

        # 802
        f.write("\n |      |      |")
        for _ in range(107):
            f.write(" ")
        f.write("|")

        # 803
        f.write("\n |      |      |")
        for _ in range(50):
            f.write(" ")
        f.write("MONTHS")
        for _ in range(51):
            f.write(" ")
        f.write("|")

        # 802
        f.write("\n |      |      |")
        for _ in range(107):
            f.write(" ")
        f.write("|")

        # 811
        f.write("\n |      |      |")
        for _ in range(107):
            f.write("-")
        f.write("|")

        # 804
        f.write("\n  |      |      |")
        for _ in range(4):
            for KJ in range(26):
                f.write(" ")
            f.write("|")

        # 805
        f.write(
            "\n  | UNIT | CAP  |  JAN      FEB      MAR   |  APR      MAY      JUN   |"
            "JUL      AUG      SEP   |  OCT      NOV      DEC   |"
        )

        # 806
        f.write("\n  | NAME | (MW) |")
        for _ in range(4):
            for KJ in range(26):
                f.write(" ")
            f.write("|")

        # 807
        f.write(
            "\n  |      |      |  1 2 3 4 5 6 7 8 9 0 1 2 3 | 4 5 6 7 8 9 0 1 2 3 4 5 6 | "
            "7 8 9 0 1 2 3 4 5 6 7 8 9 | 0 1 2 3 4 5 6 7 8 9 0 1 2 |"
        )

        # 809
        f.write(
            "\n  |      |                   1      |             2            |       3"
            "                  | 4                   5    |"
        )

        # 801
        f.write("\n  ")
        for _ in range(123):
            f.write("-")
        f.write("\n  |      |      |")

        # 804
        f.write("\n  |      |      |")
        for _ in range(4):
            for KJ in range(26):
                f.write(" ")
            f.write("|")

    # schedule first the plant with the largest total schedule MW loss x duration.
    # Find the largest MWTOT(i)
    i = N
    for LM in range(N):  # 89
        MAX1 = 0

        for K in range(N):
            if MAX1 >= MWTOT[K]:
                continue
            MAX1 = MWTOT[K]
            i = K

        # Create MWEEK(J)
        K1 = MWI[i]
        MWEEK[:M] = 0

        for K2 in np.where(ID1[:M, 1] == K1)[0]:
            MWEEK[K2] = SCHLOS[K2] * (DURLOS[K2, 0] + DURLOS[K2, 1])

        # Clear the MWTOT(i), since no longer required
        if MWTOT[i] == 0:
            continue

        MWTOT[i] = 0
        # Set the index for MWEEK(J), J=N1,N2

        N1 = 0  # in Fortran, 1; need to check
        N2 = -1  # in Fortran,0; need to check
        for j in range(M):
            if MWEEK[j] != 0:
                N2 = j
            if MWEEK[j] == 0 and N2 == -1:
                N1 += 1

        # Schedule all generators within the same plant
        gotoFlag18 = True
        while gotoFlag18:
            gotoFlag18 = False

            for JA in range(N1, N2):  # flag 30 ; maybe N2 + 1
                j = JA
                J4 = JA

                # Set index for scheduling within the flexible maintenance period,
                # between min. and max. range
                if MWEEK[JA] == 0:
                    continue

                gotoFlag191 = True
                while gotoFlag191:  # flag 191
                    gotoFlag191 = False
                    MT = 0
                    IMT = 0
                    I5 = 2
                    if ID1[j, 4] > ID1[j, 6]:
                        I5 = 1
                    if ID1[j, 4] == 0 or ID1[j, 6] == 0:
                        I5 = 0

                    DURL = DURLOS[j, 0]
                    if DURLOS[j, 1] > DURL:
                        DURL = DURLOS[j, 1]

                    MAXR = MAXRAN[IA]
                    MINR = MINRAN[IA]

                    if I5 != 0:
                        if I5 != 2:
                            MAXRAN[IA] = INHBT1[IA]
                        else:
                            MINRAN[IA] = INHBT2[IA]

                    while True:  # 19
                        I1 = MINRAN[IA]

                        IM = DURL - 1
                        IT = MAXRAN[IA] - IM
                        IX = 53 - DURL - 1  # originally in Fortran "53-DURL"
                        if I1 <= 0:
                            I1 = 1
                        IX = min(IX, IT)
                        ITE = 10**6
                        IC = 0

                        for J1 in range(I1, IX + 1):
                            IR = SCHLOS[j]
                            IS = J1 + IM
                            if J1 >= INHBT1[IA] - IM and IS <= INHBT2[IA] + IM:
                                continue
                            if LOCREW[j] == CHECK[i, J1] or LOCREW[j] == CHECK[i, IS]:
                                continue

                            breakFlag = False
                            for L in range(J1, IS + 1):
                                if IR + EFLOAD[L] >= G:
                                    breakFlag = True
                                    break
                            if breakFlag:
                                continue

                            if IS + 1 > J1:
                                IC = 1
                            IR += sum(EFLOAD[J1 : IS + 1])

                            if ITE < IR:
                                continue
                            ITE = IR
                            M1 = J1

                        MAXRAN[IA] = MAXR
                        MINRAN[IA] = MINR

                        if I5 != 0:
                            # I6=I5 # I6 never used in original Fortran
                            IC = 0
                            MT = M1
                            IMT = IM
                            DURL = DURLOS[j, 0]
                            if DURLOS[j, 1] <= DURL:
                                DURL = DURLOS[j, 1]
                            if I5 != 2:
                                MINRAN[IA] = INHBT2[IA]
                            else:
                                MAXRAN[IA] = INHBT1[IA]
                            I5 = 0
                            continue  # GO TO 19

                        # IC is the flag to check whether the schedule is feasible.
                        if IC == 0:
                            while True:
                                J4 -= 1
                                if J4 <= -1:  # <=0 in Fotran
                                    IU0 = ID1[JA, 0]
                                    IU0 = NR0[IU0]
                                    IBG1N = (
                                        ID1[JA, 3] // 168 + 1
                                    )  # maybe remvoe "+1" here; ID1[JA, 3] / 168 + 1 in Fortran
                                    IBG2N = (
                                        ID1[JA, 5] // 168 + 1
                                    )  # maybe remvoe "+1" here; ID1[JA, 5] / 168 + 1 in Fortran
                                    ID1R = (
                                        ID1[JA, 4] // 168
                                    )  # ID1[JA, 4] / 168 in Fortran
                                    ID2R = (
                                        ID1[JA, 6] // 168
                                    )  # ID1[JA, 6] / 168 in Fortran

                                    f.write(
                                        "          SCHEDULE FOR  GENERATOR ** %s %s **  IS NOT FEASIBLE"
                                        "\n          'THIS UNIT IS SCHEDULED WITH PRESPECIFIED PARAMETERS AS FOLLOWS:\n"
                                        "          BEGINING FIRST OUTAGE = %2d   DURATION = %2d\n"
                                        "          BEGINING SECOND OUTAGE = %2d   DURATION = %2d\n"
                                        % (
                                            NAMU[IU0],
                                            NUMP[IU0],
                                            IBG1N,
                                            ID1R,
                                            IBG2N,
                                            ID2R,
                                        )
                                    )

                                    MWEEK[JA] = 0
                                    INDEX[j, 0] = 0
                                    INDEX[j, 1] = 0

                                    gotoFlag18 = True  # GO TO 18
                                    break

                                # Cancel the previous scheduled generator, try to schedule the
                                # Non-feasible one. Interchange order of the scheduling.
                                if MWEEK[J4] == 0:
                                    continue

                                if INDEX[J4, 0] == 0 and INDEX[J4, 1] == 0:
                                    continue
                                else:
                                    break

                                for ci in [0, 1]:
                                    if INDEX[J4, ci] != 0:  # maybe -1
                                        NC1 = INDEX[J4, ci]
                                        NC2 = NC1 + DURLOS[J4, ci] - 1
                                        CHECK[i, NC1 : NC2 + 1] = 0
                                        LOAD[NC1 : NC2 + 1] -= CAPLOS[J4]
                                        EFLOAD[NC1 : NC2 + 1] -= SCHLOS[J4]
                                        WEEKS[NC1 : NC2 + 1] = B
                                        INDEX[J4, ci] = 0

                                gotoFlag191 = True
                                break

                        if gotoFlag18:
                            break

                        if gotoFlag191:
                            break

                        # INDEX(j) is the starting scheduled maintenance week for generator j
                        IMM = IM + 1
                        IMM = IMM * 168

                        if IMM != ID1[j, 4]:
                            M3 = MT
                            IM3 = IMT
                            M4 = M1
                            IM4 = IM
                        else:
                            M3 = M1
                            IM3 = IM
                            M4 = MT
                            IM4 = IMT

                        INDEX[j, 0] = M3
                        ID1[j, 3] = (M3 - 1) * 168
                        INDEX1[j] = 0
                        M2 = M3 + IM3

                        if M2 >= M3 and M3 != 0:
                            CHECK[i, M3 : M2 + 1] = LOCREW[j]
                            EFLOAD[M3 : M2 + 1] += SCHLOS[j]
                            LOAD[M3 : M2 + 1] += CAPLOS[j]

                        INDEX[j, 1] = M4
                        ID1[j, 5] = (M4 - 1) * 168
                        M2 = M4 + IM4

                        if M2 >= M4 and M4 != 0:
                            CHECK[i, M4 : M2 + 1] = LOCREW[j]
                            EFLOAD[M4 : M2 + 1] += SCHLOS[j]
                            LOAD[M4 : M2 + 1] += CAPLOS[j]

                        while True:
                            J4 += 1
                            if J4 > JA:
                                gotoFlag30 = True
                                break  # GO TO 30
                            j -= 1
                            if MWEEK[j] == 0:
                                continue

                        if gotoFlag30:
                            break

                        while True:
                            J4 += 1
                            if J4 > JA:
                                gotoFlag30 = True
                                break  # GO TO 30
                            j -= 1
                            if MWEEK[j] != 0:
                                break

                        if gotoFlag30:
                            break

                        # end of while-loop 19

                    if gotoFlag18:
                        break

                    if gotoFlag191:
                        continue

                    # end of while-loop 191

                if gotoFlag18:
                    break

                if gotoFlag30:
                    continue
                # end of for-loop 30

            if gotoFlag18:
                continue
    # end of for-loop 89

    # Print output of the scheduled generators of the plant
    NTI = 0
    NMAX = 40
    WEEKS = [" "] * 52
    for i in range(M):
        JB = i
        if INDEX[JB, 0] == 0 and INDEX[JB, 1] == 0:
            continue

        for ci in [0, 1]:
            if INDEX[JB, ci] != 0:
                MC1 = INDEX[JB, ci]
                MC2 = MC1 + DURLOS[JB, ci] - 1
                MC2 = min(MC2, 51)
                WEEKS[MC1 : MC2 + 1] = A if INDEX1[JB] == 0 else AB

        IU0 = ID1[JB, 0]
        IU0 = NR0[IU0]

        if IREPM != 0:
            f.write("\n  | %s%s | %4d |\n" % (NAMU[IU0], NUMP[IU0], CAPLOS[JB]))

            for KI in range(4):
                for KJ in range(13):
                    f.write("%s " % (WEEKS[(KI - 1) * 13 + KJ]))
                f.write("|")

        WEEKS[:52] = B

        NTI += 1
        if NTI <= NMAX:
            continue

        NMAX += 40
        if IREPM != 0:
            f.write("\n  |      |      |")
            for _ in range(4):
                for KJ in range(26):
                    f.write(" ")
                f.write("|")

            # 801
            f.write("\n  ")
            for _ in range(123):
                f.write("-")
            f.write("\n  |      |      |")

            # 190
            for _ in range(63):
                f.write("\n ")
            f.write("TABLE %4d \n\n" % (ITC))

            # 801
            f.write("\n  ")
            for _ in range(123):
                f.write("-")
            f.write("\n  |      |      |")

            # 802
            f.write("\n |      |      |")
            for _ in range(107):
                f.write(" ")
            f.write("|")

            # 803
            f.write("\n |      |      |")
            for _ in range(50):
                f.write(" ")
            f.write("MONTHS")
            for _ in range(51):
                f.write(" ")
            f.write("|")

            # 802
            f.write("\n |      |      |")
            for _ in range(107):
                f.write(" ")
            f.write("|")

            # 801
            f.write("\n  ")
            for _ in range(123):
                f.write("-")
            f.write("\n  |      |      |")

            # 804
            f.write("\n  |      |      |")
            for _ in range(4):
                for KJ in range(26):
                    f.write(" ")
                f.write("|")

            # 805
            f.write(
                "\n  | UNIT | CAP  |  JAN      FEB      MAR   |  APR      MAY      JUN   |"
                "JUL      AUG      SEP   |  OCT      NOV      DEC   |"
            )

            # 806
            f.write("\n  | NAME | (MW) |")
            for _ in range(4):
                for KJ in range(26):
                    f.write(" ")
                f.write("|")

            # 807
            f.write(
                "\n  |      |      |  1 2 3 4 5 6 7 8 9 0 1 2 3 | 4 5 6 7 8 9 0 1 2 3 4 5 6 | "
                "7 8 9 0 1 2 3 4 5 6 7 8 9 | 0 1 2 3 4 5 6 7 8 9 0 1 2 |"
            )

            # 804
            f.write("\n  |      |      |")
            for _ in range(4):
                for KJ in range(26):
                    f.write(" ")
                f.write("|")

            # 801
            f.write("\n  ")
            for _ in range(123):
                f.write("-")
            f.write("\n  |      |      |")

            # 804
            f.write("\n  |      |      |")
            for _ in range(4):
                for KJ in range(26):
                    f.write(" ")
                f.write("|")

    if IREPM != 0:
        # 804
        f.write("\n  |      |      |")
        for _ in range(4):
            for KJ in range(26):
                f.write(" ")
            f.write("|")

        # 801
        f.write("\n  ")
        for _ in range(123):
            f.write("-")
        f.write("\n  |      |      |")

        # 258
        f.write("\n 1")
        for _ in range(10):
            f.write("\n")
        f.write(
            "\t\t\t\t     WEEKLY PEAK LOAD + EFFECTIVE CAPACITY (MW) ON MAINTENANCE \n"
        )

        # 290
        f.write("0\n")
        for KI in range(4):
            for KJ in range(13):
                f.write("  %.4f" % (EFLOAD[KI * 13 + KJ]))
            f.write("\n")

        # 268
        f.write("0\n\n\n\n\n\t\t\t\t     WEEKLY PEAK LOAD + CAPACITY ON MAINTENANCE \n")

        # 290
        f.write("0\n")
        for KI in range(4):
            for KJ in range(13):
                f.write("  %.4f" % (LOAD[KI * 13 + KJ]))
            f.write("\n")

    f.close()

    ITAB = ITC
    for i in range(NGU):
        IND = ID1[i, 0]
        IND = NR0[IND]
        ID[IND, 3] = (
            ID1[i, 3] // 168 + 1
        )  # maybe remvoe "+1" here; ID1[i, 3] / 168 + 1 in Fortran
        ID[IND, 5] = (
            ID1[i, 5] // 168 + 1
        )  # maybe remvoe "+1" here; ID1[i, 3] / 168 + 1 in Fortran

    return ITAB
