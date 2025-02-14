# Benchmarking GraphRAG vs FastToG

This document provides a guide on how to set up, modify, and run the benchmarking script to compare **GraphRAG** and **FastToG** for querying a Knowledge Graph (KG).

## 1. Overview
The benchmarking script runs a set of predefined queries against both GraphRAG and FastToG and saves the results for comparison. It utilizes **Neo4j** as the KG backend and executes both retrieval approaches programmatically.

## 2. Folder Structure
The expected structure for running the benchmarking:
```
/benchmarking
|-- run_benchmarking.py  # The main script
|-- test_queries.py      # The test set
|-- FastToG/            # Cloned FastToG repository
|-- graphrag_results.json  # Output from GraphRAG
|-- fasttog_results.json   # Output from FastToG
```

## 3. Setting Up
### **Step 1: Clone FastToG**
Ensure that **FastToG** is cloned into the same directory as `run_benchmarking.py`:
```bash
git clone https://github.com/yourrepo/FastToG.git
```

### **Step 2: Install Dependencies**
Ensure required dependencies are installed:
```bash
pip install -r requirements.txt  # Install dependencies
```

### **Step 3: Configure Environment Variables**
Create a `.env` file in the same directory and specify your credentials:
```
OPENAI_API_KEY=your_openai_key
NEO4J_URI=your_neo4j_uri
NEO4J_USER=your_neo4j_username
NEO4J_PASSWORD=your_neo4j_password
```

## 4. Modifying the Test Set
The queries and entities used for benchmarking are stored in `test_queries.py`. Modify this file to update the test set:
```python
query_entity_mappings = {
    "What tools does Ada use?": {
        "start_entity": "Agent (Ada)",
        "related_labels": ["Tool"]
    },
    "Which resources does Ada configure?": {
        "start_entity": "Agent (Ada)",
        "related_labels": ["Resource"]
    }
    # Add more queries as needed...
}
```

## 5. Running the Benchmarking Script
To execute the benchmarking, run:
```bash
python run_benchmarking.py
```
This will:
- Run each query on **GraphRAG** and **FastToG**
- Save the results in `graphrag_results.json` and `fasttog_results.json`
- Print status updates and execution times

## 6. Understanding the Script
### **GraphRAG Execution**
- The script initializes a **Neo4j graph connection** and an **OpenAI LLM**.
- It processes queries by **generating a Cypher query**, validating it, and executing it.
- Results are stored in `graphrag_results.json`.

### **FastToG Execution**
- Runs FastToG via **subprocess**, passing parameters dynamically.
- Retrieves results and stores them in `fasttog_results.json`.

## 7. Results and Evaluation
### **Where to Find the Results?**
- **GraphRAG Results:** `graphrag_results.json`
- **FastToG Results:** `fasttog_results.json`

### **Performance Metrics Computed**
The script evaluates the following metrics for GraphRAG:
- **Precision**: Percentage of correctly retrieved answers
- **Recall**: Fraction of expected answers retrieved
- **Mean Reciprocal Rank (MRR)**: Rank quality of correct answers

### **Example Output Format**
```json
[
    {"question": "What tools does Ada use?", "graph_answer": "Ada uses VS Code and Jupyter"},
    {"question": "What tools does Ada use?", "fasttog_answer": "Entity not found."}
]
```

## 8. Troubleshooting
- **FastToG Fails to Find Entities**: Ensure that your KG contains well-connected entities.
- **GraphRAG Query Errors**: The script attempts query correction. If errors persist, check the generated Cypher query.
- **Slow Execution**: Reduce the number of queries in `test_queries.py`.

## 9. Conclusion
This benchmarking script automates the evaluation of GraphRAG and FastToG for KG-based retrieval. Modify `test_queries.py` to adapt it to your dataset and compare the results across different query types.

