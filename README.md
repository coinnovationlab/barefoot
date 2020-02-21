# Barefoot

Barefoot is an open source Java library for online and offline map matching with OpenStreetMap, developed by the BMW car's IT department.\
This fork is part of an experiment that uses Barefoot to match bus routes defined in GTFS files to OpenStreetMap's road map.

This README file describes the additions and changes made to the original library and how to use it to map-match GTFS bus routes. You can find more information on Barefoot in the [original README file](barefoot_README.md).


## Map-matching for buses

The goal of this fork is to experiment the results of using Barefoot to map-match the data on bus routes contained in **GTFS files** to OpenStreetMap's road map.

Barefoot was designed for cars. Some roads are restricted to buses and cannot be traversed by cars. Similarly, some one-way streets have a lane dedicated to public transport vehicles that allows them to travel the opposite way.\
Changes were made to the original library so that the aforementioned streets may be traversed properly by buses.

Barefoot expects its input files to be GPS coordinates recorded by a vehicle. GTFS files contain coordinates often inserted by hand by drawing on a map, that may be used to fake GPS coordinates for Barefoot to use.

Two files in the standard are of particular interest:
- **shapes.txt**, containing the coordinates of points that make up bus routes
- **stops.txt**, containing the coordinates of where stops are placed

While it may seem more logical to use *shapes.txt* to map-match the bus route, after some initial experiments it was decided to use *stops.txt* instead.

As both files contain imprecise coordinates that place points only roughly in the right spot, *stops.txt* files tend to generate less errors, as less points are present.\
In addition, *shapes.txt* files often contain points on the "elbows" of turns as well as roundabouts, where imprecise placement is highly likely to generate (sometimes major) errors. Bus stops are very unlikely to be placed in such spots and tend to be located in straight segments of the route, allowing for a smoother reconstruction of the actual path.
Finally, *shapes.txt* is not always present, as the standard considers it optional.


## Requirements

Before executing the map-matching procedure, some files need to be provided and some need to be configured.

The files that need to be provided are GTFS files and an extract of OpenStreetMap's data of the surrounding area.

GTFS files can generally be obtained from the official website of the municipality. They usually come as an archive that contains multiple *.txt* files. Only the following 3 files are actually needed for map-matching bus routes:
- **stop_times.txt**
- **stops.txt**
- **trips.txt**

It is however better if **shapes.txt** is also available, as it makes evaluating the results of map-matching easier.
