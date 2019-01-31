"""
Team VoIS-Network
Date: 01/28/2019
Purpose: Network Topology Visualization
Author: Shikha Suneja
"""

import sqlite3
import networkx as nx
import matplotlib.pyplot as plt

TOPOLOGY_DB = 'topology.db'
SW_TABLE = 'switches'
LINKS_TABLE = 'topo_connections'
TOPOLOGY_IMAGE = 'topology.png'

def get_all_records(conn, table):
    return conn.execute("SELECT * from {}".format(table))

def get_topo_details():
    conn = sqlite3.connect(TOPOLOGY_DB)
    switches = ["s" + str(row[0]) for row in get_all_records(conn, SW_TABLE)]
    links = [("s" + str(row[0]), "s" + str(row[1]), {'src_port':row[2],
            'dst_port': row[3]}) for row in get_all_records(conn, LINKS_TABLE)]
    return switches, links

def get_edge_labels(G, label):
     return dict([((u,v,),d[label]) for u,v,d in G.edges(data=True)])

def set_edge_labels(G, pos, edge_labels, label_pos):
    nx.draw_networkx_edge_labels(G, pos, edge_labels = edge_labels,
    label_pos = label_pos)

def draw_topology(switches, links):
    G = nx.MultiGraph()
    G.add_nodes_from(switches)
    G.add_edges_from(links)
    options = {'node_color': 'skyblue', 'node_shape': 's', 'node_size': 1500,
            'with_labels': True, 'font_weight': 'bold'}
    pos = nx.spring_layout(G)
    nx.draw(G, pos, **options)
    src_ports = get_edge_labels(G, 'src_port')
    set_edge_labels(G, pos, src_ports, 0.2)
    dst_ports = get_edge_labels(G, 'dst_port')
    set_edge_labels(G, pos, dst_ports, 0.8)
    plt.show()
    #plt.savefig(TOPOLOGY_IMAGE)

if __name__ == "__main__":
    switches, links = get_topo_details()
    draw_topology(switches, links)
