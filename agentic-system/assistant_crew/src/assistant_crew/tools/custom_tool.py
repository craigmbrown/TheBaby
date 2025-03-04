from crewai.tools import BaseTool
from pydantic import BaseModel, Field, model_validator
from tavily import TavilyClient
from typing import Optional, Any, Type, Annotated
from dotenv import load_dotenv
from .GraphRAG.graphengine.memory_preprocessing import generate
from .GraphRAG.graphengine.query_graph import query_graph
import os
from firecrawl import FirecrawlApp
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pickle
import re
from urlextract import URLExtract
from google.oauth2.credentials import Credentials as InstalledCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials as UserCredentials

load_dotenv()

# Get the current root path and use it for relative paths
import os.path

# Determine the root directory (where the package is installed)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "assistant_crew", "tools", "credentials.json")
TOKEN_PICKLE_PATH = os.path.join(ROOT_DIR, "assistant_crew", "tools", "token.pickle")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]



class TavilySearchInput(BaseModel):
    query: Annotated[str, Field(description="The search query to find information on the web")]
    max_results: Annotated[
        int, Field(description="Maximum number of search results to return (between 1 and 10)", ge=1, le=10)
    ] = 5
    search_depth: Annotated[
        str,
        Field(
            description="Search depth level: 'basic' for faster, simpler results or 'advanced' for more comprehensive results",
            choices=["basic", "advanced"],
        ),
    ] = "basic"
    
    
class TavilySearchTool(BaseTool):
    name: str = "Tavily Search"
    description: str = (
        "Performs a comprehensive web search using the Tavily API to find relevant information "
        "from across the internet. Returns AI-curated search results with titles, content snippets, and source URLs."
    )
    args_schema: Type[BaseModel] = TavilySearchInput

    def _run(self, query: str, max_results: int = 5, search_depth: str = "basic") -> str:
        # Retrieve API key from environment
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        
        # Initialize the client locally
        client = TavilyClient(api_key=api_key)
        
        try:
            response = client.search(
                query=query, max_results=max_results, search_depth=search_depth
            )
            return self._process_response(response)
        except Exception as e:
            return f"An error occurred while performing the search: {str(e)}"

    def _process_response(self, response: dict) -> str:
        if not response.get("results"):
            return "No results found."
        results = []
        for item in response["results"][:5]:
            title = item.get("title", "No title")
            content = item.get("content", "No content available")
            url = item.get("url", "No URL available")
            results.append(f"Title: {title}\\nContent: {content}\\nURL: {url}\\n")
        return "\\n".join(results)
    
    

class URLsToGraphInput(BaseModel):


    mode: Annotated[
        str, 
        Field(
            description="The generation mode for the knowledge graph: 'current' for latest settings, 'custom' for user-defined settings, or 'baseline' for default settings", 
            choices=["current", "custom", "baseline"]
        )
    ] = "current"


    
class URLsToGraphTool(BaseTool):
    name: str = "URLs to Graph"
    description: str = (
        "Extracts URLs from the most recent email, scrapes their content, "
        "and creates a knowledge graph out of the results."
    )
    args_schema: Type[BaseModel] = URLsToGraphInput

    def _get_credentials(self) -> Any:
        creds = None
        if os.path.exists(TOKEN_PICKLE_PATH):
            with open(TOKEN_PICKLE_PATH, "rb") as token_file:
                creds = pickle.load(token_file)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0, open_browser=True)
            with open(TOKEN_PICKLE_PATH, "wb") as token_file:
                pickle.dump(creds, token_file)

        return creds

    def get_latest_email(self, service: Any) -> str:
        """
        Retrieve the most recent email from the 'INBOX' label.
        """
        try:
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=1
            ).execute()
            if 'messages' not in results:
                return "No messages found."
            msg = service.users().messages().get(
                userId='me',
                id=results['messages'][0]['id'],
                format='full'
            ).execute()
            headers = msg['payload']['headers']
            subject = next(header['value'] for header in headers if header['name'].lower() == 'subject')
            if 'parts' in msg['payload']:
                body = msg['payload']['parts'][0]['body'].get('data', '')
            else:
                body = msg['payload']['body'].get('data', '')
            if body:
                import base64
                body = base64.urlsafe_b64decode(body).decode('utf-8')
            return f"Subject: {subject}\nBody: {body}"
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def extract_texts(self, url: str) -> str:
        """
        Scrapes the content from a URL using Firecrawl.
        """
        try:
            app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
            response = app.crawl_url(url=url,
                                    params={
                'limit': 100, 
                'scrapeOptions': {'formats': ['markdown', 'html']}
                    },
            poll_interval=30)
            print(response)
            if response["success"] == True:
                return response["data"][0]["markdown"]
            else:
                print(f"Error in response: {response.get('error', 'Unknown error')}")
                # Return empty string instead of raising exception
                return ""
        except Exception as e:
            print(f"Exception occurred while extracting text: {str(e)}")
            return ""


    def extract_urls(self, text: str) -> list:
        """
        Finds any URLs in the given text using URLExtract.
        """
        extractor = URLExtract()
        return extractor.find_urls(text)

    def convert_text_to_graph(self, texts, mode="custom", ontology_mode="expressive") -> bool:
        """
        Converts the extracted texts into a knowledge graph.
        
        Args:
            texts: List of text content to convert
            mode: Mode for graph generation ("current", "custom", "baseline")
            ontology_mode: Mode for ontology structure ("expressive", "strict")
            
        Returns:
            bool: True if graph was created successfully, False otherwise
        """
        try:
            # Check if texts is empty or None
            if not texts:
                print("No texts provided for graph generation")
                return False
                
            # Make sure texts is a list of strings
            if not isinstance(texts, list):
                texts = [texts]
                
            # Filter out any None values
            texts = [text for text in texts if text]
            
            if not texts:
                print("No valid texts after filtering")
                return False
                
            # For custom mode, we need to pass the ontology_mode
            if mode == "custom":
                return generate(
                    texts=texts,
                    mode=ontology_mode,
                    require_confirmation=False,
                    viz=False
                )
            else:
                # For current or baseline mode
                return generate(
                    texts=texts,
                    mode=mode,
                    require_confirmation=False,
                    viz=False
                )
        except Exception as e:
            print(f"Error in convert_text_to_graph: {str(e)}")
            return False

    def _run(self, mode: str = "custom") -> str:
        """
        Implementation of the abstract _run method required by BaseTool.
        
        Args:
            mode: The generation mode for the knowledge graph
            
        Returns:
            str: Status message indicating success or failure
        """
        # 1) Initialize credentials and build the Gmail service
        creds = self._get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        # 2) Get latest email body contents, extract URLs, then scrape each URL
        latest_email_body = self.get_latest_email(service)
        urls = self.extract_urls(latest_email_body)
        
        if not urls:
            return "No URLs found in the latest email."
            
        # Extract text from each URL
        texts = []
        for url in urls:
            text = self.extract_texts(url)
            if text:  # Only add non-empty texts
                texts.append(text)
        
        if not texts:
            return "Failed to extract content from URLs."

        # 3) Save all scraped text to a single Markdown file
        import datetime
        from pathlib import Path

        # e.g., "scraped_content_20231002_211213.md"
        filename = f"scraped_content_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        md_file = Path(filename)
        md_file_contents = []

        for idx, text in enumerate(texts, start=1):
            md_file_contents.append(f"## Content from URL #{idx}\n\n{text}\n\n---\n\n")

        md_file.write_text("".join(md_file_contents), encoding="utf-8")
        print(f"Scraped content saved to {md_file.resolve()}")

        # 4) Convert scraped text into a knowledge graph
        # Parse the mode parameter to determine how to call convert_text_to_graph
        if mode == "custom":
            # For custom mode, we need to specify the ontology_mode
            converted = self.convert_text_to_graph(texts, mode="custom", ontology_mode="expressive")
        else:
            # For current or baseline mode
            converted = self.convert_text_to_graph(texts, mode=mode)
            
        return "Graph created successfully" if converted else "Graph creation failed"


class QuestionAnsweringInput(BaseModel):
    question: Annotated[str, Field(description="The specific question you want to answer using the knowledge graph")]


class QuestionAnsweringTool(BaseTool):
    name: str = "Question Answering"
    description: str = (
        "Queries the previously created knowledge graph to answer questions based on the information "
        "stored in the graph. This tool leverages the structured data from web content to provide "
        "accurate and contextually relevant answers to your questions."
    )
    args_schema: Type[BaseModel] = QuestionAnsweringInput

    def _run(self, question: str) -> str:
        return query_graph(question)
    


class GoogleCalendarInput(BaseModel):
    events_date: Annotated[str, Field(description="The specific date to retrieve calendar events for, in YYYY-MM-DD format (e.g., 2024-05-15)")]
    

class GoogleCalendarTool(BaseTool):
    """
    Retrieves and displays events scheduled in your Google Calendar for a specific date.
    Connects to your Google Calendar, fetches events for the specified date,
    and returns them in a chronological list with event times and titles.
    """
    name: str = "Google Calendar"
    description: str = (
        "Retrieves and displays all events scheduled in your Google Calendar for a specific date. "
        "This tool connects to your Google Calendar account, fetches the events for the requested date, "
        "and returns them in a chronological list with event times and titles."
    )
    args_schema: Type[BaseModel] = GoogleCalendarInput

    def _get_credentials(self) -> Any:
        creds = None
        if os.path.exists(TOKEN_PICKLE_PATH):
            with open(TOKEN_PICKLE_PATH, "rb") as token_file:
                creds = pickle.load(token_file)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0, open_browser=True)
            with open(TOKEN_PICKLE_PATH, "wb") as token_file:
                pickle.dump(creds, token_file)

        return creds

    def _run(self, events_date: str) -> str:
        """
        Implementation of the abstract _run method required by BaseTool.
        Retrieves events from the user's Google Calendar for the specified date (YYYY-MM-DD).
        
        Args:
            events_date: The date to retrieve events for in YYYY-MM-DD format
            
        Returns:
            str: Formatted list of events or error message
        """
        try:
            # Validate date format
            try:
                date_obj = datetime.strptime(events_date, "%Y-%m-%d")
            except ValueError:
                return "Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-05-15)."
            
            # Get credentials and build service
            creds = self._get_credentials()
            service = build("calendar", "v3", credentials=creds)

            # Set time boundaries for the specified date (midnight to 11:59:59 PM)
            # Use UTC timezone for API requests
            start_datetime = datetime.combine(date_obj.date(), datetime.min.time())
            end_datetime = datetime.combine(date_obj.date(), datetime.max.time())
            
            # Format for Google Calendar API (RFC 3339 timestamp with Z suffix for UTC)
            start_time = start_datetime.isoformat() + "Z"
            end_time = end_datetime.isoformat() + "Z"

            # Fetch events
            events_result = service.events().list(
                calendarId="primary",
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            if not events:
                return f"No events found for {events_date}."

            # Format events for display
            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                
                # Handle both datetime and date-only formats
                if 'T' in start:  # It's a datetime
                    # Remove Z or timezone offset and parse
                    dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%I:%M %p")
                else:  # It's a date-only event (all-day)
                    formatted_time = "All day"
                    
                summary = event.get("summary", "No title")
                formatted_events.append(f"- {formatted_time}: {summary}")

            return "\n".join([f"Events for {events_date}:"] + formatted_events)

        except Exception as e:
            return f"An error occurred: {str(e)}"

class CreateCalendarEventInput(BaseModel):
    summary: Annotated[str, Field(description="The title or summary of the event")]
    start_datetime: Annotated[str, Field(description="The start date and time in format 'YYYY-MM-DD HH:MM' (e.g., '2024-05-15 14:30')")]
    end_datetime: Annotated[str, Field(description="The end date and time in format 'YYYY-MM-DD HH:MM' (e.g., '2024-05-15 15:30')")]
    description: Annotated[Optional[str], Field(description="Optional description or details for the event")] = None
    location: Annotated[Optional[str], Field(description="Optional location for the event")] = None
    

class CreateCalendarEventTool(BaseTool):
    """
    Creates a new event in your Google Calendar with the specified details.
    Connects to your Google Calendar, creates a new event with the provided information,
    and returns a confirmation with the event details.
    """
    name: str = "Create Calendar Event"
    description: str = (
        "Creates a new event in your Google Calendar with the specified details. "
        "This tool allows you to schedule events with a title, start and end times, "
        "and optional description and location information."
    )
    args_schema: Type[BaseModel] = CreateCalendarEventInput

    def _get_credentials(self) -> Any:
        creds = None
        if os.path.exists(TOKEN_PICKLE_PATH):
            with open(TOKEN_PICKLE_PATH, "rb") as token_file:
                creds = pickle.load(token_file)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0, open_browser=True)
            with open(TOKEN_PICKLE_PATH, "wb") as token_file:
                pickle.dump(creds, token_file)

        return creds

    def _run(self, summary: str, start_datetime: str, end_datetime: str, description: Optional[str] = None, location: Optional[str] = None) -> str:
        """
        Implementation of the abstract _run method required by BaseTool.
        Creates a new event in the user's Google Calendar with the specified details.
        
        Args:
            summary: The title or summary of the event
            start_datetime: The start date and time in format 'YYYY-MM-DD HH:MM'
            end_datetime: The end date and time in format 'YYYY-MM-DD HH:MM'
            description: Optional description or details for the event
            location: Optional location for the event
            
        Returns:
            str: Confirmation message with event details or error message
        """
        try:
            # Parse and validate datetime formats
            try:
                start_dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
            except ValueError:
                return "Invalid datetime format. Please use 'YYYY-MM-DD HH:MM' format (e.g., '2024-05-15 14:30')."
            
            # Ensure end time is after start time
            if end_dt <= start_dt:
                return "End time must be after start time."
            
            # Get credentials and build service
            creds = self._get_credentials()
            service = build("calendar", "v3", credentials=creds)
            
            # Create event body
            event_body = {
                'summary': summary,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            # Add optional fields if provided
            if description:
                event_body['description'] = description
            if location:
                event_body['location'] = location
                
            # Insert the event
            event = service.events().insert(calendarId='primary', body=event_body).execute()
            
            # Format confirmation message
            start_formatted = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
            end_formatted = end_dt.strftime("%I:%M %p")
            
            confirmation = [
                f"✅ Event created successfully!",
                f"Title: {summary}",
                f"When: {start_formatted} to {end_formatted}"
            ]
            
            if location:
                confirmation.append(f"Where: {location}")
            if description:
                confirmation.append(f"Description: {description}")
                
            confirmation.append(f"Event link: {event.get('htmlLink')}")
            
            return "\n".join(confirmation)
            
        except Exception as e:
            return f"An error occurred while creating the event: {str(e)}"