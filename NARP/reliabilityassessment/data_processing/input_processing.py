from copy import deepcopy

from reliabilityassessment.data_processing.datax import datax
from reliabilityassessment.data_processing.dpeak import dpeak
from reliabilityassessment.data_processing.plhr import plhr
from reliabilityassessment.data_processing.resca import resca
from reliabilityassessment.data_processing.smaint import smaint
from reliabilityassessment.data_processing.wpeakf import wpeakf
from reliabilityassessment.data_processing.xldnew import xldnew
from reliabilityassessment.data_processing.xporta import xporta
from reliabilityassessment.data_processing.xports import xports


def input_processing(inputB_dict_nameToInt, filePathToLEEI, NAMU, NUMP):
    """
    Apply further pre-processing on the loaded data and create/update certain arrays.

    :param dict inputB_dict_nameToInt: a compound dictionary stores all the parsed
        data from the INPUTB file
    :param str filePathToLEEI: path to file 'LEEI'
    :param list NAMU: list of strings, gen unit names
    :param list NUMP: list of strings, gen plant names
    :return: (*tuple*) -- a series of numpy arrays

    .. note:: detailed variable info see ``variable description list.xlsx`` at
        https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0
    """

    (
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
    ) = datax(inputB_dict_nameToInt)

    RATES = deepcopy(inputB_dict_nameToInt["ZZUD"]["HRLOAD"][0:4, :].T)

    # Read the hourly load data from the file 'LEEI'
    HRLOAD = xldnew(filePathToLEEI, PKLOAD)

    # Add interchanges
    xporta(JENT, INTCH, HRLOAD)

    # Find daily peaks and hour of daily peaks
    MAXHR, DYLOAD, MAXDAY = dpeak(HRLOAD, hour_within_day=24)

    # Finds weekly peaks (MW)
    WPEAK = wpeakf(DYLOAD)

    # Find hour of pool daily peaks
    MXPLHR = plhr(HRLOAD)

    # Remove interchanges and restore hrload
    xports(JENT, INTCH, HRLOAD)

    # Calculate the total owned cap and interchange at peak
    resca(SUSTAT, MAXDAY, QTR, CAPOWN, RATES, JENT, INTCH)

    # Prepare jplout - table of planned outages of units
    # * return values are subjected to change *
    IREPM = inputB_dict_nameToInt["ZZMC"]["IREPM"]
    ITAB = 6
    JPLOUT, ITAB = smaint(
        NOAREA,
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
    )

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
        RATES,
        ID,
        HRLOAD,
        MAXHR,
        DYLOAD,
        MAXDAY,
        WPEAK,
        MXPLHR,
        JPLOUT,
        ITAB,
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
