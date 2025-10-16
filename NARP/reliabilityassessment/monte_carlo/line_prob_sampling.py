import math

import numpy as np


def lstate(PROBL, test_seed=None):
    """Establish the line state according the probability of the line being in
    each particular state. This vectorized implementation allows the line state
    probabilities to be different for each line, and assumes that the lines can be
    in up to 6 states overall.

    :param numpy.ndarray PROBL: cumulative capacity probability of each line
    :raises TypeError: if PROBL is not a numpy array
    :return: (*numpy.ndarray*) -- line state value (in integer) of each line
    """
    if not isinstance(PROBL, np.ndarray):
        raise TypeError("PROBL must be a numpy array")

    NLINES = PROBL.shape[0]
    line_states = np.array([1, 2, 3, 4, 5, 6])

    # set random seed for reproducibility
    if test_seed is not None:
        rng = np.random.default_rng(seed=test_seed)
    else:
        rng = np.random.default_rng()

    rand_mat = rng.random(NLINES)
    LNSTAT = np.zeros(NLINES, dtype=np.int32)

    for i in range(line_states.size):
        mask = (LNSTAT == 0) & (rand_mat < PROBL[:, i])
        LNSTAT[mask] = line_states[i]
    return LNSTAT


def lstate_original(NLINES, PROBL, test_seed=None):
    """Establishes the line state according the probability of the line being in
    each particular state. This implementation assumes the lines can be in up to 6 states overall.

    :param int NLINES: total number of lines
    :param numpy.ndarray PROBL: array of the cumulative capacity probability of each line
    :raises TypeError:
        NLINES must be an integer
        PROBL must be a numpy array
    :raises ValueError: NLINES must be positive
    :raises Exception: PROBL values must sum to 1
    :return: (*numpy.ndarray*) -- array of line state value (in integer) of each line
    """

    if not isinstance(NLINES, int):
        raise TypeError("NLINES must be an integer")

    if not NLINES > 0:
        raise ValueError("NLINES must be positive")

    if not isinstance(PROBL, np.ndarray):
        raise TypeError("PROBL must be a numpy array")

    # set random seed for reproducibility
    if test_seed is not None:
        rng = np.random.default_rng(seed=test_seed)
    else:
        rng = np.random.default_rng()

    # recover original probabilities
    PROB = np.concatenate(([PROBL[0]], np.diff(PROBL)))
    if not math.isclose(np.sum(PROB), 1):
        raise Exception("PROB values must must sum to 1")

    LNSTAT = np.zeros(NLINES, dtype=np.int32)
    for i in range(NLINES):
        # Draw a random number for each line
        RANDL = rng.random()

        # Determine the State and Available Capacity for Each Generator.
        if RANDL <= PROBL[0]:
            LNSTAT[i] = 1
        elif RANDL <= PROBL[1]:
            LNSTAT[i] = 2
        elif RANDL <= PROBL[2]:
            LNSTAT[i] = 3
        elif RANDL <= PROBL[3]:
            LNSTAT[i] = 4
        elif RANDL <= PROBL[4]:
            LNSTAT[i] = 5
        else:
            LNSTAT[i] = 6
    return LNSTAT


def discrete_prob_gen(NLINES, PROBL, test_seed=None):
    """Establishes the line state according the probability of the line being in
    each particular state. This implementation makes use of folllowing built-in numpy
    function:
    https://numpy.org/doc/stable/reference/random/generated/numpy.random.choice.html
    This implementation assumes that the line state probabilities are the same for
    every line, and the lines can be in up to 6 states overall.

    :param int NLINES: total number of lines
    :param numpy.ndarray PROBL: array of predefined capacity probability of each line
    :raises TypeError:
        NLINES must be an integer
        PROBL must be a numpy array
    :raises ValueError: NLINES must be positive
    :raises Exception: PROBL values must sum to 1
    :return: (*numpy.ndarray*) -- array of line state value (in integer) of each line
    """

    if not isinstance(NLINES, int):
        raise TypeError("NLINES must be an integer")

    if not NLINES > 0:
        raise ValueError("NLINES must be positive")

    if not isinstance(PROBL, np.ndarray):
        raise TypeError("PROBL must be a numpy array")

    # recover original probabilities
    PROB = np.concatenate(([PROBL[0]], np.diff(PROBL)))
    if not math.isclose(np.sum(PROB), 1):
        raise Exception("PROB values must must sum to 1")

    # set random seed for reproducibility
    if test_seed is not None:
        rng = np.random.default_rng(seed=test_seed)
    else:
        rng = np.random.default_rng()

    line_states = np.array([1, 2, 3, 4, 5, 6])

    return rng.choice(line_states, NLINES, p=PROB)
