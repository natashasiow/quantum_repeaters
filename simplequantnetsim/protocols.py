import networkx as nx
import numpy as np

from simplequantnetsim.graph import (
    reset_graph_usage,
    update_graph_usage,
    update_usage_from_subgraph,
    reset_graph_state,
    get_entangled_subgraph,
)
from simplequantnetsim.sim import run_entanglement_step

from networkx.algorithms.approximation.steinertree import steiner_tree


def SP_protocol(G, users, timesteps, reps, count_fusion=False):
    """
    Shortest Path protocol taken from [SPsource] The protocol attempts to generate bell pairs between a central node and a set of users.
    This is done by attmepting entanglement along a set of edge disjoint paths, all connected to the centre node. The protocol
    requires a graph with only the edges required for SP routing are present. The protocol terminates once an entanglement is shared between
    the centre and all other users

    Input Pararmeters:
    G         - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    users     - List of nodes in G which between which a GHZ should be shared. users[0] is the centre of the star which should be calculated before sending to SP_protocol
    timesteps - number of timesteps the protocol will run for before terminating without a successful GHZ generation,
    reps      - number of repetions the protocol will run for the imput parameters to generate a dataset.

    Outputs:
    rate                   -  entanglement rate (ER) (average GHZs generated per timeslot)
    multipartite_gen_time  -  array (length of reps)  array of timesteps until successful GHZ generated, if no successful GHZ generated value is -1
    avg_links_used         -  number of entanglement links used per repetition for successful GHZ generation
    """
    J = _get_star(
        G, users
    )  # get the shortest star in G, which connects all destination_nodes to the source_node

    er, multipartite_gen_time, avg_links_used = _run_protocol(
        J, users, timesteps, reps, _SD_protocol, nodes=True, count_fusion=count_fusion
    )
    update_usage_from_subgraph(G, J)
    return er, multipartite_gen_time, avg_links_used


def MPG_protocol(G, users, timesteps, reps, count_fusion=False):
    """
    Multipath protocol - Greedy. Protoocol attempts shortest path routing between centre node and each other user seqentially to generate N bell pairs (1 shared between centre and each of N users). The protocol terminates once bell pairs is shared as this is sufficent for generating a GHZ.

    Input Pararmeters:
    G         - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    users     - List of nodes in G that must share a GHZ state.  users[0] is the centre of the star which should be calculated before sending to SP_protocol
    timesteps - number of timesteps the protocol will run for before terminating without a successful GHZ generation,
    reps      - number of repetions the protocol will run for the imput parameters to generate a dataset.

    Outputs:
    rate                   -  entanglement rate (ER) (average GHZs generated per timeslot)
    multipartite_gen_time  -  array (length of reps)  array of timeslots until successful GHZ generated, if no successful GHZ generated value is -1
    avg_links_used         -  number of entanglement links used per repetition for successful GHZ generation
    """
    return _run_protocol(
        G, users, timesteps, reps, _SD_protocol, nodes=True, count_fusion=count_fusion
    )


def MPC_protocol(G, users, timesteps, reps, count_fusion=False):
    """
    Multipath protocol - Cooperative. Entanglement is attempted along all edges for input graph. If all users are in the same CC of nodes connected by links, this is sufficent for a GHZ state and protocol is assumed successful

    Inputs:
    G         - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    users     - List of nodes in G that must share a GHZ state
    timesteps - number of timesteps the protocol will run for before terminating without a successful GHZ generation,
    reps      - number of repetions the protocol will run for to attempt to distribute a GHZ state before recording a failure (i.e. if all p=0).

    Outputs:
    rate                   -  entanglement rate (ER)) (average GHZs generated per timeslot)
    multipartite_gen_time  -  array (length of reps)  results ER in GHZ/tslot where tslot is number of timesteps, if no successful GHZ generated value is -1
    avg_links_used         -  number of entanglement links used per repetition for successful GHZ generation
    """
    return _run_protocol(G, users, timesteps, reps, _CC_protocol, count_fusion=count_fusion)


def _run_protocol(G, users, timesteps, reps, success_protocol, nodes=False, count_fusion=False):
    reset_graph_usage(G)
    multipartite_gen_time = -1 * np.ones((reps))
    links_used = 0
    for i in range(reps):
        reset_graph_state(G)
        used_nodes = []
        t = 0
        while t < timesteps and multipartite_gen_time[i] == -1:  # for t timesteps or until success
            t += 1
            run_entanglement_step(G, used_nodes, nodes)  # SP and MPG require nodes True
            H = get_entangled_subgraph(G)
            success = success_protocol(G, H, users, used_nodes, count_fusion)  # protocol specific
            if success:
                # do fusion (assumed ideal)
                multipartite_gen_time[i] = t
                # add usage & used links
                for path in used_nodes:
                    links_used += path["edge_count"]
                    for n in path["nodes"]:
                        G.nodes[n]["usage_count"] += 1
    rate = _multipartite_rate(multipartite_gen_time, timesteps)
    update_graph_usage(G, reps)
    avg_links_used = links_used / reps
    return rate, multipartite_gen_time, avg_links_used


# for MPC
def _CC_protocol(G, H, users, used_nodes, count_fusion=False):
    CC = nx.node_connected_component(H, users[0])

    # can check a set is within a set with operators
    if not (set(users) <= CC):
        return False  # unsuccessful, all users not in same connected component which is needed for tree between them to exist

    K = steiner_tree(
        H.subgraph(CC), users, weight="length"
    )  # calculate Steiner tree connecting users

    # only nodes that perform entanglement swapping (2 edges) and (optionally) fusion (3 edges or user with 2 edges) is recorded as used
    used_nodes.append(
        {
            "nodes": [node for node in K.nodes if _count_node(K, node, users, count_fusion)],
            "edge_count": K.number_of_edges(),
        }
    )

    return True


def _count_node(K, node, users, count_fusion=False):
    count_node = False

    # entanglement swapping
    if K.degree(node) == 2:
        # if node is a user then it performs fusion
        if (node not in users) or count_fusion:
            count_node = True

    # fusion
    elif K.degree(node) > 2 and count_fusion:
        count_node = True

    return count_node


# for SP and MPG
def _SD_protocol(G, H, users, used_nodes, count_fusion=False):
    source_node = users[0]
    destination_nodes = users[1:]

    for destination_node in destination_nodes:
        if not G.nodes[destination_node]["entangled"] and nx.has_path(
            H, source_node, destination_node
        ):
            path = nx.shortest_path(H, source_node, destination_node)
            _create_bell_pair(G, H, path, used_nodes)
    return all([G.nodes[x]["entangled"] for x in destination_nodes])


def _create_bell_pair(G, H, path, used_nodes):
    """
    create Bell pair between source node and destination node, record as value "entangled" in destination node in graph G. This is done by performing entanglement swapping at all nodes in the shortest path

    Inputs:
    G                - Networkx graph G(V,E') which defines the topology of the graph (or subgraph which entanglement is attempted on).
    H                - Networkx graph G'(V,E') which defines the topology of the links.
    route            - path of nodes selected to perform entanglement swapping between route[0]=source route[-1] = destination
    used_nodes       - list of paths of the nodes that performed entanglement swapping to be updated

    """
    for u, v in zip(path[:-1], path[1:]):  # node - next_node pairs
        H.remove_edge(u, v)
        edge = G.edges[u, v]
        edge["entangled"] = False
        edge["age"] = 0

    destination_node = G.nodes[path[-1]]
    destination_node["entangled"] = True
    destination_node["age"] = 0

    used_nodes.append(
        {"nodes": path[1:-1], "age": 0, "destination_node": path[-1], "edge_count": len(path) - 1}
    )


def _multipartite_rate(gen_times, max_timesteps):
    """
    Returns entanglement rate (ER) in terms of GHZ/timeslots and the total timesteps

    Input Pararmeters:
    gen_times     - Array of how many timeslots it took to generate a GHZ state, if no GHZ was generated a value of -1 is recorded
    max_timesteps - The number of timesteps the simulation attempted to generate a GHZ before terminating
    Output Pararmeters:
        - ER (total number of GHZ states generated / total number of timesteps run)
    """
    successful_attempts = gen_times[np.where(gen_times != -1)]
    fail_count = len(gen_times) - len(successful_attempts)
    t_total = (
        sum(successful_attempts) + fail_count * max_timesteps
    )  # total timesteps = (sum of timesteps when success + sum of failures*max_t)
    return len(successful_attempts) / t_total  # number GHZ states / total timesteps


def _get_star(G, users):
    """
    get edge disjoint shortest paths from set source (first node in list)

        Input Pararmeters:
        G      - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
        users  - List of nodes in G which between which a GHZ should be shared. users[0] is the centre of the star which should be calculated before sending to SP_protocol
        Outputs:
        J      - Networkx graph J(V,E') with edges of the star-path connecting each destination user with the source node

    Notes:
    non-optimal star found ? #
    if no edge-disjoint star-route exists, then allow edge sharing (this is none edge disjoint and will give ER = 0 if Qc = 1. If Qc>1 then protocol feasible as time division multiplexing (TDM) allows bell pairs to be generated
    TODO redo this function ES - 17/11/2022
    """

    # get edge disjoint shortest paths from set source (first node in list)
    # if edge disjoint paths don't exist, allow shared edge use
    # NON optimal good enough for grids with corner users
    source_node = users[0]
    destination_nodes = users[1:]
    # copy G twice H for calculation and J for reduced graph
    T = G.__class__()
    T.add_nodes_from(G.nodes(data=True))
    T.add_edges_from(G.edges(data=True))
    # Graph H is a deepcopy of G, if an edge is added to J it is removed from H, routing is then performed over H. This enforces edge disjoint routing
    J = G.__class__()
    J.add_nodes_from(G.nodes(data=True))  # Graph J with nodes from G and no edges (yet!)
    edge_disjoint = True  # G.degree[source_node]>= len(destination_nodes) # can it be edge disjoint
    for destination_node in destination_nodes:
        if nx.has_path(T, source_node, destination_node):
            path = nx.shortest_path(T, source_node, destination_node)
            for u, v in zip(path[:-1], path[1:]):  # node- next_node pairs
                T.remove_edge(u, v)  # remove path from H
                J.add_edge(u, v)  # add edge to new graph J
        else:
            edge_disjoint = False  # unused flag to say if J is edge_disjoint
            path = nx.shortest_path(G, source_node, destination_node)
            for u, v in zip(path[:-1], path[1:]):
                J.add_edge(u, v)  # add edge to new graph J
                if T.has_edge(u, v):
                    T.remove_edge(u, v)  # remove path from H
    [
        J[u][v].update(G.get_edge_data(u, v)) for (u, v) in J.edges()
    ]  # add edge data to edge in J from G
    return J
