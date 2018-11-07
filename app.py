
from globals import *
import time 
from blueprints import app
from flask import g
import threading 

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_request
def start_timer():
	if 'start' not in g:
		g.start = {}
	g.start[threading.currentThread().getName()] = time.time()
	#print( "{0},{1}".format(threading.currentThread().getName(),time.time()) )

app.run( host='0.0.0.0', port=5000, debug=True )