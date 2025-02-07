from generate_graph import Graph, GraphGenerator, OntologyEnhancer
from load_data import TextProcessor
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import ChatOpenAI
import os
from typing import Optional,List
from datetime import datetime
import glob
from visualize_graph import NodeSimilaritySearchMan
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging
import argparse
from generate_from_file import (
    get_nodes_rels_from_current_ontology_file,
    export_current_ontology_to_json
)

load_dotenv()
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(f"logs/memory_preprocessing_logs/logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        logging.StreamHandler()  
    ]
)
logger = logging.getLogger(__name__)


def get_latest_file_alternative(folder_path, file_pattern="*"):
    files = glob.glob(os.path.join(folder_path, file_pattern))
    if not files:
        return None
    def extract_timestamp_flexible(filename):
        formats = [
            ('%Y-%m-%d_%H%M%S', r'_(\d{4}-\d{2}-\d{2}_\d{6})'),
            ('%Y%m%d_%H%M%S', r'_(\d{8}_\d{6})'),
            ('%Y%m%d_%H%M%S_%f', r'_(\d{8}_\d{6}_\d{3})')
        ]
        import re
        for date_format, pattern in formats:
            try:
                match = re.search(pattern, filename)
                if match:
                    timestamp_str = match.group(1)
                    return datetime.strptime(timestamp_str, date_format)
            except:
                continue
        return datetime.min
    latest_file = max(files, key=extract_timestamp_flexible)
    return latest_file

def generate(
    file_path: str,
    mode: str = "expressive",
    uri: str = os.getenv("NEO4J_URI"), 
    username: str = os.getenv("NEO4J_USERNAME"), 
    password: str = os.getenv("NEO4J_PASSWORD"),
    openai_api_key: str = os.getenv("OPENAI_API_KEY"),
    rel_labels: Optional[List[str]] = None,
    nodes_labels: Optional[List[str]] = None,
    viz: bool = True,
    require_confirmation: bool = True
):
    try:
        neo4j_driver = GraphDatabase.driver(uri, auth=(username, password))
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=openai_api_key)

        # Load file text using TextProcessor
        data = TextProcessor(file_path=file_path).load_text()
        if not data:
            logger.error("Could not load data")
            return None
        logger.info("File loaded successfully.")
        texts = [doc.page_content for doc in data]

        
        # If labels are not provided, decide based on the mode:
        if not rel_labels or not nodes_labels:
            if mode.lower() == "current":
                ontology_file = get_latest_file_alternative("logs/ontologies", "ontology_*.json")
                rels, nodes = get_nodes_rels_from_current_ontology_file(ontology_file)
            else:
                # Custom ontology generation (expressive or strict)
                enhancer = OntologyEnhancer(neo4j_driver, llm)
                final_ontology = enhancer.process_multiple_texts(texts, mode=mode, require_confirmation=require_confirmation)
                final_nodes = final_ontology.nodes
                final_rels = final_ontology.relationships
                current_rels_labels = enhancer.existing_ontology.get("relationships", [])
                current_nodes_labels = enhancer.existing_ontology.get("nodes", [])
                relationship_labels = [rel.relationship_type for rel in final_rels] + current_rels_labels
                node_labels = [node.node_type for node in final_nodes] + current_nodes_labels
                rels = list(set(relationship_labels))
                nodes = list(set(node_labels))
            if rels and nodes and rels != [] and nodes != []:
                rel_labels = rels
                nodes_labels = nodes
            else:
                logger.error("Ontology is currently empty")
                return None

        logger.info(f"Final node labels: {nodes_labels}")
        logger.info(f"Final relationship labels: {rel_labels}")

        # Generate graph documents
        graph_generator = GraphGenerator(relationship_labels=rel_labels, node_labels=nodes_labels, node_properties=["name", "description"])
        graph_documents = graph_generator.generate_graph(data)
        if not graph_documents:
            logger.error("Could not extract graph triples")
            return None

        # Add graph documents to Neo4j
        graph_database = Graph(uri=uri, username=username, password=password)
        data_added = graph_database.add_graph(graph_documents)
        if not data_added:
            logger.error("Failed to add graph to Neo4j")
            return None

        logger.info("Graph generation and insertion into Neo4j completed successfully.")
        logger.info("Exporting current ontology...")
        ontology_path = export_current_ontology_to_json()
        rels, nodes = get_nodes_rels_from_current_ontology_file(ontology_path)
        logger.info(f"Current Nodes: {nodes}")
        logger.info(f"Current Relationships: {rels}")

        if viz:
            driver = GraphDatabase.driver(uri, auth=(username, password))

            search_man = NodeSimilaritySearchMan(driver)
            neighbors = search_man.find_relationship_neighbors()
            if neighbors:
                logger.info("Graph visualization found.")
                html_file_path = search_man.visualize_relationship_graph_interactive(neighbors)
                logger.info(f"Graph visualization saved to '{html_file_path}'.")
        return True
    except Exception as e:
        logger.error(f"Error occurred while processing data: {e}")
        return None


def generate_from_file(
    document_file_path: str,
    ontology_file_path: str = "logs/ontologies",
    URI: str = os.getenv("NEO4J_URI"),
    USER: str = os.getenv("NEO4J_USERNAME"),
    PASS: str = os.getenv("NEO4J_PASSWORD"),
    mode: str = "expressive",
    require_confirmation: bool = True,
    viz: bool = True
):
    if document_file_path:
        if mode.lower() == "current":
            ontology_file = get_latest_file_alternative(ontology_file_path, "ontology_*.json")
            rels, nodes = get_nodes_rels_from_current_ontology_file(ontology_file)
            if rels != [] and nodes != []:
                processed = generate(
                    document_file_path,
                    mode=mode,
                    uri=URI,
                    username=USER,
                    password=PASS,
                    rel_labels=rels,
                    nodes_labels=nodes,
                    require_confirmation=require_confirmation,
                    viz=viz
                )
                if processed:
                    logger.info("Graph generation succeeded based on current ontology.")
                else:
                    logger.error("Graph generation failed.")
            else:
                logger.error("Your ontology is currently empty")
        else:
            # For custom ontology generation, ignore existing ontology file.
            processed = generate(
                document_file_path,
                mode=mode,
                uri=URI,
                username=USER,
                password=PASS,
                require_confirmation=require_confirmation,
                viz=viz
            )
            if processed:
                logger.info("Graph generation succeeded with custom ontology.")
            else:
                logger.error("Graph generation failed.")
    else:
        logger.error("Please provide full path to your document.")


def generate_from_baseline_ontology(
    file_path: str,
    require_confirmation: bool = True,
    viz: bool = True
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
    file = input("Please enter the full path to your file: ").strip()
    if file:
        generation_choice = input(
            "How would you like to generate your graph?\n"
            "Type 'A' to generate based on your current ontology\n"
            "Type 'B' to generate using a new custom ontology\n"
            "Type 'C' to generate based on the predefined baseline ontology\n"
            "Choice: "
        ).strip().upper()
        if generation_choice == "A":
            logger.info("Exporting current ontology...")
            from generate_from_file import export_current_ontology_to_json
            export_current_ontology_to_json()
            logger.info("Generating graph based on current ontology...")
            generate_from_file(file, mode="current")
        elif generation_choice == "B":
            mode = input("Choose ontology mode (expressive/strict): ").strip().lower()
            if mode not in ["expressive", "strict"]:
                print("Invalid mode selected; defaulting to expressive.")
                mode = "expressive"
            processed = generate(file, mode=mode)
            if processed:
                logger.info("Graph generation with custom ontology completed successfully.")
            else:
                logger.error("Graph generation failed.")
        elif generation_choice == "C":
            processed = generate_from_baseline_ontology(file)
            if processed:
                logger.info("Graph generation based on baseline ontology completed successfully.")
            else:
                logger.error("Graph generation failed.")
        else:
            logger.error("Please make a valid choice.")
    else:
        logger.error("Please provide a valid file path.")


def main():
    parser = argparse.ArgumentParser(description='Generate and update ontology from text files')
    parser.add_argument('--file', help='Path to the input file')
    parser.add_argument('--mode', choices=['current', 'custom', 'baseline'], 
                        help='Generation mode: current (from existing ontology), custom (new ontology), or baseline')
    parser.add_argument('--ontology-mode', choices=['expressive', 'strict'], default='expressive',
                        help='For custom ontology generation: expressive (generic) or strict (constrained)')
    parser.add_argument('--no-confirm', action='store_true', help='Skip user confirmation and automatically accept suggestions')
    parser.add_argument('--no-viz', action='store_true', help='Skip visualization generation')
    args = parser.parse_args()

    if not args.file and not args.mode:
        interactive_mode()
        return

    if not args.file:
        logger.error("File path is required when using command line arguments")
        return

    viz = not args.no_viz
    require_confirmation = not args.no_confirm

    if args.mode == 'current':
        generate_from_file(args.file, mode="current", require_confirmation=require_confirmation, viz=viz)
    elif args.mode == 'custom':
        generate(args.file, mode=args.ontology_mode, require_confirmation=require_confirmation, viz=viz)
    elif args.mode == 'baseline':
        generate_from_baseline_ontology(args.file, require_confirmation=require_confirmation, viz=viz)


if __name__ == "__main__":
    main()
