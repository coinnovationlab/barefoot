# This script builds PostGIS geometries of the results of BMW Car IT's Barefoot Map-matching algorithm on GTFS bus routes.

import psycopg2
import os
from configobj import ConfigObj

conn = None
cur = None

try:
	config = ConfigObj('../config/busmatching.properties')
	db_name = config.get('database.name')
	db_user = config.get('database.user')
	db_password = config.get('database.password')
	db_host = config.get('database.host')
	db_port = config.get('database.port')
	
	bf_ways_table = config.get('database.table')
	
	gtfs_schema = config.get('gtfs.schema')
	mapmatching_schema = config.get('mapmatching.schema')
	road_sequence_table = config.get('mapmatching.table.road-sequence')
	shape_stops_table = config.get('gtfs.derived-table.shape-stops')
	mm_errors_table = config.get('mapmatching.table.shape-errors')
	
	distances_table = config.get('mapmatching.table.distances')
	indicators_table = config.get('mapmatching.table.indicators')
	close_threshold = config.get('mapmatching.indicators.close_threshold')
	mid_threshold = config.get('mapmatching.indicators.mid_threshold')
	select_limit = config.get('mapmatching.indicators.limit')
	
	epsg = config.get('mapmatching.coordinates.epsg')
	mapmatched_directory = config.get('mapmatching.output.directory')
	mapmatched_prefix = config.get('mapmatching.output.prefix')
	
	conn = psycopg2.connect(database=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
	cur = conn.cursor()
	
	# Creates a table that contains the distance between each point from the shapes.txt GTFS file and the map-matched route based on the GTFS stops.
	cur.execute("""DROP TABLE IF EXISTS {0}.{1};""".format(mapmatching_schema, distances_table))
	cur.execute("""
		CREATE TABLE {0}.{2} AS
			WITH mm_shapes AS (
				SELECT
					shape_id,
					ST_Union(segment_geom) AS shape
				FROM {0}.{3}
				GROUP BY shape_id
			)
			SELECT
				gs.shape_id,
				gs.shape_pt_sequence,
				ST_SetSRID(ST_MakePoint(gs.shape_pt_lon,gs.shape_pt_lat),4326) AS geom,
				ST_Distance(ST_Transform(ST_SetSRID(ST_MakePoint(gs.shape_pt_lon,gs.shape_pt_lat),4326), {4}), ST_Transform(ms.shape, {4})) AS distance_meters
			FROM {1}.shapes gs INNER JOIN mm_shapes ms
				ON gs.shape_id = ms.shape_id::bigint;
	""".format(mapmatching_schema, gtfs_schema, distances_table, road_sequence_table, epsg))
	
	conn.commit()
	print("Generated table {0}.{1}, containing distances between each point from the shapes.txt GTFS file and the map-matched route based on the GTFS stops.".format(mapmatching_schema, distances_table))
	
	try:
		cur.execute("""
			ALTER TABLE {0}.{1}
			ADD COLUMN distance_meters double precision;
		""".format(gtfs_schema, shape_stops_table))
	except psycopg2.errors.DuplicateColumn:
		pass
	conn.commit()

	cur.execute("""
		WITH mm_shapes AS (
			SELECT
				shape_id,
				ST_Union(segment_geom) AS shape
			FROM {0}.{1}
			GROUP BY shape_id
		)
		UPDATE {2}.{3} AS gs
		SET distance_meters = ST_Distance(ST_Transform(gs.geom, {4}), ST_Transform(ms.shape, {4}))
		FROM mm_shapes AS ms
		WHERE gs.shape_id = ms.shape_id::bigint;
	""".format(mapmatching_schema, road_sequence_table, gtfs_schema, shape_stops_table, epsg))
	conn.commit()
	print("Added column to table {0}.{1} to contain distance between each stop from the stops.txt GTFS file and map-matched routes that make a corresponding stop.".format(gtfs_schema, shape_stops_table))
	
	cur.execute("""DROP TABLE IF EXISTS {0}.{1};""".format(mapmatching_schema, indicators_table))
	cur.execute("""
		CREATE TABLE {0}.{1} AS
			WITH route_point_counts AS (
				SELECT
					shape_id,
					COUNT(shape_id) AS total,
					COUNT(CASE WHEN distance_meters < {5} THEN shape_id END) AS close,
					COUNT(CASE WHEN distance_meters >= {5} AND distance_meters < {6} THEN shape_id END) AS mid,
					COUNT(CASE WHEN distance_meters >= {6} THEN shape_id END) AS far,
					AVG(distance_meters) AS avg_distance,
					MAX(distance_meters) AS max_distance
				FROM {0}.{2}
				GROUP BY shape_id
			), stops_point_counts AS (
				SELECT
					shape_id,
					COUNT(shape_id) AS total,
					COUNT(CASE WHEN distance_meters < {5} THEN shape_id END) AS close,
					COUNT(CASE WHEN distance_meters >= {5} AND distance_meters < {6} THEN shape_id END) AS mid,
					COUNT(CASE WHEN distance_meters >= {6} THEN shape_id END) AS far,
					AVG(distance_meters) AS avg_distance,
					MAX(distance_meters) AS max_distance
				FROM {3}.{4}
				GROUP BY shape_id
			)
			SELECT
				r.shape_id,
				r.total AS route_total,
				r.close AS route_close,
				r.mid AS route_mid,
				r.far AS route_far,
				r.mid::decimal/r.total AS route_mid_rate,
				r.far::decimal/r.total AS route_far_rate,
				r.avg_distance AS route_avg_distance,
				r.max_distance AS route_max_distance,
				s.total AS stops_total,
				s.close AS stops_close,
				s.mid AS stops_mid,
				s.far AS stops_far,
				s.mid::decimal/s.total AS stops_mid_rate,
				s.far::decimal/s.total AS stops_far_rate,
				s.avg_distance AS stops_avg_distance,
				s.max_distance AS stops_max_distance
			FROM route_point_counts r LEFT JOIN stops_point_counts s
				ON r.shape_id = s.shape_id
	""".format(mapmatching_schema, indicators_table, distances_table, gtfs_schema, shape_stops_table, close_threshold, mid_threshold))
	
	conn.commit()
	print("Generated table {0}.{1}, containing indicators for how close the map-matching result is to the GTFS shapes and stops.".format(mapmatching_schema, indicators_table))
	print("\nIndicators are as follows:")
	print("route_close: number of GTFS points (from shapes.txt) that are close (less than {0} meters) to the map-matching result. The higher the better.".format(close_threshold))
	print("route_mid: number of GTFS points (from shapes.txt) that are at medium distance (between {0} and {1} meters) from the map-matching result. The lower the better.".format(close_threshold, mid_threshold))
	print("route_far: number of GTFS points (from shapes.txt) that are far (more than {0} meters) from the map-matching result. The lower the better.".format(mid_threshold))
	print("route_mid_rate: result of mid/total. The lower the better.".format(close_threshold))
	print("route_far_rate: result of far/total. The lower the better.".format(close_threshold))
	print("route_avg_distance: average distance between the map-matching result and GTFS points (from shapes.txt). The lower the better.".format(close_threshold))
	print("route_max_distance: distance from the map-matching result of the GTFS point (from shapes.txt) that is furthest away. The lower the better.".format(close_threshold))
	print("stops_close: equivalent to route_close, but for GTFS stops.txt.")
	print("stops_mid: equivalent to route_mid, but for GTFS stops.txt.")
	print("stops_far: equivalent to route_far, but for GTFS stops.txt.")
	print("stops_mid_rate: equivalent to route_mid_rate, but for GTFS stops.txt.")
	print("stops_far_rate: equivalent to route_far_rate, but for GTFS stops.txt.")
	print("stops_avg_distance: equivalent to route_avg_distance, but for GTFS stops.txt.")
	print("stops_max_distance: equivalent to route_max_distance, but for GTFS stops.txt.")
	
	cur.execute("""
		SELECT COUNT(shape_id)
		FROM {0}.{1}
	""".format(mapmatching_schema, indicators_table))
	print("\nTotal number of shapes: {0}.".format(cur.fetchall()[0][0]))
	
	print("\nDistance comparisons from GTFS routes")
	cur.execute("""
		SELECT
			shape_id,
			route_total,
			route_close,
			route_mid,
			route_far,
			route_mid_rate,
			route_far_rate,
			route_avg_distance,
			route_max_distance
		FROM {0}.{1}
		ORDER BY route_far_rate DESC
		LIMIT {2};
	""".format(mapmatching_schema, indicators_table, select_limit))
	print("\nHere are the {0} shapes with highest route_far_rate:".format(cur.rowcount))
	print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format('shape_id'.ljust(14), 'total'.ljust(6), 'close'.ljust(6), 'mid'.ljust(6), 'far'.ljust(6), 'mid_rate'.ljust(9), 'far_rate'.ljust(9), 'avg_distance'.ljust(13), 'max_distance'))
	for r in cur.fetchall():
		print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format(str(r[0]).ljust(14), str(r[1]).ljust(6), str(r[2]).ljust(6), str(r[3]).ljust(6), str(r[4]).ljust(6), str(round(r[5], 4)).ljust(9), str(round(r[6], 4)).ljust(9), str(round(r[7], 2)).ljust(13), round(r[8], 2)))
		
	cur.execute("""
		SELECT
			shape_id,
			route_total,
			route_close,
			route_mid,
			route_far,
			route_mid_rate,
			route_far_rate,
			route_avg_distance,
			route_max_distance
		FROM {0}.{1}
		ORDER BY route_max_distance DESC
		LIMIT {2};
	""".format(mapmatching_schema, indicators_table, select_limit))
	print("\nHere are the {0} shapes with highest route_max_distance:".format(cur.rowcount))
	print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format('shape_id'.ljust(14), 'total'.ljust(6), 'close'.ljust(6), 'mid'.ljust(6), 'far'.ljust(6), 'mid_rate'.ljust(9), 'far_rate'.ljust(9), 'avg_distance'.ljust(13), 'max_distance'))
	for r in cur.fetchall():
		print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format(str(r[0]).ljust(14), str(r[1]).ljust(6), str(r[2]).ljust(6), str(r[3]).ljust(6), str(r[4]).ljust(6), str(round(r[5], 4)).ljust(9), str(round(r[6], 4)).ljust(9), str(round(r[7], 2)).ljust(13), round(r[8], 2)))
		
	print("\nDistance comparisons from GTFS stops")
	cur.execute("""
		SELECT
			shape_id,
			stops_total,
			stops_close,
			stops_mid,
			stops_far,
			stops_mid_rate,
			stops_far_rate,
			stops_avg_distance,
			stops_max_distance
		FROM {0}.{1}
		ORDER BY stops_far_rate DESC
		LIMIT {2};
	""".format(mapmatching_schema, indicators_table, select_limit))
	print("\nHere are the {0} shapes with highest stops_far_rate:".format(cur.rowcount))
	print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format('shape_id'.ljust(14), 'total'.ljust(6), 'close'.ljust(6), 'mid'.ljust(6), 'far'.ljust(6), 'mid_rate'.ljust(9), 'far_rate'.ljust(9), 'avg_distance'.ljust(13), 'max_distance'))
	for r in cur.fetchall():
		print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format(str(r[0]).ljust(14), str(r[1]).ljust(6), str(r[2]).ljust(6), str(r[3]).ljust(6), str(r[4]).ljust(6), str(round(r[5], 4)).ljust(9), str(round(r[6], 4)).ljust(9), str(round(r[7], 2)).ljust(13), round(r[8], 2)))
		
	cur.execute("""
		SELECT
			shape_id,
			stops_total,
			stops_close,
			stops_mid,
			stops_far,
			stops_mid_rate,
			stops_far_rate,
			stops_avg_distance,
			stops_max_distance
		FROM {0}.{1}
		ORDER BY stops_max_distance DESC
		LIMIT {2};
	""".format(mapmatching_schema, indicators_table, select_limit))
	print("\nHere are the {0} shapes with highest stops_max_distance:".format(cur.rowcount))
	print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format('shape_id'.ljust(14), 'total'.ljust(6), 'close'.ljust(6), 'mid'.ljust(6), 'far'.ljust(6), 'mid_rate'.ljust(9), 'far_rate'.ljust(9), 'avg_distance'.ljust(13), 'max_distance'))
	for r in cur.fetchall():
		print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}|{8}".format(str(r[0]).ljust(14), str(r[1]).ljust(6), str(r[2]).ljust(6), str(r[3]).ljust(6), str(r[4]).ljust(6), str(round(r[5], 4)).ljust(9), str(round(r[6], 4)).ljust(9), str(round(r[7], 2)).ljust(13), round(r[8], 2)))
		
	cur.execute("""DROP TABLE IF EXISTS {0}.{1}""".format(mapmatching_schema, mm_errors_table))
	cur.execute("""CREATE TABLE {0}.{1} (shape_id bigint);""".format(mapmatching_schema, mm_errors_table))
	file_list = os.listdir(mapmatched_directory)
	mm_error_count = 0
	mm_error_list = ''
	for file_name in file_list:
		with open(mapmatched_directory + '/' + file_name, 'r') as mm_file:
			if mm_file.readline().startswith('ERROR'): # There was an error during the map-matching of this shape
				mm_error_count += 1
				shape_id = file_name[len(mapmatched_prefix) : file_name.index('.')]
				mm_error_list += ' ' + shape_id
				cur.execute("""
					INSERT INTO {0}.{1} (shape_id) VALUES ({2})
				""".format(mapmatching_schema, mm_errors_table, shape_id))
	conn.commit()
	if mm_error_count > 0:
		print("\nThe following {0} shapes, also listed in the {1}.{2} table, caused an error and could not be map-matched:{3}".format(mm_error_count, mapmatching_schema, mm_errors_table, mm_error_list))
		
finally:
	if cur is not None:
		cur.close()
		del cur
		
	if conn is not None:
		conn.close()
		del conn