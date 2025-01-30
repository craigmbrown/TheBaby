
import sys
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
# Load environment variables
load_dotenv()
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_neo4j import GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain.chains import RetrievalQAWithSourcesChain

from langchain_core.prompts.prompt import PromptTemplate

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}
Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
Examples: Here are a few examples of generated Cypher statements for particular questions:
# How many people played in Top Gun?
MATCH (m:Movie {{name:"Top Gun"}})<-[:ACTED_IN]-()
RETURN count(*) AS numberOfActors

IMPORTANT:
always have a like in search instead of exact
example : what do we know about o1 models?
instead of : 
MATCH (m:Model {{name: "o1"}})
RETURN m
use:
MATCH (m:Model {{name: "%o1%"}})
RETURN m

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)
def query_w_chain(query):
    # Create an instance of the LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0,api_key=os.getenv("OPENAI_API_KEY"))

    
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username="neo4j",
        password=os.getenv("NEO4J_PASSWORD")
    )
    store = Neo4jVector.from_existing_index(
    OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY")),
    url=os.getenv("NEO4J_URI"),
    username="neo4j",
    password=os.getenv("NEO4J_PASSWORD"),
    index_name="vector"
    )
    ret = store.as_retriever()
    # Refresh the schema for safety
    graph.refresh_schema()

    # Create the chain
    chain = GraphCypherQAChain.from_llm(
        graph=graph,
        llm=llm,
        cypher_prompt=CYPHER_GENERATION_PROMPT,
        verbose=True,
        allow_dangerous_requests=True,

    )
    vector_chain = RetrievalQAWithSourcesChain.from_chain_type(
    ChatOpenAI(temperature=0,api_key=os.getenv("OPENAI_API_KEY")), chain_type="stuff", retriever=ret)
    # Pass the query to the chain
    graph_res = chain.invoke({"query": query})
    vector_res = vector_chain.invoke({"question":query},return_only_outputs=True)

    prompt = ChatPromptTemplate.from_template("""
    You are a helpful QA assistant. The user asked this question : {question}
    use the context below which is composed of context retrieved from a vector store and a knowledge graph to generate 
a final answer for the user's query
vector search result : {vec_res}
Knoweldge graph result : {kg_res}
""")



    final_chain = prompt | ChatOpenAI(temperature=0,api_key=os.getenv("OPENAI_API_KEY"))

    return final_chain.invoke(    {
        "vec_res": vector_res["answer"] ,
        "kg_res": graph_res
    }).content
    

if __name__ == "__main__":
    # Extract the query from command line arguments
    if len(sys.argv) < 2:
        print("Usage: python query_graph.py \"<YOUR QUERY HERE>\"")
        sys.exit(1)

    # Combine all command line arguments into a single query string
    user_query = " ".join(sys.argv[1:])

    # Get the result
    result = query_w_chain(user_query)

    # Print the result
    print("Result:\n", result)

