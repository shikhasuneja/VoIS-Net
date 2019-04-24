"""
    Team VoIS-Network
    Purpose: VoIS-Network Webpage
    Author: Shikha Suneja
"""

import logging
from flask import Flask, render_template
from network_visualization import *
import os


logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

TOPOLOGY_IMAGE = 'static/topology.png'

@app.route('/displayTopology', methods=['GET'])
def displayTopologyPage():
    visualize_topology()
    return render_template('displayTopology.html', topo_image=TOPOLOGY_IMAGE)


@app.after_request
def add_header(r):
    """
    Add headers to ensure the images are not cached.
    """

    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded = True)
