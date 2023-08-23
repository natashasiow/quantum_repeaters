import networkx as nx

from simplequantnetsim.graph import network, reset_graph_state, update_graph_params
from networkx.generators import *
from networkx.readwrite import json_graph
import json
import os
import csv


def save_graph(G, name="tree"):
    """
    Save Networkx graph as json object in graphs folder

    Input Pararmeters:
    G    - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    name - graph filename
    """
    with open("graphs//" + name + ".json", "w") as outfile1:
        outfile1.write(json.dumps(json_graph.node_link_data(G)))


def load_graph(filename):
    """
    load Networkx graph as json object in graphs folder

    Input Pararmeters:
    filesname - graph filename (.json file only) (name excluding directory or ".json")

    Outputs:
        G        - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    """
    with open("graphs//" + filename + ".json", "r") as f:
        js_graph = json.loads(f.read())
    return json_graph.node_link_graph(js_graph)


def make_graphs_list():
    """
    create Networkx json graphs from .txt files in graphs folder
    Note:
    Also create 6x6 grid graph
    initialise p and Qc as 1
    """
    current_directory = os.getcwd()
    graphs_dir = os.path.join(current_directory, "graphs")
    G = network(6, 6)
    update_graph_params(G, p=1, Qc=1)  # initalise p,Qc as 1
    save_graph(G, "grid_6_6")
    for file in [file for file in os.listdir(graphs_dir) if file.endswith(".txt")]:
        print(os.path.join(graphs_dir, file))
        file_name = file.split("\\")[0]
        G = load_from_file(file=file_name)
        nom = file_name[:-4]
        update_graph_params(G, p=1, Qc=1)  # initalise p,Qc as 1
        save_graph(G, name=file_name)


def load_from_file(file="UKnet.txt"):  # could be done better?
    """
    load Networkx graph from file in graphs folder

    Input Pararmeters:
    file - graph filename (.txt file only)

    Outputs:
        G   - Networkx graph G(V,E) which defines the topology of the network. see graphs.py for more details
    Note:
    initialise p and Qc as 1
    """
    current_directory = os.getcwd()
    graphs_dir = os.path.join(current_directory, "graphs")
    title = True
    data = []
    with open(graphs_dir + "/" + file, encoding="ISO-8859-1") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter="\t")
        for row in csv_reader:
            if title:
                title = False
            else:
                data.append(
                    (int(row[0]), int(row[1]), float(row[2]) / 100)
                )  # note dividing km by 100 for the length
    G = nx.Graph()
    for x in data:
        G.add_edge(str(x[0]), str(x[1]), length=x[2])
    update_graph_params(G, p=1, Qc=1)  # default p,Qc as 1
    reset_graph_state(G)  # initalise link data
    return G


def get_G_list():  # Load saved topologies from graphs folder
    """
    load all Networkx graphs from file in graphs folder

    Outputs:
    G_list          - List of Networkx graphs G(V,E) which defined from txt files in 'graphs' folder (+ grid graph)
    name_list_clear - List of Names of graphs in folder (hardcoded)
    Note:
    initial p and Qc set to 1
    """
    name_list_clear = ["ARPA", "EON", "Eurocore", "NSFnet", "UKnet", "USnet", "Grid"]
    # Create list of graphs G
    G_list, name_list = [], []
    current_directory = os.getcwd()
    graphs_dir = os.path.join(current_directory, "graphs")
    for file in os.listdir(graphs_dir):
        if file.endswith(".txt"):
            file_name = file.split("\\")[0]
            G = load_from_file(file=file_name)
            G_list.append(G)
            name_list.append(file_name[:-4])
    G_list.append(load_graph("grid_6_6"))
    name_list.append("grid_6_6")
    return G_list, name_list_clear
