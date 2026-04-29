Summary
-------

Reliability performance is the most important criteria for any electric power system
planning and operation activity to comply with.  This becomes increasingly challenging
as more intermittent energy resources are added to the system with an accelerated pace
of the retirement of fossil fuel generation. In addition, more frequent extreme weather
events and climate change also leads to more severe blackouts, as measured by both the
time duration of the blackout and the magnitude of affected demand. Understanding the
reliability performance of the existing system and accordingly planning for a reliable
future energy system requires a comprehensive reliability assessment module with
flexible demand and variable generation that can assess the fundamental elements of a
system’s reliability, including:

+ Generator’s availability and capacity contribution to system adequacy;
+ System resource balancing capability to satisfy demand needs with renewable generation;
+ Risk of load interruptions under modeled events and outages.

The objective of this project is to develop and translate an add-on module embedded
into the modeling framework to enable the simulation of reliability performance metrics
of an electric system’s transmission and generation equipment to identify future
planning needs. Underlying this project is the reliability assessment currently used as
the industry standard – General Electric’s Multi Area Reliability Simulation (GE-MARS).
GE-MARS calculates reliability performance indices in a multi-area interconnected
electric power system to evaluate system risk and guide generation capacity planning.
The program is based on a Monte Carlo simulation approach to reflect the effects of
random events such as generator and transmission link failures as well as deterministic
operating rules and policies. The original concept and codes came from
Prof. Chanan Singh, currently at Texas A&M University. This project ports an original
Fortran-based power system reliability assessment program ('NARP') into a modern
language (Python and Julia) and publishes it as an open-source tool as the final
deliverable, not only for industry application but also for the research community
to continue building upon.
