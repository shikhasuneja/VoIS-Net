#!/bin/sh

ryu run --observe-links topology_discovery.py &
python3 network_visualization.py &
python3 alexa.py &
python3 webpage.py &

