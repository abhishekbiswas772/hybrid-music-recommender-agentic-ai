from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from typing import Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from models.models import MusicalContext
from configs.configurations import config
import json


class MusicalContextTool(BaseTool):
    name: str = "musical_context_extractor"
    description: str = "Extracts musical context, activity, and preferences from user input"

    def _run(self, user_input: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        llm = config.llm
        parser = PydanticOutputParser(pydantic_object=MusicalContext)
        
        prompt = PromptTemplate(
            template="""
            You are a music expert and curator. Extract musical context and preferences from this request:

            Request: "{user_input}"

            Analyze:
            - What activity or situation is this for?
            - What energy level is needed? (0.0 = very low energy, 1.0 = very high energy)
            - Social context (alone, with others, party, intimate, etc.)
            - Time-related context (morning, evening, late night, etc.)
            - Musical preferences implied (any specific styles mentioned?)
            - Genre hints from language used (electronic, acoustic, classical, etc.)
            - Sonic characteristics desired (warm, bright, heavy, light, etc.)
            - Preferred instruments (if any mentioned or implied)

            {format_instructions}
            """,
            input_variables=["user_input"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | llm | StrOutputParser()
        
        try:
            result = chain.invoke({"user_input": user_input})
            parsed_result = parser.parse(result)
            return json.dumps(parsed_result.model_dump())
            
        except Exception as e:
            print(f"Context extraction failed: {e}")
            try:
                fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=llm)
                result = chain.invoke({"user_input": user_input})
                parsed_result = fixing_parser.parse(result)
                return json.dumps(parsed_result.model_dump())
            except Exception as e2:
                print(f"Fixing parser also failed: {e2}")
                fallback_context = MusicalContext(
                    activity_type="general",
                    energy_preference=0.5,
                    familiarity_preference=0.5,
                    social_context="unknown",
                    temporal_context="anytime",
                    genre_hints=["general"],
                    sonic_descriptors=["pleasant"],
                    instrumental_preferences=["any"]
                )
                return json.dumps(fallback_context.model_dump())

    async def _arun(self, user_input: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        llm = config.llm
        parser = PydanticOutputParser(pydantic_object=MusicalContext)
        
        prompt = PromptTemplate(
            template="""
            You are a music expert and curator. Extract musical context and preferences from this request:

            Request: "{user_input}"

            Analyze:
            - What activity or situation is this for?
            - What energy level is needed? (0.0 = very low energy, 1.0 = very high energy)
            - Social context (alone, with others, party, intimate, etc.)
            - Time-related context (morning, evening, late night, etc.)
            - Musical preferences implied (any specific styles mentioned?)
            - Genre hints from language used (electronic, acoustic, classical, etc.)
            - Sonic characteristics desired (warm, bright, heavy, light, etc.)
            - Preferred instruments (if any mentioned or implied)

            {format_instructions}
            """,
            input_variables=["user_input"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | llm | StrOutputParser()
        
        try:
            result = await chain.ainvoke({"user_input": user_input})
            parsed_result = parser.parse(result)
            return json.dumps(parsed_result.model_dump())
            
        except Exception as e:
            print(f"Async context extraction failed: {e}")
            fallback_context = MusicalContext(
                activity_type="general",
                energy_preference=0.5,
                familiarity_preference=0.5,
                social_context="unknown",
                temporal_context="anytime",
                genre_hints=["general"],
                sonic_descriptors=["pleasant"],
                instrumental_preferences=["any"]
            )
            return json.dumps(fallback_context.model_dump())

# def test_context_tool():
#     tool = MusicalContextTool()
#     test_inputs = [
#         "I need focus music for deep programming work",
#         "Something energetic for my morning workout",
#         "Chill vibes for a late night study session",
#         "Party music for a birthday celebration",
#         "I want something like watching the sunrise from a mountain - peaceful but uplifting",
#         "Need background music for a romantic dinner with my partner",
#         "Something to help me fall asleep, maybe with piano",
#         "High-energy electronic music for gaming"
#     ]
    
#     for i, user_input in enumerate(test_inputs, 1):
#         print(f"\n--- Context Test {i} ---")
#         print(f"Input: {user_input}")
#         print("Analyzing...")
        
#         try:
#             result = tool.invoke(user_input)
#             print("Raw result:", result)
            
#             parsed = json.loads(result)
#             print("Formatted Analysis:")
#             print(f"Activity: {parsed['activity_type']}")
#             print(f"Energy Level: {parsed['energy_preference']}")
#             print(f"Social Context: {parsed['social_context']}")
#             print(f"Time Context: {parsed['temporal_context']}")
#             print(f"Genre Hints: {', '.join(parsed['genre_hints'])}")
#             print(f"Sound Descriptors: {', '.join(parsed['sonic_descriptors'])}")
#             print(f"Instruments: {', '.join(parsed['instrumental_preferences'])}")
#             print(f"Familiarity Preference: {parsed['familiarity_preference']}")
            
#         except Exception as e:
#             print(f"Context tool error: {e}")

# async def test_async_context():
#     print("\nTesting Async Context Extraction")
#     print("=" * 40)
#     tool = MusicalContextTool()
#     user_input = "I need something calming for meditation and mindfulness practice"
#     try:
#         result = await tool.ainvoke(user_input)
#         parsed = json.loads(result)
        
#         print(f"Input: {user_input}")
#         print("Async Analysis:")
#         for key, value in parsed.items():
#             print(f"  {key}: {value}")
            
#     except Exception as e:
#         print(f"Async test error: {e}")

# if __name__ == "__main__":
#     print("Testing Fixed Musical Context Tool")
#     print("=" * 50)
#     test_context_tool()
#     import asyncio
#     asyncio.run(test_async_context())
    
#     print("\n All tests completed!")