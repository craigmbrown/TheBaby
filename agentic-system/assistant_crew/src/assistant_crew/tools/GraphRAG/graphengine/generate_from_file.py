from datetime import datetime
import json
from typing import Dict, List
from neo4j import Driver
from neo4j import GraphDatabase
import os 
from dotenv import load_dotenv
load_dotenv()

def export_current_ontology_to_json(
    URI=os.getenv("NEO4J_URI"),
    USER=os.getenv("NEO4J_USERNAME"),
    PASS=os.getenv("NEO4J_PASSWORD"),
    output_dir: str = "logs/ontologies"
) -> Dict[str, List[str]]:
    """
    Export existing ontology from Neo4j database to JSON file
    
    Args:
        driver: Neo4j driver instance
        output_path: Path to save JSON file (default: ontology.json)
        
    Returns:
        Dictionary containing nodes and relationships
        {
            "nodes": [list_of_node_labels],
            "relationships": [list_of_relationship_types]
        }
        
    Raises:
        neo4j.exceptions.Neo4jError: If database connection fails
        IOError: If file writing fails
    """
    driver = GraphDatabase.driver(URI, auth=(USER, PASS))
    ontology_data = {
        "nodes": [],
        "relationships": []
    }
    
    try:
        with driver.session() as session:
            # Get node labels
            node_result = session.run("CALL db.labels()")
            ontology_data["nodes"] = [record["label"] for record in node_result]
            
            # Get relationship types
            rel_result = session.run("CALL db.relationshipTypes()")
            ontology_data["relationships"] = [record["relationshipType"] for record in rel_result]
        file_name = f"ontology_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        file = output_dir+"/"+file_name            
        # Write to JSON file
        with open(file, 'w') as f:
            json.dump(ontology_data, f, indent=2)
            
    except Exception as e:
        raise RuntimeError(f"Failed to export ontology: {str(e)}") from e
        
    return  file



def get_nodes_rels_from_current_ontology_file(file_path):
    """
    Extracts the 'relationships' and 'nodes' keys from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        tuple: A tuple containing two lists - relationships and nodes.
    """
    with open(file_path, "r") as f:
        json_data = json.load(f)

    relationships = json_data.get("relationships", [])
    nodes = json_data.get("nodes", [])

    return relationships, nodes




