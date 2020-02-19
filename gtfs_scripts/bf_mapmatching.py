# This script executes BMW Car IT's Barefoot Map-matching algorithm on all bus routes.
# Before executing it, make sure there is a folder named "mapmatched_shapes" in the same folder as this script.

# Parameters are as follows:
# host: Host the Docker container is running on.
# port: Port to access the service running in the container.
# format: Desired output format. Use "debug" to make it compatible with the script that converts it into a sequence of road IDs.
# shp_id: String to affix at the end of the output file's name. Shape ID is recommended.

# Note that batch.py has been edited so that the output of the map-matching algorithm will be saved as a JSON file, inside a new directory, with a name that follows this structure: <prefix>_<shp_id_value>.json

import os
from configobj import ConfigObj

config = ConfigObj('../config/busmatching.properties')
input_directory = config.get('mapmatching.input.directory')
output_directory = config.get('mapmatching.output.directory')
input_prefix = config.get('mapmatching.input.prefix')
output_prefix = config.get('mapmatching.output.prefix')

for file in os.listdir(input_directory):
	shape_id = file[len(input_prefix) : file.index('.')]
	
	os.system('python ../util/submit/batch.py --host localhost --port 1234 --format=debug --shp_id=' + shape_id + ' --file ' + input_directory + '/' + input_prefix + shape_id + '.json --properties ../config/busmatching.properties --output_directory ' + output_directory + ' --output_prefix ' + output_prefix)