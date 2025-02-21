from crewai.tools import BaseTool
from pydantic import BaseModel, Field, model_validator
from tavily import TavilyClient
from typing import Optional, Any, Type, Annotated
from dotenv import load_dotenv
from GraphRAG.graphengine.memory_preprocessing import generate
from GraphRAG.graphengine.query_graph import query_graph
import os
from firecrawl import FirecrawlApp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pickle
import re
from urlextract import URLExtract

load_dotenv()


class TavilySearchInput(BaseModel):
    query: Annotated[str, Field(description="The search query string")]
    max_results: Annotated[
        int, Field(description="Maximum number of results to return", ge=1, le=10)
    ] = 5
    search_depth: Annotated[
        str,
        Field(
            description="Search depth: 'basic' or 'advanced'",
            choices=["basic", "advanced"],
        ),
    ] = "basic"
    
    
class TavilySearchTool(BaseTool):
    name: str = "Tavily Search"
    description: str = (
        "Use the Tavily API to perform a web search and get AI-curated results."
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

    ontology_mode: Annotated[
        Optional[str], 
        Field(
            description="The mode to use for the ontology of the knowledge graph", 
            choices=["expressive", "strict"]
        )
    ] = "expressive"
    mode: Annotated[
        str, 
        Field(
            description="The mode to use for the ontology of the knowledge graph", 
            choices=["current", "custom", "baseline"]
        )
    ] = "custom"

    @model_validator(mode='before')
    @classmethod
    def adjust_fields(cls, values):
        """
        Adjusts the input values so that the combination always ends up being:
         - mode: "custom"
         - ontology_mode: "expressive"
        """
        if values.get("mode") != "custom":
            values["mode"] = "custom"
            values["ontology_mode"] = "expressive"
        elif values.get("ontology_mode") is None:
            values["ontology_mode"] = "expressive"
        return values
    
class URLsToGraphTool(BaseTool):
    name: str = "URLs to Graph"
    description: str = (
        "Use the URLs to Graph tool to convert URLs to a knowledge graph."
    )
    args_schema: Type[BaseModel] = URLsToGraphInput

    def _get_credentials(self) -> Any:
        if not os.path.exists('credentials.json'):
            raise FileNotFoundError(
                "credentials.json not found. Please download OAuth 2.0 credentials "
                "from Google Cloud Console and save as 'credentials.json'"
            )
        creds = None
        if os.path.exists('token.pickle'):
            try:
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Error reading token.pickle: {e}")
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                return creds
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',['https://www.googleapis.com/auth/gmail.readonly'])
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            return creds
        except Exception as e:
            raise Exception(f"Failed to get new credentials: {e}")

    def get_latest_email(self, service: Any) -> str:
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
        app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
        response = app.scrape_url(url=url)
        if response["metadata"]["statusCode"] == 200:
            return response["markdown"]
        else:
            raise Exception("Failed to extract data: " + response.get("error", "Unknown error"))

    def extract_urls(self, text: str) -> list:
        extractor = URLExtract()
        return extractor.find_urls(text)

    def convert_text_to_graph(self, texts, generation_mode: str, ontology_mode: str) -> bool:
        graphs_created = []
        for text in texts:
            graph_created = generate(text, mode=generation_mode, ontology_mode=ontology_mode)
            graphs_created.append(graph_created)
        return all(graphs_created)

    def _run(self, mode: str = "expressive", ontology_mode: str = "custom") -> str:
        # Initialize credentials and build the Gmail service locally
        creds = self._get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        latest_email_body = self.get_latest_email(service)
        urls = self.extract_urls(latest_email_body)
        texts = [self.extract_texts(url) for url in urls]
        converted = self.convert_text_to_graph(texts, generation_mode=mode, ontology_mode=ontology_mode)
        return "Graph created successfully" if converted else "Graph creation failed"
    
    

class QuestionAnsweringInput(BaseModel):
    question: Annotated[str, Field(description="The question to answer")]


class QuestionAnsweringTool(BaseTool):
    name: str = "Question Answering"
    description: str = (
        "Use the Question Answering tool to answer questions based on a given context."
    )
    args_schema: Type[BaseModel] = QuestionAnsweringInput

    async def _run(self, question: str) -> str:
        return await query_graph(question)
    


class GoogleCalendarInput(BaseModel):
    events_date: Annotated[str, Field(description="The date to get the events for in format YYYY-MM-DD")]
    


class GoogleCalendarTool(BaseTool):
    name: str = "Google Calendar"
    description: str = (
        "Use the Google Calendar tool to get events of a specific date from your Google Calendar."
    )
    args_schema: Type[BaseModel] = GoogleCalendarInput

    def _get_credentials(self) -> Any:
        if not os.path.exists('credentials.json'):
            raise FileNotFoundError(
                "credentials.json not found. Please download OAuth 2.0 credentials "
                "from Google Cloud Console and save as 'credentials.json'"
            )
        creds = None
        if os.path.exists('token.pickle'):
            try:
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Error reading token.pickle: {e}")
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                return creds
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
        try:
            # Directly inline the scope value here.
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', ['https://www.googleapis.com/auth/calendar.readonly'])
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            return creds
        except Exception as e:
            raise Exception(f"Failed to get new credentials: {e}")

    def _run(self, events_date: str) -> str:
        try:
            # Initialize credentials and build the service locally
            creds = self._get_credentials()
            service = build('calendar', 'v3', credentials=creds)
            
            # Parse the provided date and define the day’s time window
            date_obj = datetime.strptime(events_date, '%Y-%m-%d')
            start_time = f"{date_obj.replace(hour=0, minute=0, second=0).isoformat()}Z"
            end_time = f"{date_obj.replace(hour=23, minute=59, second=59).isoformat()}Z"
            
            # Query the Calendar API
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            if not events:
                return f"No events found for {events_date}."
            
            # Format the events for output
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted_time = start_time.strftime('%I:%M %p')
                summary = event.get('summary', 'No title')
                formatted_events.append(f"- {formatted_time}: {summary}")
            
            return "\n".join([f"Events for {events_date}:"] + formatted_events)
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD format."
        except Exception as e:
            return f"An error occurred: {str(e)}"
    