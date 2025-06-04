from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from typing import Optional
from models.models import MoodAnalysis
from configs.configurations import config
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain_core.output_parsers import StrOutputParser
import json


class MoodAnalysisTool(BaseTool):
    name: str = "mood_analyzer"
    description: str = "Analyzes user's emotional state and mood from natural language input"

    def _run(
        self, 
        user_input: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        llm = config.llm
        parser = PydanticOutputParser(pydantic_object=MoodAnalysis)
        
        prompt = PromptTemplate(
            template="""
            You are an expert in human psychology and emotion. Analyze the emotional state from this text:

            Text: "{user_input}"

            Consider:
            - Explicit emotional words
            - Implicit emotional cues
            - Context that influences mood
            - Psychological undertones
            - Energy levels and arousal

            {format_instructions}
            """,
            input_variables=["user_input"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()
            }
        )
        chain = prompt | llm | StrOutputParser()
        
        try:
            result = chain.invoke({"user_input": user_input})
            parsed_result = parser.parse(result)
            return json.dumps(parsed_result.model_dump())
            
        except Exception as e:
            print(f"First parsing failed: {e}")
            try:
                fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=llm)
                result = chain.invoke({"user_input": user_input})
                parsed_result = fixing_parser.parse(result)
                return json.dumps(parsed_result.model_dump())
                
            except Exception as e2:
                print(f"Fixing parser also failed: {e2}")
                fallback_mood = MoodAnalysis(
                    primary_emotion="neutral",
                    intensity=0.5,
                    valence=0.0,
                    arousal=0.5,
                    dominance=0.5,
                    mood_descriptors=["unknown"],
                    context_factors=["analysis_failed"]
                )
                return json.dumps(fallback_mood.model_dump())

    async def _arun(
        self, 
        user_input: str, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Async version of mood analysis"""
        llm = config.llm
        parser = PydanticOutputParser(pydantic_object=MoodAnalysis)
        
        prompt = PromptTemplate(
            template="""
            You are an expert in human psychology and emotion. Analyze the emotional state from this text:

            Text: "{user_input}"

            Consider:
            - Explicit emotional words
            - Implicit emotional cues
            - Context that influences mood
            - Psychological undertones
            - Energy levels and arousal

            {format_instructions}
            """,
            input_variables=["user_input"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()
            }
        )
        chain = prompt | llm | StrOutputParser()
        
        try:
            result = await chain.ainvoke({"user_input": user_input})
            parsed_result = parser.parse(result)
            return json.dumps(parsed_result.model_dump())
            
        except Exception as e:
            print(f"Async parsing failed: {e}")
            fallback_mood = MoodAnalysis(
                primary_emotion="neutral",
                intensity=0.5,
                valence=0.0,
                arousal=0.5,
                dominance=0.5,
                mood_descriptors=["unknown"],
                context_factors=["analysis_failed"]
            )
            return json.dumps(fallback_mood.model_dump())



# def test_mood_tool():
#     tool = MoodAnalysisTool()
    
#     test_inputs = [
#         "I've been feeling quite low and anxious lately. Nothing seems to cheer me up.",
#         "I'm so excited for the weekend! Everything is going great!",
#         "Feeling pretty neutral today, just going through the motions.",
#         "I need something that feels like watching the sunrise from a mountaintop"
#     ]
    
#     for i, user_input in enumerate(test_inputs, 1):
#         print(f"\n--- Test {i} ---")
#         print(f"Input: {user_input}")
#         print("Analyzing...")
        
#         try:
#             result = tool.invoke(user_input)
#             print("Result:", result)
#             parsed = json.loads(result)
#             print("Formatted result:")
#             for key, value in parsed.items():
#                 print(f"  {key}: {value}")
                
#         except Exception as e:
#             print(f"Error: {e}")


# if __name__ == "__main__":
#     print("Testing Modern LangChain Music Tools")
#     print("=" * 70)
#     test_mood_tool()
