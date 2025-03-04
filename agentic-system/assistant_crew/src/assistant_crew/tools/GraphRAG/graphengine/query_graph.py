import sys, os, asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, TypedDict
from typing_extensions import Annotated, Union
from langchain.schema import Document
# Load environment variables
load_dotenv()

# Initialize LLM and graph connection (with enhanced schema for better details)
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
graph = Neo4jGraph(
    enhanced_schema=True,
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD")
)
graph.refresh_schema()

# Define the overall state with similarity_results included.
class OverallState(TypedDict):
    question: str
    next_action: str
    cypher_statement: str
    cypher_errors: List[str]
    database_records: List[dict]
    similarity_results: Union[List[dict],List[Document]]
    steps: Annotated[List[str], list]

# STEP 1: Generate a Cypher query from the user question.
def generate_cypher(state: OverallState) -> OverallState:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Convert the following question to a Cypher query. Return only the query."),
        ("human", "Question: {question}\nCypher:")
    ])
    chain = prompt | llm | StrOutputParser()
    state["cypher_statement"] = chain.invoke({"question": state["question"]})
    state["steps"] = state.get("steps", []) + ["generate_cypher"]
    return state

# STEP 2: Validate the generated Cypher query.
def validate_cypher(state: OverallState) -> OverallState:
    errors = []
    try:
        # Using EXPLAIN to check syntax (adjust as needed)
        graph.query(f"EXPLAIN {state['cypher_statement']}")
    except Exception as e:
        errors.append(str(e))
    state["cypher_errors"] = errors
    state["steps"] = state.get("steps", []) + ["validate_cypher"]
    # If errors exist, mark for correction
    state["next_action"] = "correct_cypher" if errors else "execute_cypher"
    return state

# STEP 3: Correct the Cypher query if errors were found.
def correct_cypher(state: OverallState) -> OverallState:
    if state["next_action"] != "correct_cypher":
        return state
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Cypher expert. Correct the errors in the following Cypher query."),
        ("human", "Errors: {cypher_errors}\nOriginal Cypher: {cypher_statement}\nCorrected Cypher: IMPORTANT: return just the cypher query diectly and only")
    ])
    chain = prompt | llm | StrOutputParser()
    corrected = chain.invoke({
        "cypher_errors": state["cypher_errors"],
        "cypher_statement": state["cypher_statement"]
    })
    state["cypher_statement"] = corrected
    state["steps"] = state.get("steps", []) + ["correct_cypher"]
    state["next_action"] = "execute_cypher"
    return state

# STEP 4: Execute the Cypher query against Neo4j.
def execute_cypher(state: OverallState) -> OverallState:
    records = graph.query(state["cypher_statement"])
    state["database_records"] = records if records else []
    state["steps"] = state.get("steps", []) + ["execute_cypher"]
    return state

# STEP 5: Run similarity search using an existing Neo4j vector index.
def execute_similarity_search(state: OverallState) -> OverallState:
    store = Neo4jVector.from_existing_index(
        OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY")),
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name="vector" 
    )
    # Run similarity search using the question (or you could use the cypher query if preferred)
    state["similarity_results"] = store.similarity_search_with_score(state["question"],k=3)
    state["steps"] = state.get("steps", []) + ["similarity_search"]
    return state

# STEP 6: Generate the final answer using both database and similarity search results.
async def generate_final_answer(state: OverallState) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "Given the following Neo4j query results:\n{database_records}\n"
                    "And similarity search results:\n{similarity_results}\n"
                    "Answer the question: {question}")
    ])
    chain = prompt | llm | StrOutputParser()
    state["steps"] = state.get("steps", []) + ["generate_final_answer"]
    return await chain.ainvoke({
        "database_records": state.get("database_records"),
        "similarity_results": state.get("similarity_results"),
        "question": state["question"]
    })

async def main():
    if len(sys.argv) < 2:
        print("Usage: python query_graph.py \"<YOUR QUERY HERE>\"")
        sys.exit(1)
    user_query = " ".join(sys.argv[1:])
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
    final_answer =await  generate_final_answer(state)
    print("Final Answer:\n", final_answer)

if __name__ == "__main__":
    asyncio.run(main())


def query_graph(question: str) -> str:
    state: OverallState = {
        "question": question,
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
    return  generate_final_answer(state)


