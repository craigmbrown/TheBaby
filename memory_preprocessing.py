from generate_graph import Graph, GraphGenerator, OntologyEnhancer
from load_data import TextProcessor
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import ChatOpenAI
import os
from datetime import datetime
import glob
from visualize_graph import NodeSimilaritySearchMan
from neo4j import GraphDatabase
import os 
import json
import webbrowser
from dotenv import load_dotenv
import logging
import argparse
from generate_from_file import (
    get_nodes_rels_from_current_ontology_file,
    export_current_ontology_to_json
)

load_dotenv()
from datetime import datetime
logging.basicConfig(
    level=logging.WARNING,  
    format='%(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(f"logs/memory_preprocessing_logs/logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            logging.StreamHandler()  # Also output to console
        ]  
)

logger = logging.getLogger(__name__)


def get_latest_file_alternative(folder_path, file_pattern="*"):
    """
    Alternative version that works with different timestamp formats
    
    Args:
        folder_path: Path to the folder containing timestamped files
        file_pattern: Pattern to match specific files (e.g., "data_*.json")
        
    Returns:
        str: Path to the most recent file
    """
    files = glob.glob(os.path.join(folder_path, file_pattern))
    
    if not files:
        return None
        
    def extract_timestamp_flexible(filename):
        """Try different timestamp formats"""
        formats = [
            # Standard format: YYYY-MM-DD_HHMMSS
            ('%Y-%m-%d_%H%M%S', r'_(\d{4}-\d{2}-\d{2}_\d{6})'),
            # Compact format: YYYYMMDD_HHMMSS
            ('%Y%m%d_%H%M%S', r'_(\d{8}_\d{6})'),
            # With milliseconds: YYYYMMDD_HHMMSS_MSS
            ('%Y%m%d_%H%M%S_%f', r'_(\d{8}_\d{6}_\d{3})')
        ]
        
        import re
        for date_format, pattern in formats:
            try:
                # Try to find timestamp using regex pattern
                match = re.search(pattern, filename)
                if match:
                    timestamp_str = match.group(1)
                    return datetime.strptime(timestamp_str, date_format)
            except:
                continue
                
        return datetime.min

    # Get the most recent file
    latest_file = max(files, key=extract_timestamp_flexible)
    return latest_file


def generate(
    file_path,
    uri=os.getenv("NEO4J_URI"), 
    username=os.getenv("NEO4J_USERNAME"), 
    password=os.getenv("NEO4J_PASSWORD"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    rel_labels=None,
    nodes_labels=None,
    viz=True,
    require_confirmation=True
):
    try:
        neo4j_driver = GraphDatabase.driver(uri, auth=(username, password))
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=openai_api_key)

        # Load file text
        data = TextProcessor(file_path=file_path).load_text()
        if not data:
            logger.error("could not load data")
            return
        logger.info("File loaded successfully.")
        texts = [doc.page_content for doc in data]

        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        docs = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        db = Neo4jVector.from_documents(
        data, embeddings, url=uri, username=username, password=password
        )

        if not rel_labels or not nodes_labels:
            nodes_labels = []
            rels_labels = []

            # Generate Ontology
            enhancer = OntologyEnhancer(neo4j_driver, llm)
            final_ontology = enhancer.process_multiple_texts(texts, require_confirmation=require_confirmation)
            
            final_nodes = final_ontology.nodes
            final_rels = final_ontology.relationships

            current_rels_labels = enhancer.existing_ontology["relationships"] if enhancer.existing_ontology["relationships"] else []
            current_nodes_labels = enhancer.existing_ontology["nodes"] if enhancer.existing_ontology["nodes"] else []

            relationship_labels = [rel.relationship_type for rel in final_rels] + current_rels_labels
            node_labels = [node.node_type for node in final_nodes] + current_nodes_labels

            rel_labels = list(set(relationship_labels))
            nodes_labels = list(set(node_labels))

        logger.info(f"Your final nodes are: {nodes_labels}")
        logger.info(f"Your final relationships are: {rel_labels}")

        # Generate Graph
        graph_generator = GraphGenerator(relationship_labels=rel_labels, node_labels=nodes_labels, node_properties=["name", "description"])
        graph_documents = graph_generator.generate_graph(data)
        if not graph_documents:
            logger.error("could not extract triples")
            return

        # Add graph to Neo4j
        graph_database = Graph(uri=uri, username=username, password=password)
        data_added = graph_database.add_graph(graph_documents)
        if data_added == False:
            logger.error("could not extract data")
            return 

        logger.info("Graph generation and insertion into Neo4j completed successfully.")
        logger.info("Getting Current ontology.....:")

        ontology_path = export_current_ontology_to_json()
        rels, nodes = get_nodes_rels_from_current_ontology_file(ontology_path)
        
        logger.info(f"Current Nodes: {nodes}")
        logger.info(f"Current Relationships {rels}")

        if viz:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            search_man = NodeSimilaritySearchMan(driver)

            neighbors = search_man.find_relationship_neighbors()
            if neighbors:
                logger.info("Found information for the entire graph......................")
                html_file_path = search_man.visualize_relationship_graph_interactive(neighbors)
                logger.info(f"Full graph visualization saved to '{html_file_path}'.")

        return True
    except Exception as e:
        logger.error(f"Error occurred while processing data: {e}")
        return None

def generate_from_file(
    document_file_path,
    ontology_file_path="logs/ontologies",    
    URI=os.getenv("NEO4J_URI"),
    USER=os.getenv("NEO4J_USERNAME"),
    PASS=os.getenv("NEO4J_PASSWORD"),
    require_confirmation=True,
    viz=True
):
    if document_file_path:
        ontology_file = get_latest_file_alternative(ontology_file_path,"ontology_*.json")
        rels, nodes = get_nodes_rels_from_current_ontology_file(ontology_file)
        if rels != [] and nodes != []:
            processed = generate(
                document_file_path,
                uri=URI,
                username=USER,
                password=PASS,
                rel_labels=rels,
                nodes_labels=nodes,
                require_confirmation=require_confirmation,
                viz=viz
            )
            if processed:
                logger.info("Success..terminating")
            else:
                logger.error("Failed..terminating")
        else:
            logger.error("Your ontology is currently empty")
    else:
        logger.error("Please provide full path to your document")

def generate_from_baseline_ontology(
    file_path,
    require_confirmation=True,
    viz=True
):
    node_types = [
        "AI_Orchestrator", "AI_Agent", "Model", "Task", "Workflow",
        "Artifact", "Tool", "User", "Dataset", "Knowledge",
        "Interaction", "System"
    ]

    relationship_types = [
        "EXECUTES", "COMPRISES", "GENERATES", "UTILIZES", "ANALYZES",
        "TRIGGERS", "OPTIMIZES", "CONTAINS", "VALIDATES", "FEEDS",
        "CONFIGURES", "RECOMMENDS"
    ]

    processed = generate(
        file_path=file_path,
        rel_labels=relationship_types,
        nodes_labels=node_types,
        require_confirmation=require_confirmation,
        viz=viz
    )
    return processed

def interactive_mode():
    file = input("Please enter the full path to your file: ")

    if file.strip():
        generation_choice = input(
            "How would you like to generate your graph?\n"
            "Type 'A' to generate based on your current ontology\n"
            "Type 'B' to generate using a new custom ontology\n"
            "Type 'C' to generate based on the predefined baseline ontology\n"
            "Choice: "
        ).strip().upper()

        if generation_choice == "A":
            logger.info("Exporting current ontology....")
            ontology_path = export_current_ontology_to_json()
            logger.info("Generating graph...")
            generate_from_file(file.strip())

        elif generation_choice == "B":
            processed = generate(file.strip())
            if processed:
                logger.info("Completed successfully.")

        elif generation_choice == "C":
            processed = generate_from_baseline_ontology(file.strip())
            if processed:
                logger.info("Completed successfully.")

        else:
            logger.error("Please make a valid choice.")
    else:
        logger.error("Please provide a valid file path.")

def main():
    parser = argparse.ArgumentParser(description='Generate and update ontology from text files')
    parser.add_argument('--file', help='Path to the input file')
    parser.add_argument('--mode', choices=['current', 'custom', 'baseline'], 
                      help='Generation mode: current (from existing ontology), custom (new ontology), or baseline')
    parser.add_argument('--no-confirm', action='store_true', 
                      help='Skip user confirmation and automatically accept suggestions')
    parser.add_argument('--no-viz', action='store_true',
                      help='Skip visualization generation')
    
    args = parser.parse_args()

    # If no arguments provided, run in interactive mode
    if not args.file and not args.mode:
        interactive_mode()
        return

    # Validate file path when in command line mode
    if not args.file:
        logger.error("File path is required when using command line arguments")
        return

    viz = not args.no_viz
    require_confirmation = not args.no_confirm

    if args.mode == 'current':
        ontology_path = export_current_ontology_to_json()
        generate_from_file(args.file,  require_confirmation=require_confirmation, viz=viz)
    
    elif args.mode == 'custom':
        processed = generate(args.file, require_confirmation=require_confirmation, viz=viz)
        if processed:
            logger.info("Completed successfully.")
    
    elif args.mode == 'baseline':
        processed = generate_from_baseline_ontology(args.file, require_confirmation=require_confirmation, viz=viz)
        if processed:
            logger.info("Completed successfully.")

if __name__ == "__main__":
    main()
