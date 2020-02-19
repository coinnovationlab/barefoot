# This script builds PostGIS geometries of the results of BMW Car IT's Barefoot Map-matching algorithm on GTFS bus routes.

import psycopg2
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
	
	gtfs_schema = config.get('gtfs.schema')
	mapmatching_schema = config.get('mapmatching.schema')
	road_sequence_table = config.get('mapmatching.table.road-sequence')
	
	distances_table = config.get('mapmatching.table.distances')
	indicators_table = config.get('mapmatching.table.indicators')
	close_threshold = config.get('mapmatching.indicators.close_threshold')
	mid_threshold = config.get('mapmatching.indicators.mid_threshold')
	select_limit = config.get('mapmatching.indicators.limit')
	
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
				ST_Distance(ST_Transform(ST_SetSRID(ST_MakePoint(gs.shape_pt_lon,gs.shape_pt_lat),4326), 32632), ST_Transform(ms.shape, 32632)) AS distance_meters
			FROM {1}.shapes gs INNER JOIN mm_shapes ms
				ON gs.shape_id = ms.shape_id::bigint;
	""".format(mapmatching_schema, gtfs_schema, distances_table, road_sequence_table))
	
	conn.commit()
	print("Generated table {0}.{1}, containing distances between each point from the shapes.txt GTFS file and the map-matched route based on the GTFS stops.".format(mapmatching_schema, distances_table))
	
	cur.execute("""DROP TABLE IF EXISTS {0}.{1};""".format(mapmatching_schema, indicators_table))
	cur.execute("""
		CREATE TABLE {0}.{1} AS
			WITH point_counts AS (
				SELECT
					shape_id,
					COUNT(shape_id) AS total,
					COUNT(CASE WHEN distance_meters < {3} THEN shape_id END) AS close,
					COUNT(CASE WHEN distance_meters >= {3} AND distance_meters < {4} THEN shape_id END) AS mid,
					COUNT(CASE WHEN distance_meters >= {4} THEN shape_id END) AS far,
					MAX(distance_meters) AS max_distance
				FROM {0}.{2}
				GROUP BY shape_id
			)
			SELECT
				shape_id,
				total,
				close,
				mid,
				far,
				mid::decimal/total AS mid_rate,
				far::decimal/total AS far_rate,
				max_distance
			FROM point_counts
	""".format(mapmatching_schema, indicators_table, distances_table, close_threshold, mid_threshold))
	
	conn.commit()
	print("Generated table {0}.{1}, containing indicators for how close the map-matching result is to the GTFS shape.".format(mapmatching_schema, indicators_table))
	print("\nIndicators are as follows:")
	print("close: number of GTFS points that are close (less than {0} meters) to the map-matching result. The higher the better.".format(close_threshold))
	print("mid: number of GTFS points that are at medium distance (between {0} and {1} meters) from the map-matching result. The lower the better.".format(close_threshold, mid_threshold))
	print("far: number of GTFS points that are far (more than {0} meters) from the map-matching result. The lower the better.".format(mid_threshold))
	print("mid_rate: result of mid/total. The lower the better.".format(close_threshold))
	print("far_rate: result of far/total. The lower the better.".format(close_threshold))
	print("max_distance: distance from the map-matching result of the GTFS point that is furthest away. The lower the better.".format(close_threshold))
	
	cur.execute("""
		SELECT COUNT(shape_id)
		FROM {0}.{1}
	""".format(mapmatching_schema, indicators_table))
	print("\nTotal number of shapes compared: {0}.".format(cur.fetchall()[0][0]))
	
	cur.execute("""
		SELECT
			shape_id,
			total,
			close,
			mid,
			far,
			mid_rate,
			far_rate,
			max_distance
		FROM {0}.{1}
		ORDER BY far_rate DESC
		LIMIT {2};
	""".format(mapmatching_schema, indicators_table, select_limit))
	print("\nHere are the {0} shapes with highest far_rate:".format(cur.rowcount))
	print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}".format('shape_id'.ljust(14), 'total'.ljust(6), 'close'.ljust(6), 'mid'.ljust(6), 'far'.ljust(6), 'mid_rate'.ljust(9), 'far_rate'.ljust(9), 'max_distance'))
	for r in cur.fetchall():
		print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}".format(str(r[0]).ljust(14), str(r[1]).ljust(6), str(r[2]).ljust(6), str(r[3]).ljust(6), str(r[4]).ljust(6), str(round(r[5], 4)).ljust(9), str(round(r[6], 4)).ljust(9), round(r[7], 4)))
		
	cur.execute("""
		SELECT
			shape_id,
			total,
			close,
			mid,
			far,
			mid_rate,
			far_rate,
			max_distance
		FROM {0}.{1}
		ORDER BY max_distance DESC
		LIMIT {2};
	""".format(mapmatching_schema, indicators_table, select_limit))
	print("\nHere are the {0} shapes with highest max_distance:".format(cur.rowcount))
	print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}".format('shape_id'.ljust(14), 'total'.ljust(6), 'close'.ljust(6), 'mid'.ljust(6), 'far'.ljust(6), 'mid_rate'.ljust(9), 'far_rate'.ljust(9), 'max_distance'))
	for r in cur.fetchall():
		print("{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}".format(str(r[0]).ljust(14), str(r[1]).ljust(6), str(r[2]).ljust(6), str(r[3]).ljust(6), str(r[4]).ljust(6), str(round(r[5], 4)).ljust(9), str(round(r[6], 4)).ljust(9), round(r[7], 4)))

finally:
	if cur is not None:
		cur.close()
		del cur
		
	if conn is not None:
		conn.close()
		del conn