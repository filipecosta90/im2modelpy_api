from flask import Flask, render_template, request, redirect, Blueprint
from flask_jsonpify import jsonpify

from werkzeug import secure_filename
import urllib.request
import urllib.error
import urllib.parse
import os
import json
import sys
import ase.io.cif
from ase import Atoms
import zlib
import sqlite3
import ntpath
import numpy as np
from matplotlib import pyplot as plt
import sys 
import jsonschema
import redis
from rejson import Client, Path

#so that we can import globals
sys.path.append('../..')

from globals import *

def get_default_json( ):
	return {
  "dimensions" : { "n_rows" : None, "n_cols": None },
  "exp_id" : None,
  "correlation_method" : None,
  "normalization_mode" : None,
  "runned_simulation" : False,
  "best_match" : None,
  "dat_ids_1d" : None,
  "simulated_matches_1d" : None,
  "simulated_matches_location_1d" : None
}

def adjust_simgrids_array_fields( saveJson ):
	if saveJson["dimensions"]["n_rows"] is not None and saveJson["dimensions"]["n_cols"]:
		dimension_1d = saveJson["dimensions"]["n_rows"] * saveJson["dimensions"]["n_cols"]
		if saveJson["dat_ids_1d"] is None:
			saveJson["dat_ids_1d"] = []
		len_dat_ids_1d = len( saveJson["dat_ids_1d"] )

		for i in range(len_dat_ids_1d,dimension_1d):
			saveJson["dat_ids_1d"].append( None )
			
		if saveJson["simulated_matches_1d"] is None:
			saveJson["simulated_matches_1d"] = []
		len_simulated_matches_1d = len( saveJson["simulated_matches_1d"] )

		for i in range(len_simulated_matches_1d,dimension_1d):
			saveJson["simulated_matches_1d"].append( None )

		if saveJson["simulated_matches_location_1d"] is None:
			saveJson["simulated_matches_location_1d"] = []
		len_simulated_matches_location_1d = len( saveJson["simulated_matches_location_1d"] )

		for i in range(len_simulated_matches_location_1d,dimension_1d):
			saveJson["simulated_matches_location_1d"].append( None )

		if len_dat_ids_1d > dimension_1d:
			del saveJson["dat_ids_1d"][dimension_1d:]
		if len_simulated_matches_1d > dimension_1d:
			del saveJson["simulated_matches_1d"][dimension_1d:]
		if len_simulated_matches_location_1d > dimension_1d:
			del saveJson["simulated_matches_location_1d"][dimension_1d:]

	return saveJson


def get_schema_simgrids( ):
	schema = None
	with open('blueprints/simgrids/schemas/schema_simgrids.json', 'r') as f:
		schema_data = f.read()
		schema = json.loads(schema_data)
	return schema

def get_schema_simgrids_dat( ):
	schema = None
	with open('blueprints/simgrids/schemas/schema_simgrids_dat.json', 'r') as f:
		schema_data = f.read()
		schema = json.loads(schema_data)
	return schema

def update_simgrids_dat( id, setupJson, simgridsDBPath, simgridsDBSchema ):
	result = None
	error_message = None
	data = get_simgrids_data( id, simgridsDBPath, simgridsDBSchema )
	if data is not None:
		try:
			jsonschema.validate( setupJson, get_schema_simgrids_dat() )
			n_row = setupJson["position"]["n_row"]
			n_rows = data["dimensions"]["n_rows"]
			n_col = setupJson["position"]["n_col"]
			n_cols = data["dimensions"]["n_cols"]
			dat_ids_1d_pos = n_row * n_cols + n_col
			if n_row < n_rows and n_col < n_cols and dat_ids_1d_pos < len( data["dat_ids_1d"] ):
				data["dat_ids_1d"][dat_ids_1d_pos] = setupJson["dat_id"]
				compressed_result = zlib.compress( json.dumps(data).encode('utf-8') )
				sqlite3_conn = create_or_open_db( simgridsDBPath, simgridsDBSchema )
				sql = '''update simgrids set result = ? where id = ?;'''
				sqlite3_conn.execute( sql,[ compressed_result, id ] )
				sqlite3_conn.commit()
				result = get_simgrids_data( id, simgridsDBPath, simgridsDBSchema )
				sqlite3_conn.close()
			else:
				error_message = "position {0} exceeds simgrid limits {1}.".format( setupJson["position"], data["dimensions"] )
		except jsonschema.exceptions.ValidationError as ve:
			error_message = str(ve)
			pass

	return result, error_message

def update_simgrids( id, setupJson, simgridsDBPath, simgridsDBSchema ):
	result = None
	error_message = None
	data = get_simgrids_data( id, simgridsDBPath, simgridsDBSchema )
	if data is not None:
		saveJson = {**data, **setupJson}
		saveJson = adjust_simgrids_array_fields( saveJson )
		try:
			jsonschema.validate( saveJson, get_schema_simgrids() )
			compressed_result = zlib.compress( json.dumps(saveJson).encode('utf-8') )
			sqlite3_conn = create_or_open_db( simgridsDBPath, simgridsDBSchema )
			sql = '''update simgrids set result = ? where id = ?;'''
			sqlite3_conn.execute( sql,[ compressed_result, id ] )
			sqlite3_conn.commit()
			result = get_simgrids_data( id, simgridsDBPath, simgridsDBSchema )
			sqlite3_conn.close()
		except jsonschema.exceptions.ValidationError as ve:
			error_message = str(ve)
			pass

		
	return result, error_message

#backgroud save_cells_unitcells_data job
def save_simgrids_setup_data_rejson( id, setupJson, rejson_host, rejson_key, rejson_db ):
	saveJson = {** get_default_json(), **setupJson}
	rj = Client(host=rejson_host, port=rejson_key, db=rejson_db)
	redis_key = rj.incr('simgrids_key')
	saveJson["id"] = redis_key
	json_key = "simgrids_key_{0}".format(redis_key)
	status = rj.jsonset( json_key, Path.rootPath(), saveJson)
	return redis_key, saveJson


def get_simgrids_data_rejson( rejson_host, rejson_key, rejson_db, redis_key, json_path = '.' ):
	result = None
	rj = Client(host=rejson_host, port=rejson_key, db=rejson_db)
	json_key = "simgrids_key_{0}".format(redis_key)
	result = rj.jsonget( json_key )
	return result

#####################################################
##################### BLUEPRINT #####################
#####################################################

simgrids = Blueprint(
    'simgrids', #name of module
    __name__,
    template_folder='templates' # templates folder
)

@simgrids.route('/', methods = ['GET'])
def api_simgrids_getindex():
    return render_template('index_simgrids.html')

@simgrids.route('/', methods = ['POST'])
def api_simgrids_add():
	global apiVersion
	status = False
	data_dict = None 
	if len(request.data) > 0:
		data_dict = json.loads( request.data )
	data = None
	inserted_simgrid_id, data = save_simgrids_setup_data_rejson( None, data_dict, redisHost, redisPort, 0 )
	if inserted_simgrid_id is not None and data is not None:
		simgrid_link = "{0}api/simgrids/{1}".format( request.host_url, inserted_simgrid_id )
		status = True

	if status is False:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": "Something went wrong.",
		            "url": request.url,
		            }, 
		        }
		return_code = 404
	else:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "data" : data, 
		        "links" : { "simgrid" : { "self" : simgrid_link } }, 
		        }
		return_code = 200

	return jsonpify(result), return_code

@simgrids.route('/<string:simgridid>', methods = ['GET'])
def api_simgrids_get(simgridid):
	global apiVersion
	status = None
	result = None
	print(simgridid)
	data = get_simgrids_data_rejson(redisHost, redisPort, 0, simgridid)
	if data is None:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": "Something went wrong.",
		            "url": request.url,
		            },
		        }
		return_code = 404
	else:
		simgrid_link = "{0}api/simgrids/{1}".format( request.host_url, simgridid )
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "data" : data,
		        "links" : { "simgrid" : { "self" : simgrid_link } },  
		        }
		return_code = 200

	return jsonpify(result), return_code


@simgrids.route('/<string:simgridid>', methods = ['POST'])
def api_simgrids_post(simgridid):
	global apiVersion
	global simgridsDBPath
	global simgridsDBSchema
	status = None
	result = None
	data_dict = None 
	data = None
	error_message = None

	if len(request.data) > 0:
		data_dict = json.loads( request.data )
		data, error_message = update_simgrids(simgridid, data_dict, simgridsDBPath, simgridsDBSchema)
	
	if data is None:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": "Something went wrong.\n\n" + error_message,
		            "url": request.url,
		            },
		        }
		return_code = 404
	else:
		simgrid_link = "{0}api/simgrids/{1}".format( request.host_url, simgridid )
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "data" : data,
		        "links" : { "simgrid" : { "self" : simgrid_link } },  
		        }
		return_code = 200

	return jsonpify(result), return_code


@simgrids.route('/<string:simgridid>/dat', methods = ['POST'])
def api_simgrids_dat_post(simgridid):
	global apiVersion
	global simgridsDBPath
	global simgridsDBSchema
	status = None
	result = None
	data_dict = None 
	data = None
	error_message = None

	if len(request.data) > 0:
		data_dict = json.loads( request.data )
		data, error_message = update_simgrids_dat(simgridid, data_dict, simgridsDBPath, simgridsDBSchema)
	
	if data is None:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": "Something went wrong.\n\n" + error_message,
		            "url": request.url,
		            },
		        }
		return_code = 404
	else:
		simgrid_link = "{0}api/simgrids/{1}".format( request.host_url, simgridid )
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "data" : data,
		        "links" : { "simgrid" : { "self" : simgrid_link } },  
		        }
		return_code = 200

	return jsonpify(result), return_code
