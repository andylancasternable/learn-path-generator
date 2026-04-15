from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from src.models import LearningPath, PathStep
from src.graph.knowledge_graph import KnowledgeGraph
from src.config import settings
import json
import re
import os


class PathGenerator:
    """Generates personalized learning paths based on goals"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph
        api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
        self.llm = ChatAnthropic(
            api_key=api_key,
            model_name=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        
        self.path_prompt = ChatPromptTemplate.from_template(
            """You are a learning path expert. Based on the available ebooks and the user's learning goal, 
create an optimal learning path sequence.

Available Ebooks:
{ebooks_info}

Learning Goal: {goal}

Please provide a JSON response with the following structure:
{{
    "path_steps": [
        {{
            "order": 1,
            "ebook_title": "Ebook Name",
            "topics": ["topic1", "topic2"],
            "estimated_hours": 5.0,
            "rationale": "Why this book/topic is important for the goal"
        }}
    ],
    "total_estimated_hours": 50.0,
    "recommendations": ["recommendation1", "recommendation2"]
}}

Respond with ONLY valid JSON, no additional text."""
        )
    
    def generate(self, learning_goal: str, difficulty_preference: str = "intermediate") -> LearningPath:
        """Generate a learning path for a specific goal"""
        try:
            # Prepare ebook information
            ebooks_info = self._format_ebooks_info(difficulty_preference)
            
            chain = self.path_prompt | self.llm
            
            response = chain.invoke({
                "ebooks_info": ebooks_info,
                "goal": learning_goal
            })
            
            content = response.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group(0)
            path_data = json.loads(json_str)
            
            # Create learning path
            steps = [
                PathStep(
                    order=step["order"],
                    ebook_title=step["ebook_title"],
                    topics=step.get("topics", []),
                    estimated_hours=step.get("estimated_hours", 5.0),
                    rationale=step.get("rationale", "")
                )
                for step in path_data.get("path_steps", [])
            ]
            
            learning_path = LearningPath(
                goal=learning_goal,
                ebooks_count=len(steps),
                estimated_total_hours=path_data.get("total_estimated_hours", 0.0),
                steps=steps
            )
            
            return learning_path
        
        except Exception as e:
            print(f"Error generating learning path: {e}")
            return LearningPath(goal=learning_goal, ebooks_count=0, estimated_total_hours=0.0, steps=[])
    
    def _format_ebooks_info(self, difficulty_preference: str = "intermediate") -> str:
        """Format ebook information for the LLM"""
        ebooks = self.kg.get_all_ebooks()
        
        formatted_info = []
        for ebook in ebooks:
            topics_str = ", ".join([t.name for t in ebook.topics])
            formatted_info.append(
                f"- Title: {ebook.title}\n"
                f"  Author: {ebook.author}\n"
                f"  Difficulty: {ebook.difficulty_level}\n"
                f"  Topics: {topics_str}\n"
                f"  Pages: {ebook.total_pages or 'Unknown'}"
            )
        
        return "\n".join(formatted_info)
