
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

def get_default_json( ):
	return { 
  "description" : "",
  "dimensions" : { "n_rows": None, "n_cols": None },
  "margins" : { "nm" : None, "px" : None },
  "sampling_rate" : { "x_nm_per_pixel" : None, 
  					  "y_nm_per_pixel" : None
  },
  "roi_rectangle" : { "x": None, "y": None, "n_rows": None, "n_cols": None, "center_x" :None , "center_y" : None },
  "image_statistical" : { "mean" : [], "stddev" : [] }
}

def get_schema_dats( ):
	schema = None
	with open('blueprints/dats/schemas/schema_dats.json', 'r') as f:
		schema_data = f.read()
		schema = json.loads(schema_data)
	return schema

  # backgroud read_dat_file
  # The image dimension is equal to the number of data points (NX horizontally, NY vertically) with the physical data origin (0,0) in the lower left image corner.
def read_dat_file( full_dat_path, normalize, n_cols, n_rows, margin = 0 ):
	result = False
	arr2 = np.fromfile(full_dat_path, dtype=np.float32)
	arr2 = arr2.reshape(n_cols, n_rows)
	arr2 = np.flipud( arr2 )
	dat_shape = arr2.shape
	print( dat_shape[0] )
	arr2 = arr2[ margin : dat_shape[0] - margin, margin : dat_shape[0] - margin ]
	return result, arr2

#####################################################
##################### BLUEPRINT #####################
#####################################################

dats = Blueprint(
    'dats', #name of module
    __name__,
    template_folder='templates' # templates folder
)

@dats.route('/', methods = ['GET'])
def index_dats():
    return render_template('index_dats.html')

@dats.route('/', methods = ['POST'])
def api_dats_add():
	global apiVersion
	global datsDBPath
	global datsDBSchema
	status = False
	data_dict = None 
	if len(request.data) > 0:
		data_dict = json.loads( request.data )

	if 'file' in request.files:
		file = request.files['file']
		filename = secure_filename( ntpath.basename( file.filename ) )
		filepath = os.path.join( UPLOAD_FOLDER, filename ) 
		file.save( filepath )
		#secure version of filename
		cell = ase.io.read( filepath )
		os.remove( filepath )
		data = None
		inserted_simgrid_id, data = save_simgrids_setup_data( None, data_dict, simgridsDBPath, simgridsDBSchema )
	
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
