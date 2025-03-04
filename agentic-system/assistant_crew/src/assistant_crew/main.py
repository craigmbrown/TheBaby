#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from assistant_crew.crew import (
    WebSearchCrew,
    EmailGraphCrew,
    QuestionAnsweringCrew,
    GoogleCalendarCrew
)

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run all crews sequentially.
    """
    try:
        # Web Search Crew
        web_crew = WebSearchCrew()
        web_inputs = {
            "user_input": "What is the latest news on AI?"
        }
        web_result = web_crew.crew().kickoff(inputs=web_inputs)
        print("WebSearchCrew result:")
        print(web_result)
        
        # Email Graph Crew
        email_crew = EmailGraphCrew()
        email_result = email_crew.crew().kickoff()
        print("\nEmailGraphCrew result:")
        print(email_result)
        
        # Question Answering Crew
        qa_crew = QuestionAnsweringCrew()
        qa_inputs = {
            "user_input": "what does Ada use?"
        }
        qa_result = qa_crew.crew().kickoff(inputs=qa_inputs)
        print("\nQuestionAnsweringCrew result:")
        print(qa_result)
        
        # Calendar Crew
        cal_crew = GoogleCalendarCrew()
        cal_inputs = {
            "events_date": datetime.now().strftime("%Y-%m-%d")
        }
        cal_result = cal_crew.crew().kickoff(inputs=cal_inputs)
        print("\nGoogleCalendarCrew result:")
        print(cal_result)

    except Exception as e:
        raise Exception(f"An error occurred while running the crews: {e}")

def train():
    """
    Train the specified crew for a given number of iterations.
    Usage: python main.py train <crew_name> <n_iterations> <filename>
    """
    if len(sys.argv) != 4:
        print("Usage: python main.py train <crew_name> <n_iterations> <filename>")
        return

    crew_name = sys.argv[1]
    n_iterations = int(sys.argv[2])
    filename = sys.argv[3]

    crews = {
        "web": WebSearchCrew(),
        "email": EmailGraphCrew(),
        "qa": QuestionAnsweringCrew(),
        "calendar": GoogleCalendarCrew()
    }

    if crew_name not in crews:
        raise ValueError(f"Invalid crew name. Choose from: {', '.join(crews.keys())}")

    try:
        crew = crews[crew_name]
        crew.crew().train(n_iterations=n_iterations, filename=filename)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    Usage: python main.py replay <crew_name> <task_id>
    """
    if len(sys.argv) != 3:
        print("Usage: python main.py replay <crew_name> <task_id>")
        return

    crew_name = sys.argv[1]
    task_id = sys.argv[2]

    crews = {
        "web": WebSearchCrew(),
        "email": EmailGraphCrew(),
        "qa": QuestionAnsweringCrew(),
        "calendar": GoogleCalendarCrew()
    }

    if crew_name not in crews:
        raise ValueError(f"Invalid crew name. Choose from: {', '.join(crews.keys())}")

    try:
        crew = crews[crew_name]
        crew.crew().replay(task_id=task_id)
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    Usage: python main.py test <crew_name> <n_iterations> <openai_model_name>
    """
    if len(sys.argv) != 4:
        print("Usage: python main.py test <crew_name> <n_iterations> <openai_model_name>")
        return

    crew_name = sys.argv[1]
    n_iterations = int(sys.argv[2])
    openai_model_name = sys.argv[3]

    crews = {
        "web": WebSearchCrew(),
        "email": EmailGraphCrew(),
        "qa": QuestionAnsweringCrew(),
        "calendar": GoogleCalendarCrew()
    }

    if crew_name not in crews:
        raise ValueError(f"Invalid crew name. Choose from: {', '.join(crews.keys())}")

    try:
        crew = crews[crew_name]
        crew.crew().test(n_iterations=n_iterations, openai_model_name=openai_model_name)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        run()
    elif sys.argv[1] == "train":
        train()
    elif sys.argv[1] == "replay":
        replay()
    elif sys.argv[1] == "test":
        test()
    else:
        print("Invalid command. Use: run, train, replay, or test")
