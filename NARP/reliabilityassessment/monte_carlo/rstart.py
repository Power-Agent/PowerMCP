import pickle


def rstart(DUMPED_file):
    """
    Load (if exists) the 'DUMP' file (previously saved intermediate data and results)
    which is used to resume the Monte Carlo Simulation in external call

    :param str DUMPED_file: file path of the pickle file storing previously obtained
        intermediate data and results
    :return: (*dict*) -- snapshot_data: a python dictionary storing previously obtained
        intermediate data and results, which contains multiple scalars, 1D and 2D
        numpy.ndarrays. For detailed description see 'variable descriptions.xlsx' at:
        https://www.dropbox.com/s/eahg8x584s9pg4j/variable%20descriptions.xlsx?dl=0

    .. note:: In external call, the returned dict object will be handled via the
        following way to load all variables into memory:
        for key, val in snapshot_data.items():
            exec(key + '=val')
        Using string evaluation is risky and this is subject to refactor in the future.
    """
    with open(DUMPED_file, "rb") as f:
        snapshot_data = pickle.load(f)

    return snapshot_data
