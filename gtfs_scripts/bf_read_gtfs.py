# This script reads GTFS files and stores their data into a Postgres DB.

import sys
import psycopg2
from configobj import ConfigObj
import pandas as pd
from sqlalchemy import create_engine

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
	gtfs_path = config.get('gtfs.path')
	
	conn = psycopg2.connect(database=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
	cur = conn.cursor()
	
	cur.execute("""CREATE SCHEMA IF NOT EXISTS {0};""".format(gtfs_schema))
	cur.execute("""DROP TABLE IF EXISTS {0}.shapes;""".format(gtfs_schema))
	cur.execute("""DROP TABLE IF EXISTS {0}.stop_times;""".format(gtfs_schema))
	cur.execute("""DROP TABLE IF EXISTS {0}.stops;""".format(gtfs_schema))
	cur.execute("""DROP TABLE IF EXISTS {0}.trips;""".format(gtfs_schema))
	conn.commit()
	
	engine = create_engine("postgresql://{0}:{1}@{2}:{3}/{4}".format(db_user, db_password, db_host, db_port, db_name))
	
	df_shapes = pd.read_csv(gtfs_path + '/shapes.txt')
	df_shapes.to_sql('shapes', engine, schema=gtfs_schema)
	print('GTFS shapes table stored into DB as {0}.shapes.'.format(gtfs_schema))
	
	df_stop_times = pd.read_csv(gtfs_path + '/stop_times.txt')
	df_stop_times.to_sql('stop_times', engine, schema=gtfs_schema)
	print('GTFS stop times table stored into DB as {0}.stop_times.'.format(gtfs_schema))
	
	df_stops = pd.read_csv(gtfs_path + '/stops.txt')
	df_stops.to_sql('stops', engine, schema=gtfs_schema)
	print('GTFS stops table stored into DB as {0}.stops.'.format(gtfs_schema))
	
	df_trips = pd.read_csv(gtfs_path + '/trips.txt')
	df_trips.to_sql('trips', engine, schema=gtfs_schema)
	print('GTFS trips table stored into DB as {0}.trips.'.format(gtfs_schema))
	
except SystemExit:
	pass
	

finally:
	if cur is not None:
		cur.close()
		del cur
		
	if conn is not None:
		conn.close()
		del conn