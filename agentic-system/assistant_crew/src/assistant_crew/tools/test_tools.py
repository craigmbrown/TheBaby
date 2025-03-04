#!/usr/bin/env python3
import os
import asyncio
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import sys
from pathlib import Path
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ToolTester")

# Import the tools from custom_tool.py
from assistant_crew.tools.custom_tool import (
    TavilySearchTool,
    URLsToGraphTool,
    QuestionAnsweringTool,
    GoogleCalendarTool,
    CreateCalendarEventTool
)

# Load environment variables
load_dotenv()

def test_tavily_search():
    """Test the Tavily Search tool with a sample query."""
    print("\n=== Testing Tavily Search Tool ===")
    try:
        tool = TavilySearchTool()
        query = "What are the latest developments in AI?"
        print(f"Query: {query}")
        result = tool._run(query=query, max_results=3, search_depth="basic")
        print("Result:")
        print(result)
        return True
    except Exception as e:
        print(f"Error testing Tavily Search Tool: {str(e)}")
        traceback.print_exc()
        return False

def test_urls_to_graph_tool(mode="custom"):
    """
    Test the URLs to Graph tool with a sample URL.
    
    This test mocks the email extraction to avoid needing actual Gmail credentials.
    """
    print(f"\n=== Testing URLs to Graph Tool (mode: {mode}) ===")
    try:
        tool = URLsToGraphTool()
        
        # Mock the get_latest_email method to return a fixed email with URLs
        def mock_get_latest_email(self, service):
            return """
            Subject: Test Email with URLs
            Body: Here are some interesting articles:
            https://en.wikipedia.org/wiki/Artificial_intelligence
            https://en.wikipedia.org/wiki/Machine_learning
            """
        
        # Save the original method and replace it with our mock
        original_method = URLsToGraphTool.get_latest_email
        URLsToGraphTool.get_latest_email = mock_get_latest_email
        
        try:
            result = tool._run(mode=mode)
            print("Result:")
            print(result)
            return True
        finally:
            # Restore the original method
            URLsToGraphTool.get_latest_email = original_method
    except Exception as e:
        print(f"Error testing URLs to Graph Tool: {str(e)}")
        traceback.print_exc()
        return False

def test_question_answering_tool():
    """Test the Question Answering tool with a sample question."""
    print("\n=== Testing Question Answering Tool ===")
    try:
        tool = QuestionAnsweringTool()
        question = "What is artificial intelligence?"
        print(f"Question: {question}")
        result = tool._run(question=question)
        print("Result:")
        print(result)
        return True
    except Exception as e:
        print(f"Error testing Question Answering Tool: {str(e)}")
        traceback.print_exc()
        return False

def test_google_calendar_tool():
    """Test the Google Calendar tool with today's date."""
    print("\n=== Testing Google Calendar Tool ===")
    try:
        tool = GoogleCalendarTool()
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"Checking events for date: {today}")
        result = tool._run(events_date=today)
        print("Result:")
        print(result)
        return True
    except Exception as e:
        print(f"Error testing Google Calendar Tool: {str(e)}")
        traceback.print_exc()
        return False

def test_create_calendar_event_tool():
    """Test the Create Calendar Event tool with a sample event."""
    print("\n=== Testing Create Calendar Event Tool ===")
    try:
        tool = CreateCalendarEventTool()
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)
        
        start_str = start_time.strftime("%Y-%m-%d %H:%M")
        end_str = end_time.strftime("%Y-%m-%d %H:%M")
        
        print(f"Creating event: Test Event from {start_str} to {end_str}")
        result = tool._run(
            summary="Test Event",
            start_datetime=start_str,
            end_datetime=end_str,
            description="This is a test event created by the test_tools.py script",
            location="Virtual"
        )
        print("Result:")
        print(result)
        return True
    except Exception as e:
        print(f"Error testing Create Calendar Event Tool: {str(e)}")
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tool tests and report results."""
    print("=== Running All Tool Tests ===\n")
    
    results = {
        "Tavily Search": test_tavily_search(),
        "URLs to Graph": test_urls_to_graph_tool(),
        "Question Answering": test_question_answering_tool(),
        "Google Calendar": test_google_calendar_tool(),
        "Create Calendar Event": test_create_calendar_event_tool()
    }
    
    print("\n=== Test Results Summary ===")
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    # Calculate overall success
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    print(f"\nOverall: {success_count}/{total_count} tests passed")
    
    return all(results.values())

def test_specific_tool(tool_name):
    """
    Test a specific tool by name.
    
    Args:
        tool_name: Name of the tool to test (case-insensitive)
    """
    tool_tests = {
        "tavily": test_tavily_search,
        "search": test_tavily_search,
        "urls": test_urls_to_graph_tool,
        "graph": test_urls_to_graph_tool,
        "question": test_question_answering_tool,
        "qa": test_question_answering_tool,
        "calendar": test_google_calendar_tool,
        "event": test_create_calendar_event_tool,
        "create": test_create_calendar_event_tool
    }
    
    # Find matching test function
    test_func = None
    for key, func in tool_tests.items():
        if key.lower() in tool_name.lower():
            test_func = func
            break
    
    if test_func:
        # For URLs to Graph tool, check if mode is specified
        if "graph" in tool_name.lower() or "urls" in tool_name.lower():
            if "custom" in tool_name.lower():
                return test_func(mode="custom")
            elif "current" in tool_name.lower():
                return test_func(mode="current")
            elif "baseline" in tool_name.lower():
                return test_func(mode="baseline")
        return test_func()
    else:
        print(f"No test found for tool: {tool_name}")
        print("Available tools to test:")
        for key in sorted(set(tool_tests.values()), key=lambda x: x.__name__):
            print(f"- {key.__name__.replace('test_', '')}")
        return False

if __name__ == "__main__":
    # Check if a specific tool was requested
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]
        test_specific_tool(tool_name)
    else:
        # Run all tests
        run_all_tests() 