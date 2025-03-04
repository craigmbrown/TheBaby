from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import TavilySearchTool, URLsToGraphTool, QuestionAnsweringTool, GoogleCalendarTool
from dotenv import load_dotenv
load_dotenv()


llm = LLM(model="openai/gpt-4o-mini", timeout=600)


tavily_search = TavilySearchTool()
urls_to_graph = URLsToGraphTool()
question_answering = QuestionAnsweringTool()
google_calendar = GoogleCalendarTool()

###############################################################################
# Crew 1: Web Search Crew - Contains a single agent for web search.
###############################################################################
@CrewBase
class WebSearchCrew:
    agents_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/web_search_agents.yaml'
    tasks_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/web_search_tasks.yaml'

    @agent
    def web_search_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["web_search_assistant"],
            tools=[tavily_search],
            verbose=True,
            llm=llm,
        )

    @task
    def web_search_assistant_task(self) -> Task:
        return Task(
            config=self.tasks_config["web_search_assistant_task"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,   # Automatically created by the @agent decorator
            tasks=[self.web_search_assistant_task()],             # No tasks defined, running agent as is
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Crew 2: Email URLs-to-Graph Crew - Contains a single agent for URL-to-Graph conversion.
###############################################################################
@CrewBase
class EmailGraphCrew:
    agents_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/email_graph_agents.yaml'
    tasks_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/email_graph_tasks.yaml'

    @agent
    def email_urls_to_graph_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["email_urls_to_graph_assistant"],
            tools=[urls_to_graph],
            verbose=True,
            llm=llm,
        )

    @task
    def email_urls_to_graph_assistant_task(self) -> Task:
        return Task(
            config=self.tasks_config["email_urls_to_graph_assistant_task"],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[self.email_urls_to_graph_assistant_task()],  
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Crew 3: Question Answering Crew - Contains a single agent for question answering.
###############################################################################
@CrewBase
class QuestionAnsweringCrew:
    agents_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/qa_agents.yaml'
    tasks_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/qa_tasks.yaml'

    @agent
    def question_answering_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["question_answering_assistant"],
            tools=[question_answering],
            verbose=True,
            llm=llm,
        )

    @task
    def question_answering_assistant_task(self) -> Task:
        return Task(
            config=self.tasks_config["question_answering_assistant_task"],
        )
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[self.question_answering_assistant_task()],  
            process=Process.sequential,
            verbose=True,
        )

###############################################################################
# Crew 4: Google Calendar Crew - Contains a single agent for calendar retrieval.
###############################################################################
@CrewBase
class GoogleCalendarCrew:
    agents_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/calendar_agents.yaml'
    tasks_config = '/home/babyproject418/graphRAG/agentic-system/assistant_crew/src/assistant_crew/config/calendar_tasks.yaml'

    @agent
    def google_calendar_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["google_calendar_assistant"],
            tools=[google_calendar],
            verbose=True,
            llm=llm,
        )

    @task
    def google_calendar_assistant_task(self) -> Task:
        return Task(
            config=self.tasks_config["google_calendar_assistant_task"],
        )
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=[self.google_calendar_assistant_task()],  
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
