
# Documentation for CrewAI Tools

This document provides an overview and usage instructions for four custom CrewAI tools:

1. **TavilySearchTool**
2. **URLsToGraphTool**
3. **QuestionAnsweringTool**
4. **GoogleCalendarTool**

Each tool is built on top of CrewAI’s `BaseTool` and uses Pydantic models for input validation. Below are the details for each tool along with instructions on how to run them.

---

## 1. TavilySearchTool

### Purpose
- **TavilySearchTool** uses the Tavily API to perform web searches and retrieve AI-curated results.

### Input Schema: `TavilySearchInput`
- **Fields:**
  - `query` (string): The search query.
    - *Description:* "The search query string"
  - `max_results` (int): Maximum number of results to return (default is 5).
    - *Constraints:* Must be between 1 and 10.
    - *Description:* "Maximum number of results to return"
  - `search_depth` (string): Determines the depth of the search; options are `"basic"` or `"advanced"` (default is `"basic"`).
    - *Description:* "Search depth: 'basic' or 'advanced'"

### Implementation Details
- The tool retrieves the Tavily API key from an environment variable (`TAVILY_API_KEY`).
- The API key is used to instantiate a `TavilyClient` locally within the `_run` method.
- The `_run` method calls the client's `search` method and processes the response:
  - If results are found, it returns a formatted string with the top 5 results (title, content, and URL).
  - If no results are found or an error occurs, it returns an appropriate message.

### Example Usage
```python
# Ensure the environment variable TAVILY_API_KEY is set.
result = TavilySearchTool()._run(query="latest AI trends", max_results=5, search_depth="basic")
print(result)
```

---

## 2. URLsToGraphTool

### Purpose
- **URLsToGraphTool** extracts URLs from the latest email and converts them into a structured knowledge graph.

### Input Schema: `URLsToGraphInput`
- **Fields:**
  - `ontology_mode` (Optional[string]): Mode for the ontology of the knowledge graph.
    - *Choices:* `"expressive"` or `"strict"`
    - *Default:* `"expressive"`
  - `mode` (string): Mode to use for the knowledge graph.
    - *Choices:* `"current"`, `"custom"`, `"baseline"`
    - *Default:* `"custom"`
- **Model Validator:**
  - Ensures that if `mode` is not `"custom"`, it resets `mode` to `"custom"` and sets `ontology_mode` to `"expressive"`.

### Implementation Details
- The tool handles email extraction and graph generation:
  - **Credentials Setup:**  
    - Uses a local `_get_credentials` method to load credentials from `credentials.json` (and a token from `token.pickle` if available). The scope value (`https://www.googleapis.com/auth/gmail.readonly`) is inlined directly.
  - **Email Extraction:**  
    - The `_run` method builds a Gmail service and retrieves the latest email.
    - It then extracts the email's text and uses `URLExtract` to find URLs.
  - **Graph Generation:**  
    - For each URL, the tool calls `extract_texts` (which uses `FirecrawlApp`) to scrape the webpage content.
    - It then passes the texts to a `generate` function (from `GraphRAG.graphengine.memory_preprocessing`) to create a knowledge graph.
  - Returns a confirmation message based on whether all graphs were created successfully.

### Example Usage
```python
# Example: Run the tool with default modes.
result = URLsToGraphTool()._run(mode="expressive", ontology_mode="custom")
print(result)
```

---

## 3. QuestionAnsweringTool

### Purpose
- **QuestionAnsweringTool** answers questions based on a given context, leveraging a knowledge graph query function.

### Input Schema: `QuestionAnsweringInput`
- **Field:**
  - `question` (string): The question to be answered.
    - *Description:* "The question to answer"

### Implementation Details
- The tool defines an asynchronous `_run` method.
- It calls the external `query_graph` function (from `GraphRAG.graphengine.query_graph`) with the provided question and returns the result.

### Example Usage
```python
import asyncio

# Run the asynchronous tool.
async def run_qa():
    result = await QuestionAnsweringTool()._run(question="What is the impact of AI on modern healthcare?")
    print(result)

asyncio.run(run_qa())
```

---

## 4. GoogleCalendarTool

### Purpose
- **GoogleCalendarTool** retrieves events for a specific date from the user's Google Calendar.

### Input Schema: `GoogleCalendarInput`
- **Field:**
  - `events_date` (string): The date for which events should be retrieved, in the format `YYYY-MM-DD`.
    - *Description:* "The date to get the events for in format YYYY-MM-DD"

### Implementation Details
- **Credentials Setup:**
  - Uses `_get_credentials` to obtain credentials from `credentials.json` and a cached token (`token.pickle`). The scope value (`https://www.googleapis.com/auth/calendar.readonly`) is inlined directly.
- **Calendar Query:**
  - The `_run` method builds a Google Calendar service using the obtained credentials.
  - It converts the provided date into a start and end time for that day.
  - Queries the Calendar API for events within that time range.
  - Formats the events (time and summary) into a string.
- **Error Handling:**
  - Returns a specific error message if the date format is invalid or if no events are found.

### Example Usage
```python
result = GoogleCalendarTool()._run(events_date="2024-03-20")
print(result)
```

---

## How to Run These Tools

1. **Environment Setup:**
   - Ensure that all required environment variables are set (e.g., `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`).
   - Place necessary credential files (`credentials.json` and `token.pickle`) in the expected directories.

2. **Running Individually:**
   - Instantiate and call each tool’s `_run` method as shown in the examples above.
   - For asynchronous tools like `QuestionAnsweringTool`, use an event loop ( with `asyncio.run`)
```
import asyncio

async def run_question_answering():
    # Instantiate the QuestionAnsweringTool
    qa_tool = QuestionAnsweringTool()
    
    # Define your question
    question = "What is the impact of AI on modern healthcare?"
    
    # Run the tool asynchronously using its _run method
    answer = await qa_tool._run(question)
    
    print("Answer:", answer)

# Execute the asynchronous function using asyncio.run()
asyncio.run(run_question_answering())
```
