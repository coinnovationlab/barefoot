# This script takes the GTFS-format shapes of the bus routes and converts them into a format fit for BMW Car IT's Barefoot map-matching algorithm to be applied.
# Output files will be generated as .json files and saved inside a dedicated folder.

import sys
import os
import psycopg2
from configobj import ConfigObj
import json

conn = None
cur = None

shape_id = ''
shape_number = 0
try:
	config = ConfigObj('../config/busmatching.properties')
	db_name = config.get('database.name')
	db_user = config.get('database.user')
	db_password = config.get('database.password')
	db_host = config.get('database.host')
	db_port = config.get('database.port')
	gtfs_schema = config.get('gtfs.schema')
	shape_stops_table = config.get('gtfs.derived-table.shape-stops')
	shapes_directory = config.get('mapmatching.input.directory')
	shapes_prefix = config.get('mapmatching.input.prefix')
	epsg = config.get('mapmatching.coordinates.epsg')
	minutes_per_km = config.get('mapmatching.interval.minutes-per-km')
	
	conn = psycopg2.connect(database=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
	cur = conn.cursor()
	
	# Creates a table that lists all stops for each shape ID
	cur.execute("""DROP TABLE IF EXISTS {0}.{1};""".format(gtfs_schema, shape_stops_table))
	cur.execute("""
		CREATE TABLE {0}.{1} AS
		WITH trip_shapes AS (
			SELECT
				t.shape_id,
				MIN(t.trip_id) AS trip_id
			FROM {0}.trips t INNER JOIN {0}.stop_times st
				ON t.trip_id = st.trip_id
			GROUP BY shape_id
		)
		SELECT
			ts.shape_id,
			ts.trip_id,
			st.stop_id,
			st.stop_sequence,
			s.stop_lat,
			s.stop_lon,
			ST_SetSRID(ST_MakePoint(stop_lon,stop_lat),4326) AS geom
		FROM trip_shapes ts 
			LEFT JOIN {0}.stop_times st
				ON ts.trip_id = st.trip_id
			LEFT JOIN {0}.stops s
				ON st.stop_id = s.stop_id;
	""".format(gtfs_schema, shape_stops_table))
	cur.execute("""CREATE INDEX ON {0}.{1} (shape_id);""".format(gtfs_schema, shape_stops_table))
	conn.commit()
	
	# Retrieves the list of all shape IDs
	cur.execute("""
		SELECT DISTINCT shape_id
		FROM {0}.{1};
	""".format(gtfs_schema, shape_stops_table))
	shape_ids_tab = cur.fetchall()
	n_of_shapes = len(shape_ids_tab) # Total number of shapes
	print(str(n_of_shapes) + ' shapes found.')
	
	if not os.path.exists(shapes_directory):
		os.makedirs(shapes_directory)
	
	print('Converting each shape into a JSON file...')
	for i in range(n_of_shapes):
		shape_id = shape_ids_tab[i][0] # Shape ID
		print("Converting {0} ({1}/{2})...".format(shape_id, i+1, n_of_shapes))
		# Longitude, latitude, and a timestamp are necessary for BMW Car IT's Barefoot map-matching algorithm to work.
		# Timestamps are "fake", built by adding 2 minutes for each kilometer.
		cur.execute("""
			SELECT 	
				curr.stop_lon,
				curr.stop_lat,
				CASE WHEN curr.stop_sequence = 1 THEN '2018-01-01 10:00:00'::timestamp AT TIME ZONE 'Europe/Rome'
					ELSE '2018-01-01 10:00:00'::timestamp AT TIME ZONE 'Europe/Rome' + (interval '{3} minutes' *
						SUM(CEILING(ST_Distance(
							ST_Transform(ST_SetSRID(ST_MakePoint(curr.stop_lon, curr.stop_lat), 4326), {4}),
							ST_Transform(ST_SetSRID(ST_MakePoint(prev.stop_lon, prev.stop_lat), 4326), {4}))
						/1000)) OVER (PARTITION BY curr.shape_id ORDER BY curr.stop_sequence)
					)
				END AS timestamp
			FROM {0}.{1} curr LEFT JOIN {0}.{1} prev
			ON curr.shape_id = prev.shape_id AND curr.stop_sequence = (prev.stop_sequence + 1)
			WHERE curr.shape_id = '{2}'
			ORDER BY curr.stop_sequence;
		""".format(gtfs_schema, shape_stops_table, shape_id, minutes_per_km, epsg))
		shape_tab = cur.fetchall()
		
		shape_file = open("{0}/{1}{2}.json".format(shapes_directory, shapes_prefix, shape_id), 'w+') # Output file will be written in the shapes directory
		for j in range(len(shape_tab)): # Writes the file in the format required by the map-matching algorithm
			prefix = '{"point":"POINT('
			mid = ')","time":"'
			last_char = ','
			if j == 0:
				prefix = '[' + prefix
			if j == len(shape_tab) - 1:
				last_char = ']'
			suffix = '","id":"' + str(j) + '"}' + last_char + '\n'
		
			shape_file.write(prefix + str(shape_tab[j][0]) + ' ' + str(shape_tab[j][1]) + mid + str(shape_tab[j][2]) + suffix)
		shape_file.close() # The file for this shape is complete, continues to the next shape
		
	print('Shapes have been converted into JSON files. You can find them in the ' + shapes_directory + ' folder.')

finally:
	if cur is not None:
		cur.close()
		del cur
		
	if conn is not None:
		conn.close()
		del conn