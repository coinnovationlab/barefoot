# Barefoot

Barefoot is an open source Java library for online and offline map matching with OpenStreetMap, developed by the BMW car's IT department.\
This fork is part of an experiment that uses Barefoot to match bus routes defined in GTFS files to OpenStreetMap's road map.

This README file describes the additions and changes made to the original library and how to use it to map-match GTFS bus routes. You can find more information on Barefoot in the [original README file](barefoot_README.md).


## Map-matching for buses

The goal of this fork is to experiment using Barefoot to map-match the data on bus routes contained in **GTFS files** to OpenStreetMap's road map.

Barefoot was designed for cars. Some roads are restricted to buses and cannot be traversed by cars. Similarly, some one-way streets have a lane dedicated to public transport vehicles that allows them to travel the opposite way.\
Changes were made to the original library so that the aforementioned streets may be traversed by buses accordingly.

Barefoot expects its input files to be GPS coordinates recorded by a vehicle. GTFS files contain coordinates often inserted by hand by drawing on a map, that may be used to fake GPS coordinates for Barefoot to use.

Two files in the standard are of particular interest:
- **shapes.txt**, containing the coordinates of points that make up bus routes
- **stops.txt**, containing the coordinates of where stops are placed

While it may seem more logical to use *shapes.txt* to map-match the bus route, after some initial experiments it was decided to use *stops.txt* instead.

As both files contain imprecise coordinates that place points only roughly in the right spot, *stops.txt* files tend to generate less errors, as less points are present.\
In addition, *shapes.txt* files often contain points on the "elbows" of turns as well as roundabouts, where imprecise placement is highly likely to generate (sometimes major) errors. Bus stops are very unlikely to be placed in such spots and tend to be located in straight segments of the route, allowing for a smoother reconstruction of the actual path.


## Requirements

**Maven**, **Java** 7 or higher, **Docker** and **Python 2.7** need to be installed to run Barefoot. More details in the [original README file](barefoot_README.md).

Before executing the map-matching procedure, some files need to be provided and some need to be configured.

The files that need to be provided are GTFS files and an extract of OpenStreetMap's data of the surrounding area.


### GTFS

GTFS files can generally be obtained from official websites of municipalities or companies that offer public transportation services. They usually come as an archive that contains multiple *.txt* files. Only the following 4 files are actually needed for map-matching bus routes:
- **shapes.txt**
- **stop_times.txt**
- **stops.txt**
- **trips.txt**


### OpenStreetMap extract

An OpenStreetMap data extract is necessary, as the bus routes will be mapped to the roads contained in such extract.\
It should come as a **.osm.pbf** file and the area it covers should include all points defined in **stops.txt**.

If the area covered by the extract does not fully include all points, some routes will either not be map-matched at all or be map-matched only partially, due to no roads being found in the vicinity of points outside the extract's area.

The two following websites act as frequently-updated mirrors for OpenStreetMap extracts, with the ability to request only the street data of certain regions:
- https://download.geofabrik.de
- http://download.openstreetmap.fr/extracts/

Overpass may be used to extract small areas for testing purposes, but its use is discouraged for large areas:
- https://overpass-turbo.eu/

The following page from OpenStreetMap's wiki offers a long list of possible sources to download extracts:
- https://wiki.openstreetmap.org/wiki/Planet.osm

Try to find the smallest extract possible that fits your needs. Larger files will slow down both the preparation of Barefoot and the execution of the map-matching procedure, so it's preferable for your extract to not include large areas outside the general vicinity of GTFS points.

Regardless of the mirror used, the extract needs to be in **.osm.pbf** format. If the extract you need only comes in **.osm** format, [osmConvert](https://wiki.openstreetmap.org/wiki/Osmconvert) is easy to use and can convert it. [OSMosis](https://wiki.openstreetmap.org/wiki/Osmosis) offers a similar functionality and also allows to take a smaller portion of the roadmap, in case the extract you found was excessively large.


### Configuring Barefoot

After downloading this repository to your machine, some files need to be configured.

Place the *.osm.pbf* extract you obtained earlier inside the **/barefoot/map/osm** directory.\
Open **import.sh** from the same directory with any text editor and replace the value of `input` with the name of the *.osm.pbf* file. Save this file.

Open **/barefoot/config/busmatching.properties** with a text editor. This file contains various configurations used by the matcher server and by the Python scripts that prepare GTFS data, build geometries out of the map-matching procedure's results and allow to evaluate them.\
The only value that *must* be changed is `gtfs.path`
- `gtfs.path`: **You must change this value to the path that contains the *.txt* GTFS files you procured during the *Requirements* phase.**

If you changed any parameter (other than `input`) from *import.sh*, some properties may need to match the corresponding parameter you changed:
- `database.name`: Name of the database in the map server. The value is not important, as long as it matches the value of **database** set in *barefoot/map/osm/import.sh*. Both are set to `barefoot` as default.
- `database.user`: Root user in the map server. Must match the value of **user** set in *barefoot/map/osm/import.sh*. Both are set to `osmuser` as default.
- `database.password`: Password of root user in the map server. Must match the value of **password** set in *barefoot/map/osm/import.sh*. Both are set to `pass` as default.

Finally, if you plan on running the map server (which will run inside a Docker container) in a different machine than the one that will host the matcher server, you should change `database.host` accordingly. Otherwise, leave its value to `localhost`.
- `database.host`: Host of the map server. The map server will be started after all configurations are complete and will run inside a Docker container. If you plan on running the matcher server, as well as the Python scripts, on the same machine where the container is running, leave the `localhost` value.

Other values are used by the Python scripts contained in the *gtfs_scripts* folder and do not need to be changed. Save the *busmatching.properties* file with the edits you just made.

In case some other software is using port *1234*, change the value of `server.port` in the **server.properties** file to some available port.


## Running Barefoot

This section will explain how to run Barefoot. Running Barefoot is extensively explained in the [original README file](barefoot_README.md), so refer to that one for any issues you may encounter that are not explained in this section.

Barefoot involves running two servers:
- The **map server** will adapt and run the street database used to map-match routes and requires *Docker* to run.
- The **matcher server** executes the map-matching algorithm, using the database offered by the map server.

### Running the map server

With **Docker** running, open a terminal, change directory to the barefoot repository and run the following to build the image:
```
docker build -t barefoot-map ./map
```
You may need to add `sudo` at the beginning if you receive an authorization error.

Now that the image for the map server has been created, run the map server:
```
docker run -it -p 5431:5432 --name="barefoot-bus" -v <path_to_barefoot_repository>/map/:/mnt/map barefoot-map
```
If you receive an error because port *5431* is already in use, replace `5431` with any port not in use and update *busmatching.properties* accordingly.
Replace `<path_to_barefoot_repository>` with the absolute path to the repository you downloaded.

After a brief pause, the container will be running and the terminal will allow you to explore it.\
Confirm that the mount (the `-v <path_to_barefoot_repository>/map/:/mnt/map` part of the command) was successful by changing to the `mnt/map` directory and listing its contents:
```
cd mnt/map
ls
```
A few files should be listed. If no files are listed, the mount failed. In such case, exit the container and remove it:
```
exit
docker rm barefoot-bus
```
Solve the issue and run the container again. Mounts may be failing because of one of the following reasons:
- Computer is connected to a VPN
- Drives are not shared on Docker (Settings > Shared Drives)
- User password has been changed since drives were shared ("Reset credentials" and share them again, then restart Docker)
- Docker may need to be started with admin privileges
- The path used in the command is incorrect

Once you have confirmed that the mount was successful, run the following (assuming you're inside the *mnt/map* directory, otherwise change the path to *import.sh* accordingly):
```
bash osm/import.sh
```
If it doesn't work, just open *import.sh* with any text editor, copy its entire content and paste it into the terminal to execute it.

It may take a while to complete, depending on the size of the OpenStreetMap extract you provided (roughly 30 minutes for 150MB).

Once all its commands have completed, the map server will have finished building its PostGIS database and it's time to run the matcher server.


### Running the matcher server

Open another terminal and change directory to the Barefoot repository you downloaded.
Execute the following to build the algorithm:
```
mvn package -DskipTests
```

It should be done quickly. Once it has finished, run the following:
```
java -jar target/barefoot-0.1.5-matcher-jar-with-dependencies.jar --debug config/server.properties config/busmatching.properties
```
The matcher server will soon be running, writing a message saying it is ready and listening on port 1234.


## Executing Barefoot on GTFS data

Now that both the map server and the matcher server are running, Barefoot is ready to map-match routes.\
The GTFS *.txt* files are not in the format Barefoot expects: the scripts in the **gtfs_scripts** folder are designed to adapt them, execute map-matching and present the results.

These scripts require **Python 2.7**, which should be installed already, as it is the same version needed by the map server. Open a terminal and change directory to the Barefoot repository you downloaded.

Run `python bf_read_gtfs.py`. This will read the GTFS files you provided in the path indicated by the **gtfs.path** property of the *busmatching.properties* file. It may take a while (roughly 20 minutes for 60MB).

Run `python bf_convert_shapes.py`. This will create a folder named **mapmatching_input**, containing all bus routes adapted and ready to be used by Barefoot.

Run `python bf_mapmatching.py`. This will execute the map-matching procedure on all bus route shapes found inside the **mapmatching_input** folder, and store the results into a new folder, named **mapmatching_results**. It may take a while (roughly 6 seconds per shape).

Run `python bf_road_sequence.py`. This will read the files within the **mapmatching_results** folder to build PostGIS geometries and store them inside the map server's database.

Run `python bf_check_mm.py`. This will create some tables inside the map server's database containing quality indicators for the map-matched routes.

Once all scripts have been executed, several new tables will have been created inside the map server's PostGIS database. You can connect to the database using the same credentials as the ones listed in the *busmatching.properties* file.\
If you didn't change them, they should be:
```
database.host=localhost
database.port=5431
database.name=barefoot
database.user=osmuser
database.password=pass
```

The tables created by the scripts are as follows:
- `gtfs.shapes`: GTFS data from *shapes.txt*
- `gtfs.stop_times`: GTFS data from *stop_times.txt*
- `gtfs.stops`: GTFS data from *stops.txt*
- `gtfs.trips`: GTFS data from *trips.txt*
- `gtfs.shape_stops`: PostGIS geometries of all the stops that each route makes
- `busmatching.mm_bus_routes`: PostGIS geometries of the results of map-matching
- `busmatching.distances_gtfs_mm`: PostGIS geometries of the points defined in *shapes.txt*, along with a column indicating distance of the GTFS point from the map-matched shape
- `busmatching.quality_indicators_mm`: Various indicators for each shape to help understanding the quality of the result of map-matching


## Observations
When a bus route has frequent stops, the results tend to be really good, as stops are generally located in straight segments that do not lead the map-matching procedure to commit major errors, even if coordinates are imprecise.

However, buses that travel a long distance without taking any stops (such as routes meant to connect a small town to a larger one) often lead to a path very different from the actual one.
