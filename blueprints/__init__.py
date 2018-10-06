
from flask import Flask, render_template, request, redirect
from flask_jsonpify import jsonpify
from blueprints.cells.cells import cells
from blueprints.tdmaps.tdmaps import tdmaps
from blueprints.dats.dats import dats


app = Flask(__name__)
app.register_blueprint(cells, url_prefix='/api/cells')
app.register_blueprint(tdmaps, url_prefix='/api/tdmaps')
app.register_blueprint(dats, url_prefix='/api/dats')