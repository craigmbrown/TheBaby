from langchain.docstore.document import Document
from langchain_community.document_loaders import TextLoader
from typing import List, Optional
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
import os 
from dotenv import load_dotenv
load_dotenv()

class TextProcessor:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load_text(self) -> Optional[List[Document]]:
        try:
            loader = TextLoader(self.file_path)
            pages = loader.load()

            text = "\n".join([doc.page_content for doc in pages])
            documents = [Document(page_content=text,metadata={"source": self.file_path})]
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            docs = text_splitter.split_documents(documents)

            embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
            db = Neo4jVector.from_documents(docs, embeddings, url=os.getenv("NEO4J_URI"), username=os.getenv("NEO4J_USERNAME"), password=os.getenv("NEO4J_PASSWORD"))

            return documents
        except Exception as e:
            print(f"Failed to load text: {str(e)}")
            return None
    
    def load_urls(self, urls: List[str]) -> Optional[List[Document]]:
        """Load URLs and convert to text."""
        pass
