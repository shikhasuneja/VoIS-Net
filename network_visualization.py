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
HOSTS_TABLE = 'host_connections'
TOPOLOGY_IMAGE = 'static/topology.png'
PORT_UP = 'UP'
PORT_DOWN = 'DOWN'

def get_all_records(conn, table):
    """ Gets all records of a table from a database
        args:
            conn: Sqlite3 database connection object
            table: Table name
        returns: all records of the table from the database
    """

    try:
        records = conn.execute("SELECT * from {}".format(table))
        return records
    except sqlite3.OperationalError:
        print("Cannot connect to the table - {}".format(table))
        return []

def get_topo_details():
    """ Gets the information about switches, links, and hosts in the topology
        returns: list of switches, links and hosts
    """

    try:
        conn = sqlite3.connect(TOPOLOGY_DB)
    except:
        print("Error connecting to the database {}".format(TOPOLOGY_DB))
        return
    switches = ["s" + str(row[0]) for row in get_all_records(conn, SW_TABLE)]
    links = [("s" + str(row[0]), "s" + str(row[1]), {'src_port':row[2],
            'dst_port': row[3], 'status': row[4]})
            for row in get_all_records(conn, LINKS_TABLE)]
    hosts_switches_links = [("s" + str(row[0]), str(row[2]), {'src_port': row[1]})
            for row in get_all_records(conn, HOSTS_TABLE)]
    hosts = [host[1] for host in hosts_switches_links]
    return switches, links, hosts, hosts_switches_links

def get_edge_labels(links, label_name):
    """ Gets labels to be set on the edges based on the label_name
        args:
            links: links between switches as per the database
            label: The label name that needs to be extracted from the graph object
    """

    labels_dict = {}
    for link in links:
        # graph edges = (tail, head) = (dst_dpid, src_dpid)
        labels_dict[(link[1], link[0])] = link[2][label_name]
    return labels_dict

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

def draw_nodes(G, switches, hosts):
    """ Draw nodes of the graph including switches and hosts
        args:
            G: The networkx graph object
            switches: switches in the topology as per the topology database
            hosts: hosts in the topology as per the topology database
    """

    G.add_nodes_from(switches)
    G.add_nodes_from(hosts)
    global pos
    pos = nx.spring_layout(G)         # positions for all nodes
    nx.draw_networkx_nodes(G, pos, node_shape = 's', labels = True,
        nodelist = switches, node_color = 'skyblue', node_size = 6000,
        edgecolors = 'k')
    nx.draw_networkx_nodes(G, pos, node_shape = 's', labels = True,
        nodelist = hosts, node_color = 'skyblue', node_size = 12000,
        edgecolors = 'k', alpha = 0.2)

def draw_edges(G, links, hosts_switches_links):
    """ Draw edges of the graph including links between all nodes (switches/hosts)
        args:
            G: The networkx graph object
            links: links between switches
            hosts_switches_links: links between hosts and switches
    """

    G.add_edges_from(links)
    G.add_edges_from(hosts_switches_links)
    up_links, down_links = check_link_status(links)
    nx.draw_networkx_edges(G, pos, edgelist = up_links, edge_color = 'g')
    nx.draw_networkx_edges(G, pos, edgelist = down_links, edge_color = 'r')
    nx.draw_networkx_edges(G, pos, edgelist = hosts_switches_links,
    edge_color = 'g')

def check_link_status(links):
    """ Checks the status (up/down) of the links, and segregates them into two
        lists based on the status
        args:
            links: links between switches as per the topology database
        returns:
            up_links: the links with status "UP"
            down_links: the links with status "DOWN"
     """

    up_links = []
    down_links = []
    for link in links:
        status = link[-1]['status']
        if status == PORT_UP:
            up_links.append(link)
        elif status == PORT_DOWN:
            down_links.append(link)
    return up_links, down_links

def draw_labels(G, links):
    """ Draws labels on the graph (nodes/edges)
        args:
            G: The graph object
            links: links between switches
    """

    nx.draw_networkx_labels(G, pos, font_size = 10, font_family='sans-serif')
    src_ports = get_edge_labels(links, 'src_port')
    set_edge_labels(G, pos, src_ports, 0.2)
    dst_ports = get_edge_labels(links, 'dst_port')
    set_edge_labels(G, pos, dst_ports, 0.8)

def draw_topology(switches, links, hosts, hosts_switches_links, cli):
    """ Function to draw the network topology
        args:
            switches: list of switches in the topology
            links: list of links in the topology
            hosts: list of hosts in the topology
            cli: argument to imply if the visualization is CLI-based or not
    """

    G = nx.MultiGraph()
    plt.figure(num=TOPOLOGY_IMAGE, figsize=(12,12), dpi=80, edgecolor='k')
    draw_nodes(G, switches, hosts)
    draw_edges(G, links, hosts_switches_links)
    draw_labels(G, links)
    plt.axis('off')
    plt.savefig(TOPOLOGY_IMAGE)
    print("Saved the network topology as {}".format(TOPOLOGY_IMAGE))
    if not cli:
        plt.clf()

def visualize_topology(cli = False):
    """ Function to fetch information and visualize the network topology
        args:
            cli: argument to imply if the visualization is CLI-based or not
    """

    switches, links, hosts, hosts_switches_links = get_topo_details()
    if switches or links or hosts:
        draw_topology(switches, links, hosts, hosts_switches_links, cli)
