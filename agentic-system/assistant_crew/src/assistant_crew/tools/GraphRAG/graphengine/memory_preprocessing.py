from .generate_graph import Graph, GraphGenerator, OntologyEnhancer
from .load_data import TextProcessor
from langchain_openai import ChatOpenAI
import os
from typing import Optional,List
from langchain.schema import Document
from datetime import datetime
import glob
from .visualize_graph import NodeSimilaritySearchMan
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging
import argparse
from .generate_from_file import (
    get_nodes_rels_from_current_ontology_file,
    export_current_ontology_to_json
)

load_dotenv()
import os
from pathlib import Path

# Get the GraphRAG package root directory
GRAPHRAG_ROOT = Path(__file__).parent.parent

# Create logs directory using absolute path
log_dir = os.path.join(GRAPHRAG_ROOT, "graphengine", "logs", "memory_preprocessing_logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}")),
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
    texts: List[str],
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
    """
    Generate the graph from a list of texts.
    
    This function now assumes that file processing (via TextProcessor) has already
    been done and a list of text strings is provided.
    """
    try:
        if not texts:
            logger.error("No texts provided for graph generation.")
            return False

        # Setup drivers/LLM, etc.
        neo4j_driver = GraphDatabase.driver(uri, auth=(username, password))
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=openai_api_key)
        
        # If labels are not provided, decide based on the mode.
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
                return False

        logger.info(f"Final node labels: {nodes_labels}")
        logger.info(f"Final relationship labels: {rel_labels}")

        # Generate graph documents using the provided texts.
        graph_generator = GraphGenerator(
            relationship_labels=rel_labels,
            node_labels=nodes_labels,
            node_properties=["name", "description"]
        )
        docs = [Document(page_content=text) for text in texts]
        graph_documents = graph_generator.generate_graph(docs)  # <-- Use texts directly.
        if not graph_documents:
            logger.error("Could not extract graph triples")
            return False

        # Add graph documents to Neo4j.
        graph_database = Graph(uri=uri, username=username, password=password)
        data_added = graph_database.add_graph(graph_documents)
        if not data_added:
            logger.error("Failed to add graph to Neo4j")
            return False

        logger.info("Graph generation and insertion into Neo4j completed successfully.")
        logger.info("Exporting current ontology...")
        ontology_path = export_current_ontology_to_json()
        rels, nodes = get_nodes_rels_from_current_ontology_file(ontology_path)
        logger.info(f"Current Nodes: {nodes}")
        logger.info(f"Current Relationships: {rels}")

        if viz:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            search_man = NodeSimilaritySearchMan(driver)
            if neighbors := search_man.find_relationship_neighbors():
                logger.info("Graph visualization found.")
                html_file_path = search_man.visualize_relationship_graph_interactive(neighbors)
                logger.info(f"Graph visualization saved to '{html_file_path}'.")
        return True
    except Exception as e:
        logger.error(f"Error occurred while processing data: {e}")
        return False


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
                    [doc.page_content for doc in TextProcessor(file_path=document_file_path).load_text()],
                    mode=mode,
                    uri=URI,
                    username=USER,
                    password=PASS,
                    rel_labels=rels,
                    nodes_labels=nodes,
                    require_confirmation=require_confirmation,
                    viz=viz
                )
                if processed == True:
                    logger.info("Graph generation succeeded based on current ontology.")
                    return True
                else:
                    logger.error("Graph generation failed.")
                    return False
            else:
                logger.error("Your ontology is currently empty")
                return False
        else:
            # For custom ontology generation, ignore existing ontology file.
            processed = generate(
                [doc.page_content for doc in TextProcessor(file_path=document_file_path).load_text()],
                mode=mode,
                uri=URI,
                username=USER,
                password=PASS,
                require_confirmation=require_confirmation,
                viz=viz
            )
            if processed == True:
                logger.info("Graph generation succeeded with custom ontology.")
                return True
            else:
                logger.error("Graph generation failed.")
                return False
    else:
        logger.error("Please provide full path to your document.")
        return False


    

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
        [doc.page_content for doc in TextProcessor(file_path=file_path).load_text()],
        rel_labels=relationship_types,
        nodes_labels=node_types,
        require_confirmation=require_confirmation,
        viz=viz
    )
    return processed or False


def interactive_mode():
    
    if file := input("Please enter the full path to your file: ").strip():

        generation_choice = input(
            "How would you like to generate your graph?\n"
            "Type 'A' to generate based on your current ontology\n"
            "Type 'B' to generate using a new custom ontology\n"
            "Type 'C' to generate based on the predefined baseline ontology\n"
            "Choice: "
        ).strip().upper()
        if generation_choice == "A":
            logger.info("Exporting current ontology...")
            from graphengine.generate_from_file import export_current_ontology_to_json
            export_current_ontology_to_json()
            logger.info("Generating graph based on current ontology...")
            generate_from_file(file, mode="current")
        elif generation_choice == "B":
            mode = input("Choose ontology mode (expressive/strict): ").strip().lower()
            if mode not in ["expressive", "strict"]:
                print("Invalid mode selected; defaulting to expressive.")
                mode = "expressive"
            processed = generate_from_file(file, mode=mode)
            if processed == True:
                logger.info("Graph generation with custom ontology completed successfully.")
            else:
                logger.error("Graph generation failed.")
        elif generation_choice == "C":
            processed = generate_from_baseline_ontology(file)
            if processed == True:
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



from typing import Optional, Literal

def generate_neo4j_graph(
    file: Optional[str] = None,
    mode: Optional[Literal["current", "custom", "baseline"]] = None,
    ontology_mode: Literal["expressive", "strict"] = "expressive",
    no_confirm: bool = False,
    no_viz: bool = False
) -> None:
    """
    Processes ontology generation based on supplied parameters.

    Parameters:
        file (Optional[str]): Path to the input file.
        mode (Optional[Literal["current", "custom", "baseline"]]): Generation mode.
            If both `file` and `mode` are None, the function calls interactive_mode().
        ontology_mode (Literal["expressive", "strict"]): For custom ontology generation, either:
            "expressive" (generic) or "strict" (constrained). Defaults to "expressive".
        no_confirm (bool): If True, automatically accept suggestions and skip confirmations.
            Defaults to False.
        no_viz (bool): If True, skip generation of visualizations. Defaults to False.
    """
    # If both file and mode are missing, launch interactive mode.
    if not file and not mode:
        interactive_mode()
        return

    # If file is missing while mode is provided, log an error.
    if not file:
        logger.error("File path is required when using parameters (file argument missing)")
        return

    viz = not no_viz
    require_confirmation = not no_confirm

    if mode == "current":
        generate_from_file(file, mode="current", require_confirmation=require_confirmation, viz=viz)
    elif mode == "custom":
        generate(file, mode=ontology_mode, require_confirmation=require_confirmation, viz=viz)
    elif mode == "baseline":
        generate_from_baseline_ontology(file, require_confirmation=require_confirmation, viz=viz)


from unittest.mock import patch, call
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "test_id, file, mode, ontology_mode, no_confirm, no_viz, expected_calls",
    [
        (
            "happy_path_current_mode",
            "assets/new-script.txt",
            "current",
            "expressive",  # Not used in this mode
            False,
            False,
            [call("assets/new-script.txt", mode="current", require_confirmation=True, viz=True)],
        ),
        (
            "happy_path_custom_mode_expressive",
            "assets/new-script.txt",
            "custom",
            "expressive",
            True,
            True,
            [call("assets/new-script.txt", mode="expressive", require_confirmation=False, viz=False)],
        ),
        (
            "happy_path_custom_mode_strict",
            "assets/new-script.txt",
            "custom",
            "strict",
            False,
            True,
            [call("assets/new-script.txt", mode="strict", require_confirmation=True, viz=False)],
        ),
        (
            "happy_path_baseline_mode",
            "assets/new-script.txt",
            "baseline",
            "expressive",  # Not used in this mode
            True,
            False,
            [call("assets/new-script.txt", require_confirmation=False, viz=True)],
        ),
        (
            "missing_file",
            None,
            "current",
            "expressive",
            False,
            False,
            [],
        ),
    ],
)
@patch("memory_preprocessing.generate_from_file")
@patch("memory_preprocessing.generate")
@patch("memory_preprocessing.generate_from_baseline_ontology")
@patch("memory_preprocessing.interactive_mode")
def test_generate_neo4j_graph_parameters(
    mock_interactive_mode,
    mock_generate_from_baseline_ontology,
    mock_generate,
    mock_generate_from_file,
    test_id,
    file,
    mode,
    ontology_mode,
    no_confirm,
    no_viz,
    expected_calls,
):
    """
    Tests the generate_neo4j_graph function with various parameters.
    """
    # Act
    generate_neo4j_graph(file=file, mode=mode, ontology_mode=ontology_mode, no_confirm=no_confirm, no_viz=no_viz)

    # Assert the correct function was called
    if not file and not mode:
        mock_interactive_mode.assert_called_once()
    elif not file:
        assert mock_generate_from_file.call_count == 0
        assert mock_generate.call_count == 0
        assert mock_generate_from_baseline_ontology.call_count == 0

    if mode in ["current", "custom"]:
        # In both cases the file is processed first and then generate is invoked via generate_from_file.
        mock_generate_from_file.assert_has_calls(expected_calls)
    elif mode == "baseline":
        mock_generate_from_baseline_ontology.assert_has_calls(expected_calls)





if __name__ == "__main__":
    generate_neo4j_graph(
    "assets/new-script.txt",
    "custom",
    "expressive"
)