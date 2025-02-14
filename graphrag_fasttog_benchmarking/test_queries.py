query_entity_mappings = {
    # Simple single-hop queries
    "What tools does Ada use?": {
        "start_entity": "Agent (Ada)",
        "related_labels": ["Tool"]
    },
    
    "Which resources does Ada configure?": {
        "start_entity": "Agent (Ada)",
        "related_labels": ["Resource"]
    },
    
    "What is the name of Mickey Drexler's father?": {
        "start_entity": "Agent (Mickey Drexler)",
        "related_labels": ["Agent (Mickey Drexler's Father)"]
    },
    
    "List all AI Assistants in the system.": {
        "start_entity": None,  # General query
        "related_labels": ["Ai_assistant"]
    },
    
    # Multi-hop relationship queries
    "Which retail companies has Mickey Drexler been involved with?": {
        "start_entity": "Agent (Mickey Drexler)",
        "related_labels": ["Resource"]  # Companies like The Gap, Ann Taylor, etc.
    },
    
    "What is the connection between Steve Jobs and Mickey Drexler?": {
        "start_entity": "Agent (Steve Jobs)",
        "related_labels": ["Agent (Mickey Drexler)", "Resource (Apple Store)"]
    },
    
    "How is the Apple Store connected to both Steve Jobs and Mickey Drexler?": {
        "start_entity": "Resource (Apple Store)",
        "related_labels": ["Agent (Steve Jobs)", "Agent (Mickey Drexler)"]
    },
    
    "What tools and resources are used by both Ada and Indy Dev Dan?": {
        "start_entity": "Agent (Ada)",
        "related_labels": ["Agent (Indy Dev Dan)", "Tool", "Resource"]
    },
    
    # Community-based queries
    "What are all the relationships between AI Agents and the tools they use?": {
        "start_entity": "Ai_agent",
        "related_labels": ["Tool"]
    },
    
    "How do different AI assistants utilize structured outputs and reasoning models?": {
        "start_entity": "Ai_assistant",
        "related_labels": ["Structuredoutput", "Reasoningmodel"]
    },
    
    "What is the complete ecosystem around Generative AI, including its agents and assistants?": {
        "start_entity": "Generativeai",
        "related_labels": ["Ai_agent", "Ai_assistant"]
    },
    
    "Map out the full retail network connected to Mickey Drexler, including all companies and relationships.": {
        "start_entity": "Agent (Mickey Drexler)",
        "related_labels": ["Resource"]  # Various retail companies
    },
    
    # Complex reasoning queries
    "What are the common patterns in how AI Agents and AI Assistants interact with prompts and models?": {
        "start_entity": "Ai_agent",
        "related_labels": ["Ai_assistant", "Prompt", "Model"]
    },
    
    "Compare the technology stack used by Ada versus other AI assistants in the system.": {
        "start_entity": "Agent (Ada)",
        "related_labels": ["Ai_assistant", "Tool", "Resource"]
    },
    
    "What is the relationship between the Orchestration Layer and AI Agents, including all downstream connections?": {
        "start_entity": "Orchestrationlayer",
        "related_labels": ["Ai_agent"]
    },
    
    "Trace the complete path of how Generative AI connects to Engineers through various components.": {
        "start_entity": "Generativeai",
        "related_labels": ["Engineer"]
    },
    
    # Aggregation queries
    "How many different types of tools are used across all agents?": {
        "start_entity": "Agent",
        "related_labels": ["Tool"]
    },
    
    "What is the most commonly used resource type in the system?": {
        "start_entity": None,  # System-wide query
        "related_labels": ["Resource"]
    },
    
    "Which agent has the most diverse set of connections?": {
        "start_entity": "Agent",
        "related_labels": ["Tool", "Resource"]
    },
    
    "What are all the different ways prompts are used throughout the system?": {
        "start_entity": "Prompt",
        "related_labels": ["Ai_agent", "Largelanguagemodel"]
    },
    
    # Cross-domain queries
    "How do retail business practices (from Mickey Drexler) connect with technology (through Apple Store)?": {
        "start_entity": "Agent (Mickey Drexler)",
        "related_labels": ["Resource (Apple Store)", "Tool"]
    },
    
    "What patterns emerge when comparing human agents versus AI agents in terms of resource usage?": {
        "start_entity": "Agent",
        "related_labels": ["Ai_agent", "Resource"]
    },
    
    "Map the complete knowledge flow from Engineers through to AI Assistants and their outputs.": {
        "start_entity": "Engineer",
        "related_labels": ["Ai_assistant", "Structuredoutput"]
    },
    
    "How do different types of agents (human, AI, assistants) compare in their use of tools and resources?": {
        "start_entity": "Agent",
        "related_labels": ["Ai_agent", "Ai_assistant", "Tool", "Resource"]
    }
}
