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

#so that we can import globals
sys.path.append('../..')

from globals import *

#backgroud save_cells_unitcells_data job
def save_tdmaps_setup_data( id, tdmap_setup_json, tdmapsDBPath, tdmapsDBSchema):
	inserted_key = None
	sqlite3_conn = create_or_open_db(tdmapsDBPath, tdmapsDBSchema)
	sql = '''insert into tdmaps ( id ) VALUES( ? );'''
	id_key = None
	sqlite3_conn.execute( sql,[ id_key ] )
	sqlite3_conn.commit()
	cur = sqlite3_conn.cursor()
	sql_select = "SELECT last_insert_rowid();"
	cur.execute(sql_select)
	result_string = cur.fetchone()
	if result_string:
		inserted_key = result_string[0]

	sqlite3_conn.close()
	return inserted_key	

def get_tdmaps_data( id, tdmapsDBPath, tdmapsDBSchema ):
	result = None
	inserted_key = None
	sqlite3_conn = create_or_open_db(tdmapsDBPath, tdmapsDBPath)
	cur = sqlite3_conn.cursor()
	sql = "SELECT id , exp_setup_conf_id, cells_conf_id, slices_conf_id, waves_conf_id, dats_conf_id, simgrids_conf_id FROM tdmaps WHERE id = {0}".format(id)
	cur.execute(sql)
	result_binary = cur.fetchone()
	if result_binary:
		result = { 
		'id': result_binary[0],
		'exp_setup_conf_id': result_binary[1],
		'cells_conf_id': result_binary[2],
		'slices_conf_id': result_binary[3],
		'waves_conf_id': result_binary[4],
		'dats_conf_id': result_binary[5],
		'simgrids_conf_id': result_binary[6]
		 }
	sqlite3_conn.close()
	return result

#####################################################
##################### BLUEPRINT #####################
#####################################################

tdmaps = Blueprint(
    'tdmaps', #name of module
    __name__,
    template_folder='templates' # templates folder
)

@tdmaps.route('/')
def index_tdmaps():
    return render_template('index_tdmaps.html')

@tdmaps.route('/<string:tdmapid>', methods = ['GET'])
def api_tdmaps_get(tdmapid):
	global apiVersion
	global tdmapsDBPath
	global tdmapsDBSchema
	status = None
	result = None
	data = get_tdmaps_data(tdmapid, tdmapsDBPath, tdmapsDBSchema)
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
		tdmap_link = "{0}api/tdmaps/{1}".format( request.host_url, tdmapid )
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "data" : data,
		        "links" : { "tdmap" : { "self" : tdmap_link } },  
		        }
		return_code = 200

	return jsonpify(result), return_code

@tdmaps.route('/setup', methods = ['POST'])
def api_tdmaps_setup():
	global apiVersion
	global tdmapsDBPath
	global tdmapsDBSchema
	status = None
	data_dict = None 
	if len(request.data) > 0:
		data_dict = json.loads( request.data )
	data = {}
	inserted_tdmap_id = save_tdmaps_setup_data(None, data_dict, tdmapsDBPath, tdmapsDBSchema)
	tdmap_link = "{0}api/tdmaps/{1}".format( request.host_url, inserted_tdmap_id )
	status = True
	data = { 'id' : inserted_tdmap_id }

	if status is None:
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
		        "links" : { "tdmap" : { "self" : tdmap_link } }, 
		        }
		return_code = 200

	return jsonpify(result), return_code