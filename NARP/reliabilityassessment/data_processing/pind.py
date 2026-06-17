from copy import deepcopy

import numpy as np


def pind(inputB_dict):
    """
    Mapping name strings (of the areas, gen units, transmission link (lines)) to integer (indices)

    :param dict inputB_dict: resulted dictionary from :py:func: `readInputB`

    :return: (*dict*) inputB_dict_nameToInt -- A dictionary storing the same content as the 'inputB_dict',
                         except that all string-type 'names' are mapped to interger indices
                         based on their showing orders in the original INPUTB file.
    """
    inputB_dict_nameToInt = deepcopy(inputB_dict)

    # For ZZLD:
    NAR = inputB_dict_nameToInt["ZZLD"]["NAR"]
    unique_list = list(dict.fromkeys(NAR))
    map_AreaNameToInt = dict(zip(unique_list, range(len(unique_list))))
    inputB_dict_nameToInt["ZZLD"]["NAR"] = np.array(
        [map_AreaNameToInt[key] for key in NAR]
    )

    # For ZZUD:
    NAT = inputB_dict_nameToInt["ZZUD"]["NAT"]
    unique_list = list(dict.fromkeys(NAT))
    map_GenUnitNameToInt = dict(zip(unique_list, range(len(unique_list))))
    inputB_dict_nameToInt["ZZUD"]["NAT"] = np.array(
        [map_GenUnitNameToInt[key] for key in NAT]
    )

    NAR = inputB_dict_nameToInt["ZZUD"]["NAR"]
    inputB_dict_nameToInt["ZZUD"]["NAR"] = np.array(
        [map_AreaNameToInt[key] for key in NAR]
    )

    # For ZZTD:
    inputB_dict_nameToInt["ZZTD"]["LineID"] -= 1

    NAR = inputB_dict_nameToInt["ZZTD"]["NAR"]
    inputB_dict_nameToInt["ZZTD"]["NAR"] = np.array(
        [map_AreaNameToInt[key] for key in NAR]
    )

    NAE = inputB_dict_nameToInt["ZZTD"]["NAE"]
    inputB_dict_nameToInt["ZZTD"]["NAE"] = np.array(
        [map_AreaNameToInt[key] for key in NAE]
    )

    # For ZZFC:
    NAR = inputB_dict_nameToInt["ZZFC"]["NAR"]
    inputB_dict_nameToInt["ZZFC"]["NAR"] = np.array(
        [map_AreaNameToInt[key] for key in NAR]
    )

    NAE = inputB_dict_nameToInt["ZZFC"]["NAE"]
    inputB_dict_nameToInt["ZZFC"]["NAE"] = np.array(
        [map_AreaNameToInt[key] for key in NAE]
    )

    # For ZZOD:
    NAT = inputB_dict_nameToInt["ZZOD"]["NAT"]
    inputB_dict_nameToInt["ZZOD"]["NAT"] = np.array(
        [map_GenUnitNameToInt[key] for key in NAT]
    )

    return inputB_dict_nameToInt
