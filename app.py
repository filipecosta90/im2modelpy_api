
from globals import *

from blueprints import app

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.run(host='0.0.0.0', port=5000, debug=True)