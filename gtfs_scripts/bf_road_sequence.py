# This script reads the map-matched routes files from the input folder, and writes the sequence of roads each route goes through in the <schema>.<table> table.

import sys
import psycopg2
import os
from configobj import ConfigObj
import json

conn = None
cur = None

try:
	config = ConfigObj('../config/busmatching.properties')
	db_name = config.get('database.name')
	db_user = config.get('database.user')
	db_password = config.get('database.password')
	db_host = config.get('database.host')
	db_port = config.get('database.port')
	mapmatching_schema = config.get('mapmatching.schema')
	mapmatched_directory = config.get('mapmatching.output.directory')
	mapmatched_prefix = config.get('mapmatching.output.prefix')
	road_sequence_table = config.get('mapmatching.table.road-sequence')
	
	conn = psycopg2.connect(database=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
	
	cur = conn.cursor()
	cur.execute("""CREATE SCHEMA IF NOT EXISTS {0};""".format(mapmatching_schema))
	cur.execute("""DROP TABLE IF EXISTS {0}.{1};""".format(mapmatching_schema, road_sequence_table))
	cur.execute("""
		CREATE TABLE {0}.{1} (
			shape_id varchar,
			segment_id	varchar,
			segment_sequence integer,
			heading varchar,
			segment_geom geometry,
			PRIMARY KEY (shape_id,segment_sequence)
		) WITH ( OIDS=FALSE );""".format(mapmatching_schema, road_sequence_table))
	conn.commit()
	file_list = os.listdir(mapmatched_directory) # Lists all files within the directory
	progress = 1 # Not necessary to the algorithm, it's just a counter to display the script's progress
	for file_name in file_list: # Each file, which represents a bus route, is processed
		shape_id = file_name[len(mapmatched_prefix) : file_name.index('.')] # Extracts the shape ID
		
		print('Extracting road sequence from ' + file_name +  ' (' + str(progress) + '/' + str(len(file_list)) + ')...')
		mm_result = None
		for line in open(mapmatched_directory + '/' + file_name, 'r'):
			if line.startswith('[{"seqprob"'): # Line that contains the information necessary to build a sequence of way IDs
				mm_result = json.loads(line)
		
		if not mm_result: # File is invalid: no map-matching result found
			print("No map-matching information found in {0}, skipping.".format(file_name))
			progress += 1
			continue
		
		road_heading_sequence = []
		previous_road = None # Used to avoid duplicates
		previous_heading = None # Used to avoid situations where a (wrong) road is entered and exited immediately
		rh = None
		for element in mm_result: # This for loop builds the road sequence
			found_roads = False # "roads" is a field that contains a sequence of way IDs traversed to move from one point to another
			transition = element.get('transition')
			if transition != None: # Only the first element should lack a "transition" field
				route = transition.get('route')
				if route != None:
					roads = route.get('roads')
					if roads != None: # Contains a sequence of way IDs
						for r in roads:
							found_roads = True
							route_road = r['road']
							heading = r['heading']
							if (route_road != previous_road) or ((previous_heading == 'forward' and heading == 'backward') or (previous_heading == 'backward' and heading == 'forward')): # Checks that the road is different, or the same in opposite direction
								rh = [route_road, heading]
								road_heading_sequence.append(rh)
								previous_road = route_road
								previous_heading = heading
			if not found_roads: # The first element lacks a "transition" field, so instead it takes "point.road" for the first road
				road = element['point']['road']
				heading = element['point']['heading']
				if (road != None and road != previous_road) or ((road == previous_road) and ((previous_heading == 'forward' and heading == 'backward') or (previous_heading == 'backward' and heading == 'forward'))): # Probably an unnecessary check, but it's safer this way
					rh = [road, heading]
					road_heading_sequence.append(rh)
					previous_road = road
					previous_heading = heading
		segment_sequence = 1
		for segment in road_heading_sequence: # Inserts the sequence of way IDs into the database
			cur.execute("""
				INSERT INTO {0}.{1} (shape_id, segment_id, segment_sequence, heading)
					VALUES ('{2}', '{3}', {4}, '{5}');
			""".format(mapmatching_schema, road_sequence_table, shape_id, segment[0], segment_sequence, segment[1]))
			segment_sequence += 1
		conn.commit()
		progress += 1 # 1 more route has been processed; this counter is only used to display the script's progress
	
	cur.execute("""
		UPDATE {0}.{1} r
		SET segment_geom = b.geom
		FROM bfmap_ways b
		WHERE TRIM(LEADING '0' FROM r.segment_id) = CAST(b.gid AS varchar);
	""".format(mapmatching_schema, road_sequence_table))
	conn.commit()
	print("All bus routes have been handled.")

finally:
	if cur is not None:
		cur.close()
		del cur
		
	if conn is not None:
		conn.close()
		del conn