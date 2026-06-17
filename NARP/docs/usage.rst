Running the Program
-------------------

Before running the program, the user needs to prepare several raw input files which
defines the system for reliability assessment and certain simulation settings. These
inputs are described below in :numref:`major_input` and are defined in a csv file
format except for the LEEI file which defines the load profile data and that follows
the classic EEI format that has been used in many industry applications like PROMOD.
A simulation-ready example is available for reference in
**reliabilityassessment/data_processing/tests/**

The program has automatic error checking for data anomalies to improve the
robustness of user defined inputs given the simulation needs. There are other
miscellaneous inputs that are needed for simulation settings or for changing the case
definition (file **InputC**), which are all included in the tests. Below are
descriptions focusing on the data inputs for the modeled system. Please note that
among all the inputs, ZZMC, ZZUD, ZZLD, ZZTD, and ZZTC are required to run a
simulation while others are optional.

.. _major_input:

.. table:: Major input data on model system

    +-------+--------+------------------------------------------------------------+
    | Input | Format | Description                                                |
    +=======+========+============================================================+
    | ZZTC  | csv    | Simulation title card                                      |
    +-------+--------+------------------------------------------------------------+
    | ZZLD  | csv    | System data, including:                                    |
    |       |        | Area name;                                                 |
    |       |        | Peak demand;                                               |
    |       |        | Forecast uncertainty;                                      |
    |       |        | Outage window;                                             |
    |       |        | Forbidden period;                                          |
    |       |        | Flow constraints.                                          |
    +-------+--------+------------------------------------------------------------+
    | ZZUD  | csv    | Unit data, including:                                      |
    |       |        | Unit Name;                                                 |
    |       |        | Serial number;                                             |
    |       |        | Location;                                                  |
    |       |        | Capacity;                                                  |
    |       |        | Outage rate;                                               |
    |       |        | Derated outage rate;                                       |
    |       |        | Percentage derating due to partial failure;                |
    |       |        | Option to predetermine or auto-schedule;                   |
    |       |        | Beginning week and Duration of the first and second weeks. |
    +-------+--------+------------------------------------------------------------+
    | ZZFC  | csv    | Firm contracts, specifying the firm interchanges of power  |
    |       |        | between areas.                                             |
    +-------+--------+------------------------------------------------------------+
    | ZZOD  | csv    | Unit ownership data in percentage                          |
    +-------+--------+------------------------------------------------------------+
    | ZZTD  | csv    | Line data, including:                                      |
    |       |        | Location of areas;                                         |
    |       |        | Admittance (negative number);                              |
    |       |        | Capacity of the line in the forward direction;             |
    |       |        | Capacity of the line in the reverse direction;             |
    |       |        | Probability of the line in each state (six states in total |
    |       |        | for each line)                                             |
    +-------+--------+------------------------------------------------------------+
    | ZZDD  | csv    | Line derating data.                                        |
    +-------+--------+------------------------------------------------------------+
    | ZZMC  | csv    | Miscellaneous program settings, including:                 |
    |       |        | Seed (Loss sharing included);                              |
    |       |        | Definition of seasons;                                     |
    |       |        | Convergence test parameters;                               |
    |       |        | Frequency of drawing of the status of generators and       |
    |       |        | transmission lines, either daily or hourly;                |
    |       |        | Frequency of data collection, either daily peak or hourly; |
    |       |        | Specifications for the probability distribution of EUE     |
    |       |        | (e.g.upper limit);                                         |
    |       |        | Printout options.                                          |
    +-------+--------+------------------------------------------------------------+
    | LEEI  | EEI    | Load profile data.                                         |
    +-------+--------+------------------------------------------------------------+

Unlike other modules, the modeling framework is not required to execute this module as
a standalone reliability assessment analysis. However, it is recommended to have a
complete energy system simulation package to accommodate the reliability module as a
key piece of an overall planning study;

Similar to GE-MARS or other industry simulation application, this module is area-based,
meaning that it is designed for zonal reliability analysis. Nodal models with full
granularity need to be translated into zonal scale first in order to be able to use
this module.

After preparing all the required inputs, navigate to the folder where all input data
are files, specify the path and run:

.. code::

    INPUT_DIR = "absolute path of the input data”
    narp_main(INPUT_DIR).

The command triggers input data processing function ``dataf1`` followed by Monte-Carlo
function``contrl``. Data processing is a one-time processing while Monte-Carlo is a
repeated iterations thus convergence needs to be watched. While the program is
progressing, it will report the iteration convergence index information in the
terminal as shown below:

.. code::

    n-th REPLICATION; SUM=143.0 NEW=0.0 MEAN=0.43202416918429004 CONVERGENCE=3.702682434420153

When the ``CONVERGENCE`` index number drops to below than 1, it indicates that the
program has reached convergence tolerance and finished evaluation. If it won’t reduce
to less than 1 within defined number of iterations, it indicates that either the system
has issues, or the simulation needs to be checked. The user should follow the below
steps to identify the problem and solutions:

1. Increase number of max iteration limit (default to 9999) and re-run;
2. If it converges, stop and check results. If it still not converges, keep increasing
   iteration limit until it is reasonably large;
3. If it won’t converge with a reasonably large max # of iterations, check input data
   and look for anomalies;
4. If input data is correct without anomalies, then it indicates the system may have
   significant reliability problems that block the program from converging. Sometimes
   there may be numeric issues within the simulation rather than real system problems
   that the user may need to further verify before using the results.

After the running is finished and converged successfully, a txt file will be
generated in the root directory. The contains  reliability statistics for all the
areas are printed out in a table format.

The Expected outputs from the program will mainly include three parts:

+ Unit planned maintenance generated with Monte-Carlo simulation. This measures the
  expected availability of generation units in each area, and can be used as an input
  for follow-up studies or simulations to support generation planning.
+ Reliability indices measuring the risk of interruptions serving load for each area
  of the system: LOLE (Loss of Load Expectations), Hourly LOLE (HLOLE in short), EUE
  (Expected Unserved Energy, in kWh or MWh) for electric systems.
+ Probability distribution histogram of outage events for each area. This indicates
  the severity and probability of outages and is a key metric of risk-based
  reliability planning studies.

