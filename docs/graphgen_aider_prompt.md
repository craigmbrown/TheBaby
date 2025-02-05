# Specification Prompt Template

## High-Level Objective
Build a knowledge graph generation system that:
1. Processes text documents into structured knowledge graphs
2. Integrates with Neo4j database
3. Supports multiple ontology generation modes
4. Provides both CLI and interactive interfaces
5. Generates interactive visualizations

## Mid-Level Objectives
1. Implement text loading and preprocessing module
2. Create ontology management system with merging capabilities
3. Develop LLM-powered graph transformation pipeline
4. Build Neo4j integration with schema validation
5. Implement multi-mode operation (CLI + interactive)
6. Add visualization generation capabilities
7. Include ontology versioning/export functionality

## Implementation Notes
### Technical Details
- Use LangChain's graph transformers for base functionality
- Implement ontology merging with GPT-4-turbo
- Follow Neo4j's best practices for batch insertion
- Use Plotly/D3 for interactive visualizations

### Dependencies
- Python 3.10+
- Packages: langchain-openai, neo4j, python-dotenv, inquirer, pandas

### Coding Standards
- PEP8 compliance
- Type hinting for all functions
- Google-style docstrings
- Modular architecture with separation of concerns
- Comprehensive error handling

### Configuration
- Environment variables for credentials
- JSON-based ontology configuration
- YAML for preset ontologies

## Context
### Beginning Context
Existing Files:
- load_data.py (partial)
- generate_graph.py (partial)
- memory_preprocessing.py (partial)

### Ending Context  
Required Files:
1. load_data.py
2. generate_graph.py 
3. graph_visualizer.py
4. ontology_manager.py
5. cli_interface.py
6. interactive_mode.py
7. config/
   - preset_ontologies/
     - ai_baseline.yaml
     - finance.yaml
8. tests/
   - test_ontology_merge.py
   - test_graph_generation.py

## Low-Level Tasks

1. Implement text processing module  
aider  
Prompt: "Create TextProcessor class with error handling and text normalization"  
File: CREATE load_data.py  
Function: CREATE TextProcessor.load_text()  
Details:  
- Use LangChain TextLoader  
- Add UTF-8 encoding handling  
- Implement text cleaning (strip extra whitespace, normalize unicode)  
- Add progress logging

2. Build ontology enhancement engine  
aider  
Prompt: "Implement OntologyEnhancer with schema-aware merging"  
File: UPDATE generate_graph.py  
Function: CREATE OntologyEnhancer.merge_ontologies()  
Details:  
- Add similarity scoring for node/relationship types  
- Implement conflict resolution strategy  
- Add version tracking for merged ontologies  
- Include schema validation against Neo4j

3. Create graph generation pipeline  
aider  
Prompt: "Build GraphGenerator with LLM integration"  
File: UPDATE generate_graph.py  
Function: CREATE GraphGenerator.generate_graph()  
Details:  
- Implement batch processing for large texts  
- Add rate limiting for OpenAI API  
- Include fallback to local LLM option  
- Add property extraction from text

4. Implement Neo4j connector  
aider  
Prompt: "Create Graph class with transaction management"  
File: CREATE neo4j_connector.py  
Function: CREATE Graph.add_graph_documents()  
Details:  
- Use UNWIND for batch insertion  
- Implement retry logic for failed transactions  
- Add index management  
- Include constraint validation

5. Build CLI interface  
aider  
Prompt: "Implement multi-command CLI with argparse"  
File: CREATE cli_interface.py  
Function: CREATE main()  
Details:  
- Add --batch-size parameter  
- Implement --dry-run mode  
- Include progress bars  
- Add colorized output

6. Add visualization system  
aider  
Prompt: "Create interactive D3-based visualizer"  
File: CREATE graph_visualizer.py  
Function: CREATE visualize_network()  
Details:  
- Implement force-directed layout  
- Add zoom/pan controls  
- Include tooltip metadata  
- Add export to PNG/SVG

7. Implement testing suite  
aider  
Prompt: "Create integration tests for core functionality"  
File: CREATE tests/test_core.py  
Function: CREATE test_ontology_merge()  
Details:  
- Use pytest fixtures  
- Add mock Neo4j instance  
- Include LLM response caching  
- Add performance benchmarks
