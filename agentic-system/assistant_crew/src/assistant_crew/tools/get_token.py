import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import sys
from pathlib import Path

# Define the scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

# Get the current root path and use it for relative paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_PATH = os.path.join(ROOT_DIR, "assistant_crew", "tools", "credentials.json")
TOKEN_PICKLE_PATH = os.path.join(ROOT_DIR, "assistant_crew", "tools", "token.pickle")

def generate_gmail_token():
    """Generate a token for Gmail API access using manual authorization flow."""
    creds = None
    
    # Check if token.pickle exists
    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, "rb") as token:
            creds = pickle.load(token)
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create the flow using the client secrets file
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            
            # Set the redirect URI to the out-of-band (OOB) URI for command-line applications
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            # Generate the authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            print(f"\n\n{'='*80}")
            print("Please go to this URL on any device with a browser:")
            print(f"\n{auth_url}\n")
            print("After authorization, you will see a code on the page.")
            print("Copy that code and paste it below.")
            print(f"{'='*80}\n")
            
            # Get the authorization code from the user
            code = input("Enter the authorization code: ").strip()
            
            # Exchange the authorization code for credentials
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save the credentials for future use
            with open(TOKEN_PICKLE_PATH, "wb") as token:
                pickle.dump(creds, token)
            
            print(f"\nCredentials saved to {TOKEN_PICKLE_PATH}")
    
    return creds

if __name__ == "__main__":
    generate_gmail_token()