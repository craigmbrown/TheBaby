#!/usr/bin/env python3
import time
import schedule
import logging
import sys
import os
from datetime import datetime
import traceback
import warnings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crew_runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CrewRunner")

# Ignore specific warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Import crews from crew.py
from crew import (
    WebSearchCrew,
    EmailGraphCrew,
    QuestionAnsweringCrew,
    GoogleCalendarCrew
)

def run_all_crews():
    """
    Function to run all crews - this will be executed every 5 minutes
    """
    try:
        logger.info(f"Starting crew execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run Email Graph Crew
        try:
            logger.info("Running EmailGraphCrew...")
            email_crew = EmailGraphCrew()
            email_result = email_crew.crew().kickoff()
            logger.info(f"EmailGraphCrew completed with result: {email_result[:100]}..." if email_result else "No result")
        except Exception as e:
            logger.error(f"Error running EmailGraphCrew: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Run Calendar Crew
        try:
            logger.info("Running GoogleCalendarCrew...")
            cal_crew = GoogleCalendarCrew()
            today = datetime.now().strftime("%Y-%m-%d")
            cal_inputs = {
                "events_date": today
            }
            cal_result = cal_crew.crew().kickoff(inputs=cal_inputs)
            logger.info(f"GoogleCalendarCrew completed with result: {cal_result[:100]}..." if cal_result else "No result")
        except Exception as e:
            logger.error(f"Error running GoogleCalendarCrew: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Uncomment these if you want to run these crews as well
        
        # Run Web Search Crew
        try:
            logger.info("Running WebSearchCrew...")
            web_crew = WebSearchCrew()
            web_inputs = {
                "user_input": "What are the latest developments in AI today?"
            }
            web_result = web_crew.crew().kickoff(inputs=web_inputs)
            logger.info(f"WebSearchCrew completed with result: {web_result[:100]}..." if web_result else "No result")
        except Exception as e:
            logger.error(f"Error running WebSearchCrew: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Run Question Answering Crew
        try:
            logger.info("Running QuestionAnsweringCrew...")
            qa_crew = QuestionAnsweringCrew()
            qa_inputs = {
                "user_input": "Summarize the key information from the latest knowledge graph"
            }
            qa_result = qa_crew.crew().kickoff(inputs=qa_inputs)
            logger.info(f"QuestionAnsweringCrew completed with result: {qa_result[:100]}..." if qa_result else "No result")
        except Exception as e:
            logger.error(f"Error running QuestionAnsweringCrew: {str(e)}")
            logger.error(traceback.format_exc())
        
        logger.info(f"All crews completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"Unexpected error in run_all_crews: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    """
    Main function that sets up the schedule and runs the infinite loop
    """
    logger.info("Starting crew runner script")
    
    # Set up schedule to run every 5 minutes
    schedule.every(5).minutes.do(run_all_crews)
    
    # Run once immediately on startup
    logger.info("Running crews immediately on startup")
    run_all_crews()
    
    # Then run according to schedule
    logger.info("Entering main loop - will run every 5 minutes")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            logger.error(traceback.format_exc())
            # Sleep a bit longer if there was an error to avoid rapid error loops
            time.sleep(10)
    
    logger.info("Crew runner script terminated")

if __name__ == "__main__":
    main()