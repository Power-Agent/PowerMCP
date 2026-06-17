from copy import deepcopy

import numpy as np


def datax(inputB_dict):
    """
    Reads all data except the hourly load data
    and creates appropriate arrays.

    :param dict inputB_dict: a compound python dictionary stores
                             all the parsed data from the INPUTB file.

    :return: (*tuple*)  a series of numpy ndarrays;
                        please refer to the 'variable description list.xlsx' file at
                        https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0
    """

    # --------------------------------------------------------------
    # Process ZZMC card data and creates appropriate arrays
    # please refer to the 'variable description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    # QTR -- array of hourly index corresponding to the three quarterly change timing.
    QTR = np.zeros(3)
    QTR[0] = inputB_dict["ZZMC"]["IW1"] * 168 + 0.5
    QTR[1] = inputB_dict["ZZMC"]["IW2"] * 168 + 0.5
    QTR[2] = inputB_dict["ZZMC"]["IW3"] * 168 + 0.5

    # --------------------------------------------------------------
    # Process ZZLD data card and creates appropriate arrays
    # please refer to the 'variable description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    NOAREA = len(inputB_dict["ZZLD"]["RATES"])  # number of areas
    PKLOAD = deepcopy(
        inputB_dict["ZZLD"]["RATES"][:, 0]
    )  # Annual peak in the area, in MW.
    FU = deepcopy(inputB_dict["ZZLD"]["RATES"][:, 1])  # forecasting uncertainty
    MINRAN = deepcopy(
        inputB_dict["ZZLD"]["ID"][:, 0]
    )  # BEG WK: Beginning week of the outage window
    MINRAN -= 1  # 0-based index in Python!
    MAXRAN = deepcopy(
        inputB_dict["ZZLD"]["ID"][:, 1]
    )  # END WK: Ending week of the outage window
    MAXRAN -= 1  # 0-based index in Python!
    INHBT1 = deepcopy(
        inputB_dict["ZZLD"]["ID"][:, 2]
    )  # BEG WK: Beginning week of the Forbidden Period.
    INHBT1 -= 1  # 0-based index in Python!
    INHBT2 = deepcopy(
        inputB_dict["ZZLD"]["ID"][:, 3]
    )  # END WK: Ending week of the Forbidden Period.
    INHBT2 -= 1  # 0-based index in Python!

    # BN: a helper array storing area related info.
    BN = np.zeros((NOAREA, 5))

    if FU.any():
        NORR = 3 - 1  # 0-based index in Python
        NFCST = 5
    else:
        NORR = 1 - 1  # 0-based index in Python
        NFCST = 1

    BN[:, 0] = [i for i in range(NOAREA)]
    BN[:, 1] = 0
    BN[:, 2] = 0
    BN[:, 3] = deepcopy(inputB_dict["ZZLD"]["RATES"][:, 2])  # Sum of Flows Constraint.
    BN[:, 4] = deepcopy(inputB_dict["ZZLD"]["RATES"][:, 2])  # Sum of Flows Constraint.

    # SUSTAT: An area-related 2D array holding annual peak (MW) and certain statistics
    # Note: its last row is kept for the usage of final total statistics.
    SUSTAT = np.zeros((NOAREA + 1, 6))
    SUSTAT[:NOAREA, 0] = deepcopy(inputB_dict["ZZLD"]["RATES"][:, 0])

    # FCTERR: tiers of load-power forecasting errors
    FCTERR = np.zeros((NOAREA, 5))  #
    FCTERR[:, 2] = 1.0
    FCTERR[:, 3] = 1.0 - FU / 100.0
    FCTERR[:, 1] = 1.0 + FU / 100.0
    FCTERR[:, 0] = 1.0 + FU * 2.5 / 100.0
    FCTERR[:, 4] = 1.0 - FU * 2.5 / 100.0

    # --------------------------------------------------------------
    # Read ZZUD card (gen. unit data) and create appropriate arrays.
    # please refer to the 'variable description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    NUNITS = len(inputB_dict["ZZUD"]["SNRI"])
    CAPOWN = np.zeros((NOAREA, NUNITS))  # capacity ownership shares
    CAPCON = np.zeros((NUNITS,), dtype=int)  # capacity ownrship condition
    NOGEN = np.zeros((NOAREA,), dtype=int)  # number of gen units
    PROBG = np.zeros((NUNITS, 2))  # sampling probabilities of gen.unit capacities
    DERATE = np.zeros((NUNITS,))  # derated unit power

    CAPCON[inputB_dict["ZZUD"]["NAT"]] = deepcopy(inputB_dict["ZZUD"]["NAR"])
    CAPOWN[inputB_dict["ZZUD"]["NAR"], inputB_dict["ZZUD"]["NAT"]] = 1
    NOGEN = np.bincount(inputB_dict["ZZUD"]["NAR"])
    PROBG[:, 0] = 1 - inputB_dict["ZZUD"]["HRLOAD"][[4, 5], :].sum(axis=0)
    PROBG[:, 1] = 1 - inputB_dict["ZZUD"]["HRLOAD"][5, :]
    DERATE = 1 - inputB_dict["ZZUD"]["HRLOAD"][6, :] / 100.0

    # --------------------------------------------------------------
    # Read contract interchanges between areas and create appropriate arrays.
    # please refer to the 'variable description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    # JENT(J1,J2)-- matrix indicating areas which have interchange
    # if "-1", means none (use "0" here will cause bug since "0-based array index" in Python)
    # otherwise, means the integer index L used in INTCH(L,N).
    JENT = -1 * np.ones((NOAREA, NOAREA), dtype=int)
    MAX_CONTRACTS = 60  # the maximum possible count of fixed contracts; can be adjusted

    # INTCH(L,N): contract interchanges MW between areas indicated by pointer L, day N.
    INTCH = np.zeros((MAX_CONTRACTS, 365))
    # INTCHR: recording the from and to area no. for each contract
    INTCHR = np.zeros((MAX_CONTRACTS, 2))
    if inputB_dict["ZZFC"] and len(inputB_dict["ZZFC"]["SNRI"]) > 0:
        for i, (src, dst) in enumerate(
            dict.fromkeys(zip(inputB_dict["ZZFC"]["NAR"]), inputB_dict["ZZFC"]["NAE"])
        ):
            JENT[src, dst] = i
            INTCHR[i, :] = src, dst
            beg_day, end_day = (
                inputB_dict["ZZFC"]["BEG DAY"][i],
                inputB_dict["ZZFC"]["END DAY"][i],
            )
            INTCH[i, beg_day : end_day + 1] = inputB_dict["ZZFC"]["MW"][i]

    # --------------------------------------------------------------
    # Read ownership of units and create appropriate arrays.
    # please refer to the 'variable description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    if inputB_dict["ZZOD"] and len(inputB_dict["ZZOD"]["SNRI"]) > 0:
        for i in range(len(inputB_dict["ZZOD"]["SNRI"])):
            for j in range(NOAREA):  # CAPOWN.shape = (NOAREA, NUNITS)
                genUnitIdx = inputB_dict["ZZOD"]["NAT"][i]
                # CAPOWN(j,i),i.e.,the fraction of unit i owned by area j
                CAPOWN[j, genUnitIdx] = inputB_dict["ZZOD"]["PERCENT"][i, j] / 100.0

    # --------------------------------------------------------------
    # Read line data and create appropriate arrays.
    # please refer to the 'varaible description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    NLINES = len(inputB_dict["ZZTD"]["SNRI"])  # total number of lines
    # LINENO(j1,j2) line number between area j1 and j2.
    LINENO = (-1) * np.ones((NOAREA, NOAREA), dtype=int)
    # LP is a helper array for storing line related parameters
    LP = (-1) * np.ones((NLINES, 3), dtype=int)
    LP[:, 0] = deepcopy(inputB_dict["ZZTD"]["LineID"])  # idx (int) for the line
    LP[:, 1] = deepcopy(inputB_dict["ZZTD"]["NAR"])  # idx (int) for 'from area'
    LP[:, 2] = deepcopy(inputB_dict["ZZTD"]["NAE"])
    LINENO[LP[:, 1], LP[:, 2]] = LP[:, 0]  # idx (int) for 'to area'

    # Convert discrete probability to cumulative probability
    # PROBL(k,l) cumulative probability that line l is in state k, k=0,...5
    PROBL = np.add.accumulate(inputB_dict["ZZTD"]["PROBT"].T)

    BLPA = np.zeros((NLINES, 18))
    BLPA[:, ::3] = deepcopy(inputB_dict["ZZTD"]["ADM"])
    BLPA[:, ::3][BLPA[:, ::3] == 0] = -0.5
    BLPA[:, 1::3] = deepcopy(inputB_dict["ZZTD"]["CAP"])
    BLPA[:, 1::3][BLPA[:, 1::3] == 0] = 1
    BLPA[:, 2::3] = deepcopy(inputB_dict["ZZTD"]["CAPR"])
    BLPA[:, 2::3][BLPA[:, 2::3] == 0] = 1

    # Read critical unit data and create appropriate arrays.
    # please refer to the 'variable description list.xlsx' file at
    # https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    MXCRIT = 0  # total (maximum) number of critical units
    JCRIT = -1 * np.ones(MXCRIT)  # critical (affecting) unit id

    # Create array 'ID':
    NUNITS = len(PROBG)
    ID = np.zeros((NUNITS, 8), dtype=int)
    ID[:, 0] = deepcopy(inputB_dict["ZZUD"]["NAT"])
    ID[:, 1] = deepcopy(inputB_dict["ZZUD"]["NAT"])
    ID[:, 2] = deepcopy(inputB_dict["ZZUD"]["NAR"])
    ID[:, 3] = deepcopy(inputB_dict["ZZUD"]["ID"][:, 1]) - 1  # to 0-based index
    ID[:, 4] = deepcopy(inputB_dict["ZZUD"]["ID"][:, 2])
    ID[:, 5] = deepcopy(inputB_dict["ZZUD"]["ID"][:, 3]) - 1  # to 0-based index
    ID[:, 6] = deepcopy(inputB_dict["ZZUD"]["ID"][:, 4])
    ID[:, 7] = deepcopy(inputB_dict["ZZUD"]["ID"][:, 0])

    NLS = inputB_dict["ZZMC"]["NLS"]  # indicator of load sharing mode
    IOI = inputB_dict["ZZMC"]["IOI"]
    IOJ = inputB_dict["ZZMC"]["IOJ"]
    KVLOC = inputB_dict["ZZMC"]["KVLOC"] - 1  # 0-based index in Python
    KVSTAT = inputB_dict["ZZMC"]["KVSTAT"]
    KVTYPE = inputB_dict["ZZMC"]["KVTYPE"]
    KVWHEN = inputB_dict["ZZMC"]["KVWHEN"]
    KWHERE = inputB_dict["ZZMC"]["KWHERE"]
    CVTEST = inputB_dict["ZZMC"]["CVTEST"]
    MAXEUE = inputB_dict["ZZMC"]["MAXEUE"]
    JSTEP = int(inputB_dict["ZZMC"]["JSTEP"])
    JFREQ = int(inputB_dict["ZZMC"]["JFREQ"])
    FINISH = inputB_dict["ZZMC"]["FINISH"] * 8760.0
    INTV = inputB_dict["ZZMC"]["INTV"]
    INTVT = INTV

    return (
        QTR,
        NORR,
        NFCST,
        NOAREA,
        PKLOAD,
        FU,
        MINRAN,
        MAXRAN,
        INHBT1,
        INHBT2,
        BN,
        SUSTAT,
        FCTERR,
        CAPCON,
        CAPOWN,
        NOGEN,
        PROBG,
        DERATE,
        JENT,
        INTCH,
        INTCHR,
        LP,
        LINENO,
        PROBL,
        BLPA,
        MXCRIT,
        JCRIT,
        ID,
        NLS,
        IOI,
        IOJ,
        KVLOC,
        KVSTAT,
        KVTYPE,
        KVWHEN,
        KWHERE,
        CVTEST,
        MAXEUE,
        JSTEP,
        JFREQ,
        FINISH,
        INTV,
        INTVT,
    )
