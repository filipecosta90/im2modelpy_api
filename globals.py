import os
import sqlite3

#### globals ####

def create_or_open_db(db_file, db_schema):
    db_exists = os.path.exists(db_file)
    connection = sqlite3.connect(db_file)
    if db_exists is False:
        connection.execute(db_schema)
    return connection

global redisHost
redisHost = "localhost"

global redisPort
redisPort = 6379

global cellsDBPath
global cellsDBSchema
cellsDBPath = "data/cellsdb.sqlite3"
cellsDBSchema = '''create table if not exists unitcells(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result BLOB );'''

global datsDBPath
global datsDBSchema
datsDBPath = "data/datsdb.sqlite3"
datsDBSchema = '''create table if not exists dats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result BLOB,
        dats_conf_id INTEGER,
        dats_conf_key TEXT
        );'''

global datsConfDBPath
global datsConfDBSchema
datsConfDBPath = "data/datsconfdb.sqlite3"
datsConfDBSchema = '''create table if not exists datsconf(
        id INTEGER PRIMARY KEY AUTOINCREMENT
        );'''

global tdmapsDBPath
global tdmapsDBSchema
tdmapsDBPath = "data/tdmapsdb.sqlite3"
tdmapsDBSchema = '''create table if not exists tdmaps(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exp_setup_conf_id integer,
        cells_conf_id integer, 
        slices_conf_id integer, 
        waves_conf_id integer, 
        dats_conf_id integer,
        simgrids_conf_id integer
        );'''

global simgridsDBPath
global simgridsDBSchema
simgridsDBPath = "data/simgridsdb.sqlite3"
simgridsDBSchema = '''create table if not exists simgrids(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result BLOB
        );'''

global apiVersion 
apiVersion = "0.0.1"

UPLOAD_FOLDER = './uploads'
#### globals ####