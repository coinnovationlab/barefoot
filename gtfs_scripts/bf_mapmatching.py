# This script executes BMW Car IT's Barefoot Map-matching algorithm on all bus routes.

# Parameters are as follows:
# host: Host the matcher server is running on.
# port: Port to access the matcher server.
# format: Desired output format. Use "debug" to make it compatible with the script that converts it into a sequence of road IDs.
# input_file_name: Input file to map-match
# output_file_name: Name to give to the map-matched files.

# Note that batch.py has been edited so that the output of the map-matching algorithm will be saved as a JSON file, inside a new directory, with a name that follows this structure: <prefix><shp_id_value>.json

import os
from configobj import ConfigObj

config = ConfigObj('../config/busmatching.properties')
input_directory = config.get('mapmatching.input.directory')
output_directory = config.get('mapmatching.output.directory')
input_prefix = config.get('mapmatching.input.prefix')
output_prefix = config.get('mapmatching.output.prefix')

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

i = 1
file_list = os.listdir(input_directory)
n_files = len(file_list)
for file in file_list:
	shape_id = file[len(input_prefix) : file.index('.')]
	print("Map-matching file {0} ({1}/{2})...".format(file, i, n_files))
	command = "python ../util/submit/batch.py --host localhost --port 1234 --format=debug --input_file_name {0}/{1}{2}.json --output_file_name {3}/{4}{2}.json".format(input_directory, input_prefix, shape_id, output_directory, output_prefix)
	os.system(command)
	i += 1