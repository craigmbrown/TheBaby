from langchain_core.prompts import ChatPromptTemplate

generation_prompt = ChatPromptTemplate.from_template(
"""

You are a top-tier algorithm designed for extracting information in structured formats to build a knowledge graph by analyzing technical AI content.\nTry to capture as much information from the text as possible without sacrificing accuracy. Do not add any information that is not explicitly mentioned in the text.

# Knowledge Graph Construction Protocol

## Ontology Definition
**Nodes MUST be one of these types:**

- AI_Orchestrator: Central control system (e.g., "Ada") that manages workflows and agents
- AI_Agent: Specialized sub-component (e.g., "SQL Generator", "File Manager")
- Model: AI/ML architectures (e.g., "O1 Preview", "Claude 3.5 Sonnet")
- Task: Atomic actions (e.g., "Create CSV", "Generate Bar Chart")
- Workflow: Multi-step processes (e.g., "Data Analysis Pipeline")
- Artifact: Output files (e.g., "user_analytics.csv", "Python_loops.py")
- Tool: Software utilities (e.g., "Real-Time API", "LM-CLI")
- User: Human operator interacting with system
- Dataset: Structured data (e.g., "Product Tables", "HN Comments")
- Knowledge: Derived insights (e.g., "SEO Pattern Analysis")
- Interaction: User-system exchanges (e.g., "Voice Command")
- System: Infrastructure components (e.g., "Database Server")

## Relationship Types (EXACTLY THESE LABELS)

- EXECUTES: Orchestrator → Workflow/Agent (Ada executes Report Generation)
- COMPRISES: Workflow → Tasks (Analysis Pipeline comprises CSV Export)
- GENERATES: Task/Agent → Artifact (Python Agent generates Charts)
- UTILIZES: Task/Agent → Model/Tool (Chapter Generation uses O1 Model)
- ANALYZES: Agent → Dataset (Sentiment Agent analyzes HN Comments)
- TRIGGERS: Event → Workflow (UserCommand triggers Cleanup)
- OPTIMIZES: Model → Workflow (O1 optimizes Coding Assistant)
- CONTAINS: Dataset → Knowledge (UserData contains Usage Patterns)
- VALIDATES: Tool → Artifact (Linter validates PythonCode)
- FEEDS: Artifact → Model (TrainingData feeds GPT-5)
- CONFIGURES: User → Orchestrator (Admin configures Ada)
- RECOMMENDS: Model → Task (Claude recommends QueryOptimization)


You must extract all of the possible nodes and relationships from the given text. Ensure that the extracted nodes and relationships are consistent with the given ontology.
Tip: Make sure to answer in the correct format and do not include any explanations. Use the given format to extract information from the following input: {input}

"""
)
# Updated Node Labels (More Focused)
node_labels = [
    "AI_Orchestrator",  # Top-level system (e.g., Ada)
    "AI_Agent",         # Specialized sub-agents (e.g., SQL Agent)
    "Model",            # AI models (O1, Claude 3.5, GPT-4)
    "Task",             # Atomic actions (FileCreate, QueryExecute)
    "Workflow",         # Task sequences (DataAnalysis, ReportGen)
    "Artifact",         # Outputs (CSV, PythonScript, Markdown)
    "Tool",             # Software tools (RealTimeAPI, LM-CLI)
    "User",             # Human actor
    "Dataset",          # Structured data (SQLTables, CSVs)
    "Knowledge",        # Insights/Research (PromptPatterns, Benchmarks)
    "Interaction",      # User-AI exchanges
    "System"            # Technical components (APIs, Databases)
]

# More Precise Relationships
relationship_labels = [
    "EXECUTES",        # Orchestrator -> Workflow/Agent
    "COMPRISES",       # Workflow -> Tasks
    "GENERATES",       # Task/Agent -> Artifact
    "UTILIZES",       # Task/Agent -> Model/Tool
    "ANALYZES",       # Agent -> Dataset
    "TRIGGERS",       # Event -> Workflow
    "OPTIMIZES",      # Model -> Workflow
    "CONTAINS",       # Dataset -> Knowledge
    "VALIDATES",      # Tool -> Artifact
    "FEEDS",         # Artifact -> Model
    "CONFIGURES",    # User -> Orchestrator
    "RECOMMENDS"     # Model -> Task
]

# Enriched Properties
node_properties = ["name", "description"]
