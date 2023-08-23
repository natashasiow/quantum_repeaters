import numpy as np


def run_entanglement_step(G, used_nodes, nodes=False):
    """
    simulate the link generation and decoherence for a single timeslot (step)

    Input Pararmeters:
    G          - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    used_nodes - List of paths of used nodes (only updated if nodes parameter is True)
    nodes      - (optional) include simulating "node" entanglement in model
    """
    r_list = np.random.rand(
        len(G.edges())
    )  # array of random numbers between 0 and 1 (size of number of edges)
    for edge, r in zip(G.edges().values(), r_list):
        if edge["entangled"]:  #  if entangled edge exists inc age
            edge["age"] += 1

            if (
                edge["age"] >= edge["Qc"]
            ):  # If the edge is now too old then discard it - only required for entangled edges
                edge["entangled"] = False
                edge["age"] = 0

        if (
            not edge["entangled"] and edge["p_edge"] > r
        ):  # greater is correct (hint p_edge = 0, rand =  0) and (hint p_edge = 1, rand =  0.999...)
            edge["entangled"] = True
            edge["age"] = 0

    if nodes:
        for node_name in G.nodes():
            node = G.nodes[node_name]

            if node["entangled"]:
                node["age"] += 1

            if node["age"] >= node["Qc"]:
                node["entangled"] = False
                edge["age"] = 0

        for path in used_nodes:
            path["age"] += 1

        used_nodes[:] = [
            path for path in used_nodes if path["age"] < G.nodes[path["destination_node"]]["Qc"]
        ]
