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
    """ Gets all records of a table from a database
        args:
            conn: Sqlite3 database connection object
            table: Table name
        returns: all records of the table from the database
    """

    return conn.execute("SELECT * from {}".format(table))

def get_topo_details():
    """ Gets the information about switches and links in the topology
        returns: list of switches and links
    """

    try:
        conn = sqlite3.connect(TOPOLOGY_DB)
    except:
        print("Error connecting to the database {}".format(TOPOLOGY_DB))
        return
    switches = ["s" + str(row[0]) for row in get_all_records(conn, SW_TABLE)]
    links = [("s" + str(row[0]), "s" + str(row[1]), {'src_port':row[2],
            'dst_port': row[3]}) for row in get_all_records(conn, LINKS_TABLE)]
    return switches, links

def get_edge_labels(G, label_name):
    """ Gets labels to be set on the edges based on the label_name
        args:
            G: The networkx graph object
            label: The label name that needs to be extracted from the graph object
    """

     return dict([((u,v,),d[label_name]) for u,v,d in G.edges(data=True)])

def set_edge_labels(G, pos, edge_labels, label_pos):
    """ Set labels on the edges of the graph
        args:
            G: The networkx graph object
            pos: Layout of the graph
            edge_labels: Labels to be set on the edges
            label_pos: Position of the labels on the edges
    """

    nx.draw_networkx_edge_labels(G, pos, edge_labels = edge_labels,
    label_pos = label_pos)

def draw_topology(switches, links):
    """ Function to draw the network topology
        args:
            switches: list of switches
            links: list of links
    """

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
    plt.savefig(TOPOLOGY_IMAGE)

if __name__ == "__main__":
    switches, links = get_topo_details()
    if switches or links:
        draw_topology(switches, links)
