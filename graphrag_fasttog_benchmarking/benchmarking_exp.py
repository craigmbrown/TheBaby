import os
import sys
import json
import subprocess
import numpy as np
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, TypedDict
from typing_extensions import Annotated, Union
from langchain.schema import Document
from test_queries import query_entity_mappings

# Load environment variables
load_dotenv()

# Initialize LLM and graph connection
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
graph = Neo4jGraph(
    enhanced_schema=True,
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD")
)
graph.refresh_schema()

class OverallState(TypedDict):
    question: str
    next_action: str
    cypher_statement: str
    cypher_errors: List[str]
    database_records: List[dict]
    similarity_results: Union[List[dict], List[Document]]
    steps: Annotated[List[str], list]

def generate_cypher(state: OverallState) -> OverallState:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Convert the following question to a Cypher query. Return only the query."),
        ("human", "Question: {question}\nCypher:")
    ])
    chain = prompt | llm | StrOutputParser()
    state["cypher_statement"] = chain.invoke({"question": state["question"]})
    state["steps"] = state.get("steps", []) + ["generate_cypher"]
    return state

def validate_cypher(state: OverallState) -> OverallState:
    errors = []
    try:
        graph.query(f"EXPLAIN {state['cypher_statement']}")
    except Exception as e:
        errors.append(str(e))
    state["cypher_errors"] = errors
    state["steps"] = state.get("steps", []) + ["validate_cypher"]
    state["next_action"] = "correct_cypher" if errors else "execute_cypher"
    return state

def execute_cypher(state: OverallState) -> OverallState:
    records = graph.query(state["cypher_statement"])
    state["database_records"] = records if records else []
    state["steps"] = state.get("steps", []) + ["execute_cypher"]
    return state

def execute_similarity_search(state: OverallState) -> OverallState:
    store = Neo4jVector.from_existing_index(
        OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY")),
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name="vector"
    )
    state["similarity_results"] = store.similarity_search_with_score(state["question"], k=3)
    state["steps"] = state.get("steps", []) + ["similarity_search"]
    return state

def generate_final_answer(state: OverallState) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "Given the following Neo4j query results:\n{database_records}\n"
                    "And similarity search results:\n{similarity_results}\n"
                    "Answer the question: {question}")
    ])
    chain = prompt | llm | StrOutputParser()
    state["steps"] = state.get("steps", []) + ["generate_final_answer"]
    return chain.invoke({
        "database_records": state.get("database_records"),
        "similarity_results": state.get("similarity_results"),
        "question": state["question"]
    })

def main(user_query):
    state: OverallState = {
        "question": user_query,
        "next_action": "",
        "cypher_statement": "",
        "cypher_errors": [],
        "database_records": [],
        "similarity_results": [],
        "steps": []
    }
    state = generate_cypher(state)
    state = validate_cypher(state)
    if state["next_action"] == "correct_cypher":
        state = correct_cypher(state)
    state = execute_cypher(state)
    state = execute_similarity_search(state)
    return generate_final_answer(state)

graphrag_results = []
for question in query_entity_mappings.keys():
    try:
        graphrag_answer = main(question)
    except Exception as e:
        print('cypher generation exception')
        graphrag_answer = "could not generate an answer"
    finally:
        graphrag_results.append({"question": question, "graph_answer": graphrag_answer})

graphrag_results_json = "graphrag_results.json"
with open(graphrag_results_json, "w") as f:
    json.dump(graphrag_results, f, indent=4)

# FastToG Execution
fasttog_results = []
for query, metadata in query_entity_mappings.items():
    start_entity = metadata["start_entity"]
    if start_entity is None:
        continue
    command = [
        "python", "FastToG/fasttog.py",
        "--query", query,
        "--entity", start_entity,
        "--base_path", "FastToG",
        "--llm_api", "https://api.openai.com/v1/models",
        "--llm_api_key", os.getenv("OPENAI_API_KEY"),
        "--kg_api", os.getenv("NEO4J_URI"),
        "--kg_user", "neo4j",
        "--kg_pw", os.getenv("NEO4J_PASSWORD"),
        "--kg_graph_file_name", "visulize",
        "--community_max_size", "4"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        fasttog_results.append({"question": query, "fasttog_answer": result.stdout.strip() if result.returncode == 0 else "Error"})
    except subprocess.TimeoutExpired:
        fasttog_results.append({"question": query, "fasttog_answer": "Timeout"})
    except Exception as e:
        fasttog_results.append({"question": query, "fasttog_answer": "Execution Failed"})
with open("fasttog_results.json", "w") as f:
    json.dump(fasttog_results, f, indent=4)
print("Benchmarking completed. Results saved.")
