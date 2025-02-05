import os
import re
from typing import List, Optional, Dict
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from dotenv import load_dotenv
load_dotenv()
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from neo4j import GraphDatabase


# Define the Node model (common to both modes)
class Node(BaseModel):
    node_type: str = Field(..., description="The label indicating the type of the node")
    node_description: str = Field(..., description="The description of what this node entity signifies")

# Define two Relationship models: one for expressive mode and one for strict mode.
class RelationshipExpressive(BaseModel):
    relationship_type: str = Field(..., description="The label indicating the type of the relationship")
    relationship_description: str = Field(..., description="A free-form description of the relationship")

class RelationshipStrict(BaseModel):
    relationship_type: str = Field(..., description="The label indicating the type of the relationship")
    relationship_description: str = Field(
        ...,
        description="The description must be in the format 'ChildEntity -> ParentEntity'"
    )
    @validator('relationship_description')
    def must_follow_format(cls, value):
        # Enforce exactly one arrow (->) with extra spaces allowed.
        if not re.match(r"^\s*\S.*\s*->\s*\S.*\s*$", value):
            raise ValueError("relationship_description must be in the format 'ChildEntity -> ParentEntity'")
        return value

# We define two Ontology models. Their nodes are the same; relationships differ.
class ExpressiveOntology(BaseModel):
    nodes: List[Node] = Field(..., description="The list of suggested node labels")
    relationships: List[RelationshipExpressive] = Field(..., description="The list of suggested relationship labels")

class StrictOntology(BaseModel):
    nodes: List[Node] = Field(..., description="The list of suggested node labels")
    relationships: List[RelationshipStrict] = Field(..., description="The list of suggested relationship labels")

# For simplicity, we alias Ontology to one of these based on the mode later.
Ontology = ExpressiveOntology  # default alias; we override in the chain

# =============================================================================
# OntologyEnhancer Class with Conditional Structured Output Models
# =============================================================================
class OntologyEnhancer:
    def __init__(self, neo4j_driver: GraphDatabase.driver, llm: ChatOpenAI):
        self.driver = neo4j_driver
        self.llm = llm
        self.existing_ontology = self._get_existing_ontology()
        self.merge_chain = self._create_merge_chain()

    def _create_merge_chain(self):
        merge_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             """You are an ontology integration expert. Merge multiple ontology suggestions into a single unified ontology by:
  1. Combining similar node/relationship types.
  2. Merging descriptions while preserving important details.
  3. Removing duplicates.
  4. Maintaining naming conventions.

Guidelines:
- Use PascalCase for nodes and UPPER_SNAKE_CASE for relationships.
- Return only the merged ontology."""
            ), 
            ("human", "Ontologies to merge:\n{ontologies}")
        ])
        # We always use the expressive model here for merging; you could also switch based on a mode if needed.
        return merge_prompt | self.llm.with_structured_output(ExpressiveOntology)

    def _create_ontology_chain(self, mode: str = "expressive"):
        """
        Create a chain for ontology suggestion.
        For mode "expressive", allow free-form relationship descriptions.
        For mode "strict", require relationship descriptions in the format "ChildEntity -> ParentEntity".
        """
        if mode == "expressive":
            system_prompt = (
                "You are an expert ontology engineer. Analyze the provided text and existing database schema to:\n"
                "1. Identify new node types using broad, generic categories (e.g., Actor, Action, Resource, Structure, etc.)\n"
                "2. Identify new relationship types using broad, ambiguous terms (e.g., AFFECTS, CONTAINS, DERIVESFROM, USES, etc.)\n"
                "3. Merge similar elements while allowing multiple inheritance and circular references, aiming for high connectivity.\n"
                "Use PascalCase for node labels and UPPER_SNAKE_CASE for relationship types.\n"
                "Return only the merged ontology."
            )
            output_model = ExpressiveOntology
        elif mode == "strict":
            system_prompt = (
                "You are an expert ontology engineer. Analyze the provided text and existing database schema to:\n"
                "1. Identify new node types with clear, distinct subtypes (e.g., Agent, Process, DataObject, etc.)\n"
                "2. Identify new relationship types with strict definitions (e.g., EXECUTES, CONTAINS, PRODUCES, CONSUMES, DEPENDSON, VALIDATES, SUBCLASSOF, etc.)\n"
                "3. Enforce that each node (when applicable) has only one parent via a SUBCLASSOF relationship and that cycles are disallowed.\n"
                "Use PascalCase for node labels and UPPER_SNAKE_CASE for relationship types.\n"
                "When suggesting a SUBCLASSOF relationship, output its description in the exact format 'ChildEntity -> ParentEntity'.\n"
                "Return only the merged ontology."
            )
            output_model = StrictOntology
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", 
            "Ontology suggestion:\n"
            "Text to analyze:\n{text}\n\n"
            "Existing Nodes: {existing_nodes}\n"
            "Existing Relationship Types: {existing_rels}"
            )
        ])
        return prompt | self.llm.with_structured_output(output_model)


    def _serialize_ontology(self, ontology: ExpressiveOntology) -> str:
        nodes = "\n".join([f"Node: {n.node_type} - {n.node_description}" for n in ontology.nodes])
        rels = "\n".join([f"Relationship: {r.relationship_type} - {r.relationship_description}" for r in ontology.relationships])
        return f"Nodes:\n{nodes}\nRelationships:\n{rels}"

    def merge_ontologies(self, ontologies: List[ExpressiveOntology]) -> ExpressiveOntology:
        if not ontologies:
            return ExpressiveOntology(nodes=[], relationships=[])
        if len(ontologies) == 1:
            return ontologies[0]
        serialized = "\n\n".join([self._serialize_ontology(o) for o in ontologies])
        return self.merge_chain.invoke({"ontologies": serialized})

    def process_multiple_texts(self, texts: List[str], mode: str = "expressive", require_confirmation: bool = True) -> ExpressiveOntology:
        suggestions = [self.suggest_enhancements(text, mode=mode) for text in texts]
        merged = self.merge_ontologies(suggestions)
        if mode.lower() == "strict":
            if not self.validate_strict_ontology(merged):
                print("Strict ontology validation failed. Please revise the suggestions.")
                return merged
        if require_confirmation:
            print("\nPlease Review the new suggested Ontology:")
            self._print_ontology(merged)
            final = self.review_and_edit_suggestions(merged)
        else:
            print("\nAutomatically accepting suggested ontology:")
            self._print_ontology(merged)
            final = merged
        return final

    def suggest_enhancements(self, text: str, mode: str = "expressive") -> ExpressiveOntology:
        chain = self._create_ontology_chain(mode)
        return chain.invoke({
            "text": text,
            "existing_nodes": ", ".join(self.existing_ontology["nodes"]),
            "existing_rels": ", ".join(self.existing_ontology["relationships"])
        })

    def validate_strict_ontology(self, ontology: ExpressiveOntology) -> bool:
        """
        Validate the strict ontology by ensuring that for relationships of type SUBCLASSOF,
        each child has at most one parent and no cycles exist.
        Assumes that relationship_description for SUBCLASSOF is in the format "ChildEntity -> ParentEntity".
        """
        subclass_rels = [rel for rel in ontology.relationships if rel.relationship_type.upper() == "SUBCLASSOF"]
        child_to_parents = {}
        # Use regex to parse "ChildEntity -> ParentEntity" with extra spaces tolerated
        pattern = re.compile(r"^\s*(.+?)\s*->\s*(.+?)\s*$")
        for rel in subclass_rels:
            match = pattern.match(rel.relationship_description)
            if match:
                child = match.group(1)
                parent = match.group(2)
            else:
                print(f"Warning: Unable to parse relationship description: '{rel.relationship_description}'. Skipping validation for this entry.")
                continue
            child_to_parents.setdefault(child, []).append(parent)
        for child, parents in child_to_parents.items():
            if len(parents) > 1:
                print(f"Validation error: Node '{child}' has multiple parents: {parents}")
                return False
        # Detect cycles using DFS
        graph_map = {}
        for child, parents in child_to_parents.items():
            for parent in parents:
                graph_map.setdefault(parent, []).append(child)
        visited, rec_stack = set(), set()
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph_map.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False
        for node in graph_map:
            if node not in visited and dfs(node):
                print("Validation error: Cycle detected in SUBCLASSOF relationships.")
                return False
        return True

    def review_and_edit_suggestions(self, suggestions: ExpressiveOntology) -> ExpressiveOntology:
        edited_nodes = []
        edited_rels = []
        print("\nReviewing nodes:")
        for node in suggestions.nodes:
            # Use interactive logic if desired (for example, with inquirer)
            edited_nodes.append(Node(node_type=node.node_type, node_description=node.node_description))
        print("\nReviewing relationships:")
        for rel in suggestions.relationships:
            edited_rels.append(RelationshipExpressive(relationship_type=rel.relationship_type, relationship_description=rel.relationship_description))
        return ExpressiveOntology(nodes=edited_nodes, relationships=edited_rels)

    def _print_ontology(self, ontology: ExpressiveOntology):
        print("\nNodes:")
        for node in ontology.nodes:
            print(f"  {node.node_type}: {node.node_description}")
        print("\nRelationships:")
        for rel in ontology.relationships:
            print(f"  {rel.relationship_type}: {rel.relationship_description}")

    def _get_existing_ontology(self) -> Dict:
        existing_nodes = []
        existing_rels = []
        with self.driver.session() as session:
            node_result = session.run("CALL db.labels()")
            existing_nodes = [record["label"] for record in node_result]
            rel_result = session.run("CALL db.relationshipTypes()")
            existing_rels = [record["relationshipType"] for record in rel_result]
        return {"nodes": existing_nodes, "relationships": existing_rels}


# =============================================================================
# GraphGenerator and Graph Classes 
# =============================================================================
class GraphGenerator:
    def __init__(self, node_labels: List[str] = None, relationship_labels: List[str] = None, prompt=None, node_properties=None):
        self.node_labels = node_labels
        self.relationship_labels = relationship_labels
        self.prompt = prompt
        self.node_properties = node_properties
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
        self.llm_transformer = LLMGraphTransformer(
            llm=self.llm,
            allowed_nodes=self.node_labels,
            allowed_relationships=self.relationship_labels,
            node_properties=self.node_properties
        )

    def generate_graph(self, documents: List[Document]) -> Optional[List[Document]]:
        try:
            graph_documents = self.llm_transformer.convert_to_graph_documents(documents)
            return graph_documents
        except Exception as e:
            print(f"Failed to generate graph: {str(e)}")
            return None


class Graph:
    def __init__(self, uri: str = os.getenv("NEO4J_URI"), username: str = "neo4j", password: str = os.getenv("NEO4J_PASSWORD")):
        self.graph = Neo4jGraph(url=uri, username=username, password=password)

    def add_graph(self, graph_documents: List[Document]) -> bool:
        try:
            self.graph.add_graph_documents(graph_documents)
            return True
        except Exception as e:
            print(f"Failed to add graph to Neo4j: {str(e)}")
            return False
