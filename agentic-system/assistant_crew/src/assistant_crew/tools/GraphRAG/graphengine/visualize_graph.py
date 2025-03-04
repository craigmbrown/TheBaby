from neo4j import GraphDatabase
from typing import Optional, Union, List, Dict 
import numpy as np 
from openai import OpenAI
from pyvis.network import Network
import os 
from dotenv import load_dotenv
load_dotenv(override=True)
import logging
from datetime import datetime
logging.basicConfig(

    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_embedding(text, model="text-embedding-3-small"):
    client = OpenAI()
    text = text.replace("\n", " ")
    
    return client.embeddings.create(input = [text], model=model).data[0].embedding

def calculate_similarity(embedding1, embedding2):
    # Placeholder for similarity calculation, e.g., using cosine similarity
    # Ensure both embeddings are numpy arrays for calculation
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

class NodeSimilaritySearchMan():

    def __init__(self, neo4j_driver: GraphDatabase):
        """
        Initialize the NodeSimilaritySearchMan with a Neo4j driver instance.

        Args:
            neo4j_driver (GraphDatabase): The Neo4j driver to facilitate connection to the database.
        """
        self.driver = neo4j_driver

    def find_relationship_neighbors(self, node_name: str = None) -> List[Dict[str, Union[int, str]]]:
        """
        Finds neighbors of a given node based on direct relationships in the graph.
        If no node name is provided, fetches all nodes and their relationships.

        Args:
            node_name (str, optional): The name of the node for which to find neighbors.

        Returns:
            List[Dict[str, Union[int, str]]]: A list of dictionaries, each representing a neighbor with its ID and name.
        """
        neighbors = []

        try:
            with self.driver.session() as session:
                if node_name:
                    query = """
                        MATCH (n)-[r]->(neighbor)
                        WHERE n.name = $node_name
                        RETURN neighbor.name AS name, type(r) AS relationship_type
                        UNION
                        MATCH (n)<-[r]-(neighbor)
                        WHERE n.name = $node_name
                        RETURN neighbor.name AS name, type(r) AS relationship_type
                    """
                    params = {"node_name": node_name}
                else:
                    query = """
                        MATCH (n)-[r]-(neighbor)
                        WHERE n.name IS NOT NULL AND neighbor.name IS NOT NULL
                        RETURN n.name AS name, neighbor.name AS neighbor_name, type(r) AS relationship_type
                    """
                    params = {}

                result = session.run(query, params)
                if node_name:
                    neighbors = [
                        {
                            "name": record["name"],
                            "relationship_type": record["relationship_type"]
                        }
                        for record in result
                    ]
                else:
                    neighbors = [
                        {
                            "source": record["name"],
                            "target": record["neighbor_name"],
                            "relationship_type": record["relationship_type"]
                        }
                        for record in result
                    ]
                    logger.info(neighbors)
        except Exception as e:
            logger.error(f"Error occurred while finding neighbors: {e}")
        return neighbors


    def visualize_relationship_graph_interactive(self, neighbors=None, node_name=None, graph_path="logs/graphs", edge_label='relationship_type'):
        """
        Visualizes the relationship graph interactively.

        Args:
            neighbors (list, optional): List of neighbor relationships to visualize. Defaults to None.
            node_name (str, optional): Name of the central node. Defaults to None.
            graph_name (str, optional): Name of the graph for the HTML file. Defaults to "graph".
            edge_label (str, optional): The label for edges. Defaults to 'relationship_type'.

        Returns:
            str: File path to the saved HTML graph.
        """
        try:
            # Initialize the Network with cdn_resources set to 'remote'
            net = Network(notebook=True, cdn_resources='remote')

            if node_name and neighbors:
                # Add the main node
                net.add_node(node_name, label=node_name, color='red')

                # Add neighbors and edges to the network
                for neighbor in neighbors:
                    title = neighbor.get('neighbor_chunks_summary', '')
                    if edge_label == 'similarity':  # Adjust title for similarity
                        title += f" (Similarity: {neighbor[edge_label]})"
                    else:
                        title += f" ({edge_label}: {neighbor[edge_label]})"
                    net.add_node(neighbor['name'], label=neighbor['name'], title=title)
                    net.add_edge(node_name, neighbor['name'], title=str(neighbor[edge_label]))
            else:
                # Add all nodes and edges for full graph visualization
                nodes = set()
                for relationship in neighbors:
                    source = relationship['source']
                    target = relationship['target']
                    rel_type = relationship['relationship_type']

                    if source not in nodes:
                        net.add_node(source, label=source, color='blue')
                        nodes.add(source)

                    if target not in nodes:
                        net.add_node(target, label=target, color='green')
                        nodes.add(target)

                    net.add_edge(source, target, title=rel_type)

            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            file_path = graph_path+f"/graph_{timestamp}.html"
            # Save the graph to an HTML file
            net.save_graph(file_path)

            return file_path
        except Exception as e:
            logger.error(f"Error occurred while visualizing the graph: {e}")

if __name__ == "__main__":

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    search_man = NodeSimilaritySearchMan(driver)

    # Prompt the user for input
    node_name_input = input("Please enter the data for the knowledge graph (or leave blank for the full graph): ")

    if node_name_input.strip():
        neighbors = search_man.find_relationship_neighbors(node_name_input.strip())
        if neighbors:
            logger.info(f"Found Information for '{node_name_input}'......................")
            logger.info(f"Neighbors: {neighbors}........................")
            html_file_path = search_man.visualize_relationship_graph_interactive(neighbors, node_name_input.strip(), "relationship")

            logger.info(f"Graph visualization saved to '{html_file_path}'.")
    else:
        neighbors = search_man.find_relationship_neighbors()
        if neighbors:
            logger.info("Found information for the entire graph......................")
            html_file_path = search_man.visualize_relationship_graph_interactive(neighbors, graph_name="full_graph")

            logger.info(f"Full graph visualization saved to '{html_file_path}'.")

    driver.close()

