from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class Config:
    llm = ChatOpenAI(temperature=0.3, model="gpt-3.5-turbo",)


config = Config()