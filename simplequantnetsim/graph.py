import networkx as nx

from networkx.generators import *


def network(n, m):
    """
    function to generate 2d grid networkx graph with required edge and nodes attributes

    Input Pararmeters:
    G    - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    """
    G = nx.grid_2d_graph(n, m)  # n times m grid
    nx.set_edge_attributes(G, 1, "length")  # default edge length = 1km
    update_graph_params(G, p=1, Qc=1)  # initalise p,Qc as 1
    reset_graph_state(G)  # initialise link-state of network (as no entangled links present)
    reset_graph_usage(G)  # initialise usage params of network
    return G


def reset_graph_state(G):
    """
    function to initalise / reset the link state (e.g. if a link exists and its age) of graph G

    Input Pararmeters:
    G         - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    """
    nx.set_edge_attributes(G, False, "entangled")
    nx.set_node_attributes(G, False, "entangled")
    nx.set_edge_attributes(G, 0, "age")
    nx.set_node_attributes(G, 0, "age")


def reset_graph_usage(G):
    """
    function to initalise / reset the node usage param of graph G

    Input Pararmeters:
    G         - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    """
    nx.set_node_attributes(G, 0, "usage_count")
    nx.set_node_attributes(G, 0, "usage_fraction")


def update_graph_usage(G, reps):
    """
    function to calculate and update usage_fraction from a given number of reps

    Input Pararmeters:
    G         - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    reps - Total number of repetitions used to calculate usage fraction for each node (usage_count/reps)
    """
    for node in G.nodes:
        usage_count = G.nodes[node]["usage_count"]
        G.nodes[node]["usage_fraction"] = usage_count / reps


def update_graph_params(G, p=None, Qc=None):
    """
    function to set p and Qc to be the same value for all edges/nodes

    Input Pararmeters:
    G  - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    p  - edge link probability p, if inputted set all edges to have p_edge = p
    Qc - Decoherence time Qc, if inputted set all edges (and Nodes) to have decoherence time Qc
    """
    if Qc is not None:
        nx.set_node_attributes(G, Qc, "Qc")
        nx.set_edge_attributes(G, Qc, "Qc")
    if p is not None:
        nx.set_edge_attributes(G, p, "p_edge")


def set_p_edge(G, p_op=0.8, loss_dB=None):
    """
    function to set p as a function of loss parameters
    see networkx documentation

    Input Pararmeters:
    G  - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    p_op  - constant probability of failiure (see paper for more)
    loss_dB  - loss_dB is attenuation in dB/km
    """
    if loss_dB is None:
        update_graph_params(G, p=p_op)
    else:
        for edge in G.edges:
            length = G.edges[edge]["length"]
            p_loss = 10 ** -(loss_dB * length / 10)
            G.edges[edge]["p_edge"] = p_op * p_loss


def set_edge_length(G, length=1, p_op=0.8, loss_dB=0.2):
    """
    function to set length of all edges, p_edge will also be updated

    Input Pararmeters:
    G  - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    length - edge length in km
    p_op  - constant probability of failiure (see paper for more)
    loss_dB  - loss_dB is attenuation in dB/km
    """
    nx.set_edge_attributes(G, length, "length")
    set_p_edge(G, p_op, loss_dB)


def get_entangled_subgraph(G):
    """
    Create a subgraph G' of G, G' includes all nodes in G, and all edges with successful entanglement links
    Note G_prime is a deepcopy of data in G

    Input Pararmeters:
    G  - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    Output Pararmeters:
    G_prime - subgraph G' where only edges with entangled links are kept
    """
    G_prime = nx.Graph()
    G_prime.add_nodes_from(G)
    eligible_edges = [(u, v, e) for u, v, e in G.edges(data=True) if e["entangled"]]
    G_prime.add_edges_from(eligible_edges)

    return G_prime


def update_usage_from_subgraph(G, J):
    """
    Updates usage parameters in G using the ones from subgraph J

    Input Pararmeters:
    G  - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    J - Networkx graph which has the usage values
    """
    for node in J.nodes:
        G.nodes[node]["usage_count"] = J.nodes[node]["usage_count"]
        G.nodes[node]["usage_fraction"] = J.nodes[node]["usage_fraction"]


def remove_nodes(G: nx.Graph, min_usage, excluded_nodes=None):
    """
    Removes nodes from graph G that has a usage fraction under given min_usage, doesn't remove any nodes if given in excluded_nodes list.

    Input Pararmeters:
    G  - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    min_usage - usage_fraction cut-off for when to remove nodes
    excluded_nodes - list of nodes to not remove

    Outputs:
    count - number of removed nodes 
    """
    if excluded_nodes is None:
        excluded_nodes = []

    count = 0
    for node, usage in nx.get_node_attributes(G, "usage_fraction").items():
        if (usage < min_usage) and (node not in excluded_nodes):
            G.remove_node(node)
            count += 1

    return count
