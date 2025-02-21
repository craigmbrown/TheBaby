from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from tools.custom_tool import TavilySearchTool, URLsToGraphTool, QuestionAnsweringTool, GoogleCalendarTool
from dotenv import load_dotenv
load_dotenv()

# Basic configuration: configure your LLM instance once
llm = LLM(model="openai/gpt-4o-mini", timeout=600)

# Instantiate your custom tools
tavily_search = TavilySearchTool()
urls_to_graph = URLsToGraphTool()
question_answering = QuestionAnsweringTool()
google_calendar = GoogleCalendarTool()

###############################################################################
# Crew 1: Web Search Crew - Contains a single agent for web search.
###############################################################################
@CrewBase
class WebSearchCrew:
    agents_config = 'babycrew/config/websearch_agents.yaml'
    # tasks_config = 'config/tasks.yaml'

    @agent
    def web_search_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["web_search_assistant"],
            tools=[tavily_search],
            verbose=True,
            llm=llm,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,   # Automatically created by the @agent decorator
            tasks=[],             # No tasks defined, running agent as is
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Crew 2: Email URLs-to-Graph Crew - Contains a single agent for URL-to-Graph conversion.
###############################################################################
@CrewBase
class EmailGraphCrew:
    agents_config = 'babycrew/config/emails_agents.yaml'
    # tasks_config = 'config/tasks.yaml'

    @agent
    def email_urls_to_graph_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_urls_to_graph_assistant"],
            tools=[urls_to_graph],
            verbose=True,
            llm=llm,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[],  
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Crew 3: Question Answering Crew - Contains a single agent for question answering.
###############################################################################
@CrewBase
class QuestionAnsweringCrew:
    agents_config = 'babycrew/config/qa_agents.yaml'
    # tasks_config = 'config/tasks.yaml'

    @agent
    def question_answering_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["question_answering_assistant"],
            tools=[question_answering],
            verbose=True,
            llm=llm,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[],  
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Crew 4: Google Calendar Crew - Contains a single agent for calendar retrieval.
###############################################################################
@CrewBase
class GoogleCalendarCrew:
    agents_config = 'babycrew/config/calendar_agents.yaml'
    # tasks_config = 'config/tasks.yaml'

    @agent
    def google_calendar_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["google_calendar_assistant"],
            tools=[google_calendar],
            verbose=True,
            llm=llm,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[],  
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Running Crews
###############################################################################
if __name__ == "__main__":
    # Example: Running the Web Search Crew
    web_crew = WebSearchCrew()
    web_inputs = {
        "user_input": "What is the latest news on AI?"
    }
    web_result = web_crew.crew().kickoff(inputs=web_inputs)
    print("WebSearchCrew result:")
    print(web_result)
    
    # Similarly, you can instantiate and run other crews:
    email_crew = EmailGraphCrew()
    email_result = email_crew.crew().kickoff()
    print("EmailGraphCrew result:")
    print(email_result)
    
    qa_crew = QuestionAnsweringCrew()
    qa_inputs = {
        "user_input": "How does the knowledge graph answer my query?"
    }
    qa_result = qa_crew.crew().kickoff(inputs=qa_inputs)
    print("QuestionAnsweringCrew result:")
    print(qa_result)
    
    cal_crew = GoogleCalendarCrew()
    cal_inputs = {
        "events_date": "2024-03-20"
    }
    cal_result = cal_crew.crew().kickoff(inputs=cal_inputs)
    print("GoogleCalendarCrew result:")
    print(cal_result)
