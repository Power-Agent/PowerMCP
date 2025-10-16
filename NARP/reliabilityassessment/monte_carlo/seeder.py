import numpy as np


def seeder(JSEED, NUNITS, NLINES):
    """
    Initialize the lists of random number seeds for generator units and lines.

    :param int JSEED:  the random number seed
    :param int NUNITS: the total number of generator units
    :param int NLINES: the total number of lines
    :return: (*tuple*) -- IGSEED: list of seeded random numbers for generator state
        sampling; ILSEED: list of seeded random numbers for line state sampling
    """
    IGSEED = np.zeros(1 + NUNITS, dtype=np.int32)
    ILSEED = np.zeros(1 + NLINES, dtype=np.int32)
    # Seeding random number for Each Generator
    IGSEED[0] = JSEED
    for i in range(NUNITS):
        IGSEED[i] = IGSEED[i] * 9649599
        if IGSEED[i] < 0:
            IGSEED[i] += 2147483647
            IGSEED[i] += 1
        j = i + 1
        IGSEED[j] = IGSEED[i]

    # Continue, seeding Lines
    ILSEED[0] = IGSEED[NUNITS - 1]
    for i in range(NLINES):
        ILSEED[i] = ILSEED[i] * 9649599
        if ILSEED[i] < 0:
            ILSEED[i] += 2147483647
            ILSEED[i] += 1
        j = i + 1
        ILSEED[j] = ILSEED[i]

    return IGSEED, ILSEED
