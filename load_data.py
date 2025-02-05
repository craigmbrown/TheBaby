from langchain.docstore.document import Document
from langchain_community.document_loaders import TextLoader
from typing import List, Optional

class TextProcessor:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load_text(self) -> Optional[List[Document]]:
        try:
            loader = TextLoader(self.file_path)
            pages = loader.load()

            text = "\n".join([doc.page_content for doc in pages])
            documents = [Document(page_content=text,metadata={"source": self.file_path})]
            return documents
        except Exception as e:
            print(f"Failed to load text: {str(e)}")
            return None
