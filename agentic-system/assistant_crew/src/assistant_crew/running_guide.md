# Assistant Crew - Setup and Running Guide

This guide will walk you through the process of setting up and running the Assistant Crew system. Follow these steps in order to ensure everything works correctly.

## Table of Contents
- [1. Getting Authentication Token](#1-getting-authentication-token)
- [2. Running Individual Crews or All Crews](#2-running-individual-crews-or-all-crews)
- [3. Running the Automated 5-Minute Interval Script](#3-running-the-automated-5-minute-interval-script)
- [4. Troubleshooting](#troubleshooting)
- [5. Additional Resources](#additional-resources)

## 1. Getting Authentication Token

First, you need to obtain the necessary authentication tokens for Google services (Gmail and Calendar).

### Running the Token Generator

```bash
# Navigate to the project root directory
cd /path/to/assistant_crew

# Run the token generator script
python -m assistant_crew.tools.get_token
```

When you run this script:
1. A browser window will open asking you to log in to your Google account
2. Grant the requested permissions for Gmail (read) and Calendar (read/write)
3. The script will save your authentication token to `token.pickle`

> **Important**: Make sure to grant all requested permissions. The token needs access to:
> - Gmail (read-only)
> - Google Calendar (read and write)
> - Google Calendar Events (create/modify)

## 2. Running Individual Crews or All Crews

Once you have the authentication token, you can run the crews.

### Running All Crews

```bash
# Navigate to the project root directory
cd /graphRAG/agentic-system/assistant_crew

# Run all crews
crewai run
```

This will execute all crews sequentially:
- EmailGraphCrew (extracts URLs from emails and creates knowledge graphs)
- GoogleCalendarCrew (retrieves today's calendar events)
- WebSearchCrew (performs web searches)
- QuestionAnsweringCrew (answers questions using the knowledge graph)

### Running a Specific Crew

To run just one crew, you can modify the `main.py` file to comment out the other crews, or use the command line arguments:


## 3. Running the Automated 5-Minute Interval Script

To have the crews run automatically every 5 minutes, use the `run_every_five_minutes.py` script.

```bash
# Navigate to the project root directory
cd /path/to/assistant_crew

# Run the automated script
python -m assistant_crew.run_every_five_minutes
```

This script will:
1. Run all crews immediately upon startup
2. Then run them again every 5 minutes
3. Log all activities to both the console and a file named `crew_runner.log`

### Running in the Background (Linux/macOS)

To keep the script running in the background even after closing your terminal:

```bash
nohup python -m assistant_crew.run_every_five_minutes > /dev/null 2>&1 &
```

To check if it's running:
```bash
ps aux | grep run_every_five_minutes.py
```

To stop it:
```bash
pkill -f run_every_five_minutes.py
```

### Running in the Background (Windows)

On Windows, you can use Task Scheduler to run the script at system startup, or use:

```powershell
Start-Process python -ArgumentList "-m assistant_crew.run_every_five_minutes" -WindowStyle Hidden
```

## Troubleshooting

### Token Issues

If you encounter authentication errors:
1. Delete the existing `token.pickle` file
2. Run the token generator again: `python -m assistant_crew.tools.get_token`
3. Make sure to grant all requested permissions

### Firecrawl API Errors

If you see errors related to Firecrawl:
1. Make sure your Firecrawl API key is valid and set in your environment variables
2. Some websites may be restricted by Firecrawl - try with different URLs
3. If you see a 403 error, contact help@firecrawl.com to request access to specific websites

### JSON Mode Errors

If you encounter errors about JSON mode or schemas:
1. Check that your OpenAI API key is valid and has sufficient credits



## Additional Resources

- For more information on CrewAI, visit their [documentation](https://docs.crewai.com/)
- For Firecrawl API documentation, visit [docs.firecrawl.dev](https://docs.firecrawl.dev/)
- For Google API permissions, visit [Google Cloud Console](https://console.cloud.google.com/)
