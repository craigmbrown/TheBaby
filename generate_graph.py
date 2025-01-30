import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from load_data import TextProcessor
from dotenv import load_dotenv
load_dotenv()
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.documents import Document
from typing import Optional, List, Dict
from neo4j import GraphDatabase
import inquirer



class Node(BaseModel):
    node_type: str = Field(...,description="the label indicating the type of the node")
    node_description : str = Field(...,description="The description of what this node entity signifies")

class Relationship(BaseModel):
    relationship_type: str = Field(...,description="the label indicating the type of the relationship")
    relationship_description : str = Field(...,description="The description of what this relationship signifies")


class Ontology(BaseModel):
    nodes: List[Node] = Field(...,description="the list of suggested node labels")
    relationships: List[Relationship] = Field(...,description="the list of suggested relationship labels")





class OntologyEnhancer:

    def __init__(self, neo4j_driver: GraphDatabase.driver, llm: ChatOpenAI):
        self.driver = neo4j_driver
        self.llm = llm
        self.existing_ontology = self._get_existing_ontology()
        self.merge_chain = self._create_merge_chain()


    def _create_merge_chain(self):
        """Create chain for merging multiple ontologies"""
        merge_prompt = ChatPromptTemplate.from_messages([
                  ("system", """You are an ontology integration expert. Merge multiple ontology suggestions into a single unified ontology by:
      1. Combining similar node/relationship types
      2. Merging descriptions while preserving important details
      3. Removing duplicates
      4. Maintaining naming conventions

      Guidelines:
      - Prefer more specific descriptions that incorporate details from multiple sources
      - Use PascalCase for nodes, UPPER_SNAKE_CASE for relationships
      - Preserve all unique elements from different sources

      Return only the merged ontology."""),
                  ("human", "Ontologies to merge:\n{ontologies}")
              ])
        
        return merge_prompt | self.llm.with_structured_output(Ontology)

    def _serialize_ontology(self, ontology: Ontology) -> str:
        """Convert ontology to text format for LLM processing"""
        nodes = "\n".join([f"Node: {n.node_type} - {n.node_description}" 
                          for n in ontology.nodes])
        rels = "\n".join([f"Relationship: {r.relationship_type} - {r.relationship_description}"
                         for r in ontology.relationships])
        return f"Nodes:\n{nodes}\nRelationships:\n{rels}"

    def merge_ontologies(self, ontologies: List[Ontology]) -> Ontology:
        """Merge multiple ontologies into one using LLM"""
        if len(ontologies) == 0:
            return Ontology(nodes=[], relationships=[])
            
        if len(ontologies) == 1:
            return ontologies[0]

        serialized = "\n\n".join([self._serialize_ontology(o) for o in ontologies])
        return self.merge_chain.invoke({"ontologies": serialized})

    def process_multiple_texts(self, texts: List[str], require_confirmation: bool = True) -> Ontology:
        """Full pipeline for multiple text snippets
        
        Args:
            texts: List of text snippets to process
            require_confirmation: If True, prompts for user review. If False, accepts suggestions automatically
        """
        # Generate individual ontologies
        suggestions = [self.suggest_enhancements(text) for text in texts]
        
        # Merge suggestions
        merged = self.merge_ontologies(suggestions)
        
        if require_confirmation:
            # User review
            print("\nPlease Review the new suggested Ontology:")
            self._print_ontology(merged)
            final = self.review_and_edit_suggestions(merged)
        else:
            # Auto-accept all suggestions
            print("\nAutomatically accepting suggested ontology:")
            self._print_ontology(merged)
            final = merged
            
        return final
    def _get_existing_ontology(self) -> Dict:
        """Retrieve existing ontology from Neo4j database"""
        existing_nodes = []
        existing_rels = []
        
        with self.driver.session() as session:
            # Get existing node labels
            node_result = session.run("CALL db.labels()")
            existing_nodes = [record["label"] for record in node_result]
            
            # Get existing relationship types
            rel_result = session.run("CALL db.relationshipTypes()")
            existing_rels = [record["relationshipType"] for record in rel_result]
        
        return {
            "nodes": existing_nodes,
            "relationships": existing_rels
        }

    def _create_ontology_chain(self):
        """Create the ontology suggestion chain"""
        system_prompt = """You are an expert ontology engineer. Analyze the provided text and existing database schema to:
1. Identify new node types needed that don't exist in the current schema
2. Identify new relationship types needed between entities
3. Suggest clear descriptions for each new element

Existing Node Types: {existing_nodes}
Existing Relationship Types: {existing_rels}

Guidelines:
- Only suggest elements not already in the existing schema
- The nodes and relationships that you come up with should be high level and shouldn't be too detailed to the text. This should ensure that future texts can also be represented by the same ontology. If the nodes and relationships are too grantual future input texts may nor align with such a detailed ontology.
- Use PascalCase for node labels
- Use UPPER_SNAKE_CASE for relationship types
- Provide clear, specific descriptions"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Text to analyze:\n{text}")
        ])

        return prompt | self.llm.with_structured_output(Ontology)

    def suggest_enhancements(self, text: str) -> Ontology:
        """Generate ontology suggestions considering existing schema"""
        chain = self._create_ontology_chain()
        return chain.invoke({
            "text": text,
            "existing_nodes": ", ".join(self.existing_ontology["nodes"]),
            "existing_rels": ", ".join(self.existing_ontology["relationships"])
        })    

    def review_and_edit_suggestions(self, suggestions: Ontology) -> Ontology:
        """Interactive user review and editing of suggestions"""
        edited_nodes = []
        edited_rels = []

        # Review nodes
        print("\nReviewing nodes:")
        for node in suggestions.nodes:
            questions = [
                inquirer.Text('type', message=f"Edit node type : {node.node_type}", default=node.node_type),
                inquirer.Text('desc', message=f"Edit description", default=node.node_description)
            ]
            answers = inquirer.prompt(questions)
            edited_nodes.append(Node(
                node_type=answers['type'],
                node_description=answers['desc']
            ))

        # Review relationships
        print("\nReviewing relationships:")
        for rel in suggestions.relationships:
            questions = [
                inquirer.Text('type', message=f"Edit relationship type (current: {rel.relationship_type})", 
                            default=rel.relationship_type),
                inquirer.Text('desc', message=f"Edit description", 
                            default=rel.relationship_description)
            ]
            answers = inquirer.prompt(questions)
            edited_rels.append(Relationship(
                relationship_type=answers['type'],
                relationship_description=answers['desc']
            ))

        return Ontology(nodes=edited_nodes, relationships=edited_rels)

    def _print_ontology(self, ontology: Ontology):
        """Helper method to display ontology"""
        print("\nNodes:")
        for node in ontology.nodes:
            print(f"  {node.node_type}: {node.node_description}")
        
        print("\nRelationships:")
        for rel in ontology.relationships:
            print(f"  {rel.relationship_type}: {rel.relationship_description}")
 
        print("\nRelationships:")
        for rel in ontology.relationships:
            print(f"  {rel.relationship_type}: {rel.relationship_description}")


class GraphGenerator:
    def __init__(self, node_labels: List[str]=None, relationship_labels: List[str]=None,prompt=None,node_properties=None):
        self.node_labels = node_labels
        self.relationship_labels = relationship_labels
        self.prompt = prompt
        self.node_properties = node_properties
        self.llm = ChatOpenAI(
            temperature=0, model_name="gpt-4o", api_key=os.getenv("OPENAI_API_KEY")
        )
        self.llm_transformer = LLMGraphTransformer(
            llm=self.llm,
            allowed_nodes=self.node_labels,
            allowed_relationships=self.relationship_labels,
            # prompt=self.prompt,
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




