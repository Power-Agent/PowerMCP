from reliabilityassessment.data_processing.input_processing import input_processing
from reliabilityassessment.data_processing.pind import pind
from reliabilityassessment.data_processing.readInputB import readInputB


def dataf1(filepaths):
    """
    Data file reading and preprocessing

    :param list filepaths: the filepath to file 'INPUTB' and 'LEEI' respectively
    :return: (*tuple*)  -- the return values of 'input_processing' together with
        the reference bus number and the list of area names.
    """

    NR = 1 - 1  # 0-based index in Python
    inputB_dict = readInputB(filepaths[0])
    NAMU, NUMP = zip(*map(lambda x: (x[1:5], x[5:-1]), inputB_dict["ZZUD"]["NAT"]))
    NAMA = inputB_dict["ZZLD"]["NAR"]
    NAMA = [e.strip("'") + "  " for e in NAMA]
    inputB_dict_nameToInt = pind(inputB_dict)

    return input_processing(inputB_dict_nameToInt, filepaths[1], NAMU, NUMP) + (
        NR,
        NAMA,
    )
