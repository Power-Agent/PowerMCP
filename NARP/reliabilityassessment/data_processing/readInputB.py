import os

import numpy as np
import pandas as pd


def read_card_ZZTC(filepath):
    """
    ZZTC: title card
    The purpose of this card is to provide a title in the final output. Data inserted
    under this card is simply reproduced. This is the only formatted card in this file.

    :param str filepath: root file path for input csvs.
    :return: (*string*) -- A string describes some basic information about
                            the studied power system (e.g., how many areas).
    """
    df_ZZTC = pd.read_csv(os.path.join(filepath, "ZZTC.csv"), header=None).to_numpy()
    data = ". ".join([s[0] for s in df_ZZTC])
    return data


def read_card_ZZMC(filepath):
    """
    ZZMC: miscellaneous card.

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
                         designated keys.
    """

    df_ZZMC = pd.read_csv(os.path.join(filepath, "ZZMC.csv"))
    data = dict()

    """
    The basic seed used by the program to create seeds for generators and
    transmission lines, a 7-digit integer.
    This may be useless in Python since random number can be easily generated.
    Will remove it later
    """
    data["JSEED"] = df_ZZMC["SEED"].item()  # e.g. 345237

    """
    Load-loss sharing:
    0 --"Yes"; 1 --"No"
    """
    data["NLS"] = df_ZZMC["LS"].item()  # 1

    """
    Ending weeks for the 1st (beginning week is assumed to be the 1st week),
    2nd, 3rd seasons. The ending weeks of the 4th season is assumed as 52
    """
    # e.g.  #[13, 26, 39]
    (
        data["IW1"],
        data["IW2"],
        data["IW3"],
    ) = (
        df_ZZMC["END WK1"].item(),
        df_ZZMC["END WK2"].item(),
        df_ZZMC["END WK3"].item(),
    )

    # ----------Vars for convergence test--------------
    """
    1: based on area-statistics. The area is specified by the variable KVL below
    2: based on pool statistics
    """
    data["KWHERE"] = df_ZZMC["WHERE"].item()  # e.g. 1

    """
    1: Hourly statistics are to be used for convergence
    2: Peak statistic are to be used for convergence"""
    data["KVWHEN"] = df_ZZMC["WHEN"].item()  # e.g. 1

    """
    1: LOLE is to be used for convegence
                hourly LOLE for 'WHEN = 1'
                peak LOLE for 'WHEN = 2'
    2: EUE is to be used for convegence ( for 'WHEN = 1' only)
    """
    data["KVSTAT"] = df_ZZMC["KVS"].item()  # e.g. 1

    """
    1: Weighted average statistcs (cosniderring forecast error)
       is to be used for convegence
    2: Use only the No-forecast-error statistics
    """
    data["KVTYPE"] = df_ZZMC["KVT"].item()  # e.g. 2

    """
    Area number (used only if 'WHERE'=1) for convergence
    """
    data["KVLOC"] = df_ZZMC["KVL"].item()  # e.g. 1

    """
    0: Program stops when standard deviation of the
    tested statistics < (0.025 * mean); i.e. the true value lies
    between pos/neg 5% of the estimate with confidence level at 95%.

    >0:  Program stops when standard deviation of the
    tested statistics < (CVT * mean); i.e. the true value lies
    between pos/neg (2 CVT)% of the estimate with confidence level at 95%.
    """
    data["CVTEST"] = df_ZZMC["CVT"].item()  # e.g. 0.025

    """
    Time to terminate simulation if no convergence.
    Should be an INT type (years)
    """
    data["FINISH"] = df_ZZMC["FIN"].item()  # e.g. 9999

    # ---- Other variables
    """
    1:  Stats are collected every hour
    24: Daily peak stats only are collected
    """
    data["JSTEP"] = df_ZZMC["STEP"].item()  # e.g. 1

    """
    1:  Hourly Monte Carlo draws of generator ;and line status are used
    24: Daily Monte Carlo draws are used
    """
    data["JFREQ"] = df_ZZMC["FREQ"].item()  # e.g. 1

    """
    Defines the upper limit of the prob distribution of
    Expected unserved Energy, in MWHRS.
    Note: the original Fortran code set it as int type,
    but float type is used here since it may be more reasonable
    """
    data["MAXEUE"] = df_ZZMC["MAXE"].item()  # e.g. 1000

    """
    0: Transmission mod results are not printed.
    1: Transmission mod results are printed into file TRAOUT.
    """
    data["IOI"] = df_ZZMC["II"].item()  # e.g. 0

    """
    0: Only final statistics are printed.
    1: In addition to final statistics, results after each
       replication are also printed.
    """
    data["IOJ"] = df_ZZMC["IJ"].item()  # e.g. 0

    """
    0: Delete DUMP after the run.
    1: Retain DUMP after the run.
    """
    data["IREM"] = df_ZZMC["IR"].item()  # e.g. 1

    """
    Interval, in number of replications, for storing
    """
    data["INTV"] = df_ZZMC["IN"].item()  # e.g. 5

    """
    0: Input data from INPUTB and INPUTC is not printed.
    1: Input data is printed."""
    data["IREPD"] = df_ZZMC["D"].item()  # 1

    """
    0: Planned outage schedules are not printed.
    1: Planned outage schedules are printed.
    """
    data["IREPM"] = df_ZZMC["M"].item()  # e.g. 1

    return data


def read_card_ZZLD(filepath):
    """
    ZZLD: system data card
    Area names are given in four letters. The purpose of this card is to specify
    data applicable to a given area.

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
        designated keys.
    """
    df_ZZLD = pd.read_csv(os.path.join(filepath, "ZZLD.csv"))
    data = dict()

    RATES = np.zeros((len(df_ZZLD), 3))
    ID = np.zeros((len(df_ZZLD), 4)).astype(int)

    """
    Serial Number.
    The serial number in this and subsequent types of cards identifies
    each entry uniquely and specifies the sequence of data entries.
    After reading, the data entries are arranged by the program in the
    sequence specified under SN. The serial number can have up to three
    decimal places. This he.lps in deleting lines and inserting new lines
    through INPUTC file.
    """
    data["SNRI"] = df_ZZLD["SN"].astype(int).to_numpy()

    """
    The name of the area. It can have up to four letters and
    must be enclosed by quotes.
    """
    data["NAR"] = df_ZZLD["AREA NAME"].to_numpy()

    """
    Annual peak in the area, in MW.
    """
    RATES[:, 0] = df_ZZLD["PEAK (MW)"].to_numpy()

    """
    Load forecast uncertainty (LFU).
    One standard deviation expressed as percentage of the mean
    """
    RATES[:, 1] = df_ZZLD["LFU"].to_numpy()

    """
    Outage Window.
    The weeks during which planned maintenance can be performed.
        BEG WK: Beginning week of the outage window
        END WK: Ending week of the outage window
    """
    ID[:, 0], ID[:, 1] = (
        df_ZZLD["OUTAGE BEG WK"].to_numpy(),
        df_ZZLD["OUTAGE END WK"].to_numpy(),
    )

    """
    Forbidden Period.
    A part of the outage window during which planned maintenance
    is NOT allowed.
        BEG WK: Beginning week of the Forbidden Period.
        END WK: Ending week of the Forbidden Period.
    """
    ID[:, 2], ID[:, 3] = (
        df_ZZLD["FORBIDDEN BEG WK"].to_numpy(),
        df_ZZLD["FORBIDDEN END WK"].to_numpy(),
    )

    """
    Sum of Flows Constraint.
    The algebraic sum of flows at this node is not to exceed this value.
    """
    RATES[:, 2] = df_ZZLD["SUM OF FLOWS CONSTRAINT"].to_numpy()

    data["RATES"] = RATES
    data["ID"] = ID

    return data


def read_card_ZZUD(filepath):
    """
    ZZUD: generator unit data card

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
        designated keys.
    """

    df_ZZUD = pd.read_csv(os.path.join(filepath, "ZZUD.csv"))
    data = dict()

    # Note: the original Fortran code set the HRLOAD array as INT type;
    # Here, I use float type for it.
    HRLOAD = np.zeros((7, len(df_ZZUD)))
    ID_ZZUD = np.zeros((len(df_ZZUD), 5)).astype(int)

    """
    Serial number (refet to ZZLD)
    """
    data["SNRI"] = df_ZZUD["SN"].astype(int).to_numpy()

    """
    Unit name is six alphanumeric characters. The first four letters are the plant
    number and the next two numbers identify the unit.
    """
    data["NAT"] = df_ZZUD["NAME"].to_numpy()

    """
    Area of location
    """
    data["NAR"] = df_ZZUD["LOC"].to_numpy()

    """
    Unit capacity, MW, in the ith season (see ZZLD)
    """
    # CAP1, CAP2, CAP3, CAP4
    HRLOAD[0, :], HRLOAD[1, :], HRLOAD[2, :], HRLOAD[3, :] = (
        df_ZZUD["CAP1"].to_numpy(),
        df_ZZUD["CAP2"].to_numpy(),
        df_ZZUD["CAP3"].to_numpy(),
        df_ZZUD["CAP4"].to_numpy(),
    )

    """
    Derated forced outage rate (DFOR)
    """
    HRLOAD[4, :] = df_ZZUD["DFOR"].to_numpy()

    """
    Forced outage rate(FOR)
    """
    HRLOAD[5, :] = df_ZZUD["FOR"].to_numpy()

    """
    Percent derating (DER) due to partial failure. This is
    different from the seasonal derating which can be
    specified using CAPI.
    """
    HRLOAD[6, :] = df_ZZUD["DER"].to_numpy()

    """
    Predetermined (1) or automatic (0) scheduling.
    """
    ID_ZZUD[:, 0] = df_ZZUD["P/A"].to_numpy()

    # Notes:
    #    1. In scheduling the planned outages, the program does not
    #       take out two units belonging to one plant at the same
    #       time. Also the program can accept up to two planned
    #       outages per year for each unit.

    #    2. The program schedules units for planned outage by
    #       adjusting them into valleys in the load cycle. Therefore
    #       for any area having only generation, planned outages must
    #       be predetermined by the user.
    #
    #    3. If the program cannot schedule a unit in the automatic
    #       mode, it will print a message to indicate this and
    #       schedule the unit using B1,D1l and B2,D2 parameters.
    """
    Beginning week and duration of the first outage.
    In the automatic mode Bl is ignored.(B1, D1)
    """
    ID_ZZUD[:, 1], ID_ZZUD[:, 2] = df_ZZUD["B1"].to_numpy(), df_ZZUD["D1"].to_numpy()

    """
    Beginning week and duration of second outage. In
    the automatic mode, B2 is ignored.(B2, D2)
    """
    ID_ZZUD[:, 3], ID_ZZUD[:, 4] = df_ZZUD["B2"].to_numpy(), df_ZZUD["D2"].to_numpy()

    data["ID"] = ID_ZZUD
    data["HRLOAD"] = HRLOAD

    return data


def read_card_ZZTD(filepath):
    """
    ZZTD: line data card
    The purpose of this card is to specify the data for transmission links.

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
        designated keys.
    """

    df_ZZTD = pd.read_csv(os.path.join(filepath, "ZZTD.csv"))
    data = dict()

    ADM = np.zeros((len(df_ZZTD), 6))
    CAP, CAPR = np.zeros((len(df_ZZTD), 6)), np.zeros((len(df_ZZTD), 6))
    PROBT = np.zeros((len(df_ZZTD), 6))

    """
    Serial number
    """
    data["SNRI"] = df_ZZTD["SN"].to_numpy()

    """
    Line Id
    """
    data["LineID"] = df_ZZTD["LINE NUMBER"].to_numpy()

    """
    Name of From area
    """
    data["NAR"] = df_ZZTD["FROM AREA"].to_numpy()

    """
    Name of To area
    """
    data["NAE"] = df_ZZTD["TO AREA"].to_numpy()

    tmp = df_ZZTD["META DATA"].to_numpy()
    for i in range(len(tmp)):
        tmp_ = np.array(list(map(float, tmp[i].strip().split(",")))).reshape((6, 4))
        ADM[i, :] = tmp_[:, 0]
        CAP[i, :] = tmp_[:, 1]
        CAPR[i, :] = tmp_[:, 2]
        PROBT[i, :] = tmp_[:, 3]

    data["ADM"] = ADM
    data["CAP"] = CAP
    data["CAPR"] = CAPR
    data["PROBT"] = PROBT

    return data


def read_card_ZZFC(filepath):
    """
    ZZFC: firm contracts data card
    This card is to specify firm interchanges of power between areas. The following
    format is used for input of these interchanges

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
        designated keys.

    ** ZZFC data is not required and is given now **.
    Default values (zero , empty , None, etc.) will be given here
    """

    df_ZZFC = pd.read_csv(os.path.join(filepath, "ZZFC.csv"))
    data = dict()

    """
    Serial number
    """
    data["SNRI"] = df_ZZFC["SN"].to_numpy()

    """
    Name of From area sending power
    """
    data["NAR"] = df_ZZFC["FROM AREA"].to_numpy()

    """
    Name of To area receiving power
    """
    data["NAE"] = df_ZZFC["TO AREA"].to_numpy()

    """
    Beginning and ending days (1 to 365) of the contract.
    """
    data["BEG DAY"] = df_ZZFC["BEG DAY"].to_numpy()
    data["END DAY"] = df_ZZFC["END DAY"].to_numpy()

    """
    Exchanged power (MW) of the firm interchange (power) during the period.
    """
    data["MW"] = df_ZZFC["MW"].to_numpy()

    return data


def read_card_ZZOD(filepath):
    """
    ZZOD: unit ownership data card
    This card is to specify the joint ownership of a unit by several areas.

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
        designated keys.

    ** ZZOD data is NOT required and is not given now **.
    Default values (zero , empty , None, etc.) will be used here
    """

    df_ZZOD = pd.read_csv(os.path.join(filepath, "ZZOD.csv"))
    data = dict()

    """
    Serial number
    """
    data["SNRI"] = df_ZZOD["SN"].to_numpy()

    """
    Name of the (jointly owned) unit
    """
    data["NAT"] = df_ZZOD["UNIT NAME"].to_numpy()

    """
    Percentage ownership by each area
    """
    data["PERCENT"] = df_ZZOD["PERCENT OWNED BY AREA"].to_numpy()

    return data


def read_card_ZZDD(filepath):
    """
    ZZDD: line derarting data card
    Status of certain units can effect the line rating. For a given line, four units
    can be specified in a combination such that if all the units in the combination
    are down, then the line ratings will be multiplied by the derating factors. For
    a given line, more than one combination can be specified.

    :param str filepath: root file path for input csvs.
    :return: (*dict*) -- a dictionary contains info from the raw dataframe with
        designated keys.

    ** ZZDD data is NOT required and is not given now **.
    Default values (zero , empty , None, etc.) will be used here
    """

    df_ZZDD = pd.read_csv(os.path.join(filepath, "ZZDD.csv"))
    data = dict()

    """
    Serial number
    """
    data["SNRI"] = df_ZZDD["SN"].to_numpy()

    """
    Line number
    """
    data["LineID"] = df_ZZDD["LINE NUMBER"].to_numpy()

    """
    Four related generator unit name
    """
    data["unit1_name"] = df_ZZDD["UNIT1"].to_numpy()
    data["unit2_name"] = df_ZZDD["UNIT2"].to_numpy()
    data["unit3_name"] = df_ZZDD["UNIT3"].to_numpy()
    data["unit4_name"] = df_ZZDD["UNIT4"].to_numpy()

    """
    Derate factors
    """
    data["forward_derate"] = df_ZZDD["FORWARD"].to_numpy()
    data["backward_derate"] = df_ZZDD["BACKWARD"].to_numpy()

    return data


def readInputB(filepath):
    """read and parse raw text data from csv files.

    :param str filepath: root file path for input csvs.

    :return: (*dict*) -- A nested Python dictionary for each data card (INPUTB file).
        Originally, each data card contains either a single value or multiple arrays.
    """
    inputB_dict = dict()
    inputB_dict["ZZTC"] = read_card_ZZTC(filepath)
    inputB_dict["ZZMC"] = read_card_ZZMC(filepath)
    inputB_dict["ZZLD"] = read_card_ZZLD(filepath)
    inputB_dict["ZZUD"] = read_card_ZZUD(filepath)
    inputB_dict["ZZTD"] = read_card_ZZTD(filepath)
    inputB_dict["ZZFC"] = read_card_ZZFC(filepath)
    inputB_dict["ZZOD"] = read_card_ZZOD(filepath)
    inputB_dict["ZZDD"] = read_card_ZZDD(filepath)

    return inputB_dict
