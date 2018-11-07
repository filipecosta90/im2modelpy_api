
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
import redis
import jsonschema
from flask import send_file
import cv2
import pickle
from PIL import Image
import scipy.misc

#so that we can import globals
sys.path.append('../..')

from globals import *

def get_default_json( ):
	return { 
  "description" : "",
  "data_type" : None,
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
def read_dat_file( full_dat_path, n_cols, n_rows, data_type=np.int32 ):
	result = True
	arr2 = np.fromfile(full_dat_path, dtype=data_type)
	arr2 = arr2.reshape(n_cols, n_rows)
	arr2 = np.flipud( arr2 )
	#print( type(arr2) )
	return result, arr2

def read_image_file( full_dat_path, n_cols, n_rows, data_type=np.int32 ):
	result = True
	img = Image.open(full_dat_path)
	arr2 = np.array(img)
	print( arr2.shape )
	#arr2 = np.fromfile(full_dat_path, dtype=data_type)
	#arr2 = arr2.reshape(n_cols, n_rows)
	#arr2 = np.flipud( arr2 )
	#print( type(arr2) )
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

@dats.route('/<string:datid>', methods = ['GET'])
def api_dats_get(datid):
	global apiVersion
	status = None
	result = None
	data_dict = None 
	data = None
	error_message = "something went wrong"

	r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
	metadata = r.hmget(datid, ['metadata'])
	if metadata[0] is not None:
		decompressed_result = zlib.decompress(metadata[0])
		data_dict = json.loads(decompressed_result.decode('utf-8'))
		dats_link = "{0}api/dats/{1}".format( request.host_url, datid )
		bin_link = "{0}api/dats/{1}/bin".format( request.host_url, datid )
		status = True
	else:
		status = False

	if status is False:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": error_message,
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
		        "data" : data_dict, 
		        "links" : { "dats" : { "self" : dats_link, "bin" : bin_link } }, 
		        }
		return_code = 200

	return jsonpify(result), return_code


@dats.route('/<string:datid>/correlate/<string:template_datid>', methods = ['GET'])
def api_dats_correlate_get(datid,template_datid):
	global apiVersion
	status = False
	result = None
	data_dict = None 
	data = None
	error_message = "something went wrong"

	r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
	datbin_array = r.hmget(datid, ['bin'])
	template_datbin_array = r.hmget(template_datid, ['bin'])

	if len( datbin_array ) > 0 and len( template_datbin_array ) > 0:
		datbin_as_bytes = datbin_array[0]
		datbin = np.array( pickle.loads(datbin_as_bytes) )

		temple_datbin_as_bytes = template_datbin_array[0]
		template_datbin = np.array( pickle.loads(temple_datbin_as_bytes) )

		#normalized correlation, non-normalized correlation and sum-absolute-difference
		method = eval('cv2.TM_CCOEFF')

		# apply template matching
		res = cv2.matchTemplate(datbin.astype(np.float32),template_datbin.astype(np.float32),cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
		data_dict = {'min_val':min_val,'max_val':max_val,'min_loc':min_loc,'max_loc':max_loc}
		print( min_val, max_val, min_loc, max_loc )
		status = True

	if status is False:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": error_message,
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
		        "data" : data_dict,  
		        }
		return_code = 200

	return jsonpify(result), return_code
	

@dats.route('/<string:datid>/bin/image', methods = ['GET'])
def api_dats_bin_image_get(datid):
	global apiVersion
	global simgridsDBPath
	global simgridsDBSchema
	status = None
	result = None
	data_dict = None 
	data = None
	error_message = None
	r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
	datbin_array = r.hmget(datid, ['bin'])
	datbin_as_bytes = datbin_array[0]
	datbin = np.array( pickle.loads(datbin_as_bytes) )

	filename = '{0}.jpg'.format(datid)
	filepath = os.path.join( UPLOAD_FOLDER, filename ) 
	filepath = os.path.abspath(filepath)
	#np.save( filepath, datbin )
	scipy.misc.toimage(datbin).save(filepath)

	try:
		return send_file( filepath, as_attachment=True, attachment_filename=filename)
		os.remove( filepath )

	except Exception as e:
		return str(e)

	return_code = 200

	return jsonpify({}), return_code

@dats.route('/<string:datid>/bin', methods = ['GET'])
def api_dats_bin_get(datid):
	global apiVersion
	global simgridsDBPath
	global simgridsDBSchema
	status = None
	result = None
	data_dict = None 
	data = None
	error_message = None
	r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
	datbin = r.hmget(datid, ['bin'])
	filename = '{0}.npy'.format(datid)
	filepath = os.path.join( UPLOAD_FOLDER, filename ) 
	filepath = os.path.abspath(filepath)
	np.save( filepath, datbin )

	try:
		return send_file( filepath, as_attachment=True, attachment_filename=filename)
		os.remove( filepath )

	except Exception as e:
		return str(e)

	return_code = 200

	return jsonpify({}), return_code

@dats.route('/import', methods = ['POST'])
def api_dats_import_post():
	global apiVersion
	status = False
	data_dict = None 

	compressed_result = None
	datfile = None
	inserted_dat_id = None 
	np_data_type = None
	error_message = "something went wrong"
	if 'metadata' in request.files and 'bin' in request.files:
		metadatafile = request.files['metadata']
		filename = secure_filename( ntpath.basename( metadatafile.filename ) )
		filepath = os.path.join( UPLOAD_FOLDER, filename ) 
		metadatafile.save( filepath )
		with open (filepath) as jsonfile:
			data_dict = json.loads( jsonfile.read() )
		os.remove( filepath )

		try:
			jsonschema.validate( data_dict, get_schema_dats() )
			data_type = data_dict["data_type"]
			
			if data_type == "float32":
				np_data_type = np.float32

			elif data_type == "int32":
				np_data_type = np.int32

			elif data_type == "int16":
				np_data_type = np.int16

			file = request.files['bin']
			filename = secure_filename( ntpath.basename( file.filename ) )
			filepath = os.path.join( UPLOAD_FOLDER, filename ) 
			file.save( filepath )
			
			if np_data_type is not None:
				n_rows = data_dict["dimensions"]["n_rows"]
				n_cols = data_dict["dimensions"]["n_cols"]		
				status, datfile = read_image_file( filepath, n_rows, n_cols, np_data_type )
			
			os.remove( filepath )
		
			compressed_result = zlib.compress( json.dumps(data_dict).encode('utf-8') )
			
			if datfile is not None and compressed_result is not None:
				r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
				redis_key = r.incr('dats_key')
				bin_as_bytes = pickle.dumps(datfile)
				status = r.hmset( redis_key, { 'metadata' : compressed_result , 'bin' : bin_as_bytes } )
				data_dict["id"] = redis_key
				dats_link = "{0}api/dats/{1}".format( request.host_url, redis_key )
				bin_link = "{0}api/dats/{1}/bin".format( request.host_url, redis_key )

		except jsonschema.exceptions.ValidationError as ve:
			error_message = str(ve)
			status = False
			pass

	if status is False:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": error_message,
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
		        "data" : data_dict, 
		        "links" : { "dats" : { "self" : dats_link, "bin" : bin_link } }, 
		        }
		return_code = 200

	return jsonpify(result), return_code

@dats.route('/', methods = ['POST'])
def api_dats_add():
	global apiVersion
	global datsDBPath
	global datsDBSchema
	status = False
	data_dict = None 

	compressed_result = None
	datfile = None
	inserted_dat_id = None 
	np_data_type = None
	error_message = "something went wrong"
	if 'metadata' in request.files and 'bin' in request.files:
		metadatafile = request.files['metadata']
		filename = secure_filename( ntpath.basename( metadatafile.filename ) )
		filepath = os.path.join( UPLOAD_FOLDER, filename ) 
		metadatafile.save( filepath )
		with open (filepath) as jsonfile:
			data_dict = json.loads( jsonfile.read() )

		os.remove( filepath )

		try:
			jsonschema.validate( data_dict, get_schema_dats() )
			data_type = data_dict["data_type"]
			
			if data_type == "float32":
				np_data_type = np.float32

			elif data_type == "int32":
				np_data_type = np.int32

			elif data_type == "int16":
				np_data_type = np.int16

			file = request.files['bin']
			filename = secure_filename( ntpath.basename( file.filename ) )
			filepath = os.path.join( UPLOAD_FOLDER, filename ) 
			file.save( filepath )
			
			if np_data_type is not None:
				n_rows = data_dict["dimensions"]["n_rows"]
				n_cols = data_dict["dimensions"]["n_cols"]		
				status, datfile = read_dat_file( filepath, n_rows, n_cols, np_data_type )
			
			os.remove( filepath )
		
			compressed_result = zlib.compress( json.dumps(data_dict).encode('utf-8') )
			
			if datfile is not None and compressed_result is not None:
				r = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
				redis_key = r.incr('dats_key')
				bin_as_bytes = pickle.dumps(datfile)
				status = r.hmset( redis_key, { 'metadata' : compressed_result , 'bin' : bin_as_bytes } )
				data_dict["id"] = redis_key
				dats_link = "{0}api/dats/{1}".format( request.host_url, redis_key )
				bin_link = "{0}api/dats/{1}/bin".format( request.host_url, redis_key )

		except jsonschema.exceptions.ValidationError as ve:
			error_message = str(ve)
			status = False
			pass

	if status is False:
		result = {
		        "apiVersion": apiVersion,
		        "params": request.args,
		        "method": request.method,
		        "took": 0,
		        "error" : {
		            "code": 404,
		            "message": error_message,
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
		        "data" : data_dict, 
		        "links" : { "dats" : { "self" : dats_link, "bin" : bin_link } }, 
		        }
		return_code = 200

	return jsonpify(result), return_code
