from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from src.models import Ebook, Topic, Concept
from src.config import settings
import json
import re
import os


class ContentAnalyzer:
    """Analyzes ebook content to extract topics and concepts"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
        self.llm = ChatAnthropic(
            api_key=api_key,
            model_name=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        
        self.analysis_prompt = ChatPromptTemplate.from_template(
            """Analyze the following ebook content and extract structured learning information.

Ebook Title: {title}
Ebook Author: {author}

Content Preview (first 3000 chars):
{content_preview}

Extract the following in JSON format:
{{
    "summary": "2-3 sentence summary of the book",
    "difficulty_level": "beginner|intermediate|advanced",
    "topics": [
        {{
            "name": "Topic Name",
            "description": "Brief description",
            "concepts": [
                {{
                    "name": "Concept Name",
                    "description": "What this concept covers",
                    "difficulty_level": "beginner|intermediate|advanced",
                    "prerequisites": ["Concept A", "Concept B"]
                }}
            ]
        }}
    ]
}}

Respond with ONLY valid JSON, no additional text."""
        )
    
    def analyze(self, ebook: Ebook, content: str) -> Ebook:
        """Analyze ebook content and populate topics/concepts"""
        try:
            # Limit content preview to avoid token limits
            content_preview = content[:3000]
            
            chain = self.analysis_prompt | self.llm
            
            response = chain.invoke({
                "title": ebook.title,
                "author": ebook.author,
                "content_preview": content_preview
            })
            
            content_str = response.content
            json_match = re.search(r'\{.*\}', content_str, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group(0)
            analysis = json.loads(json_str)
            
            # Update ebook with analysis
            ebook.summary = analysis.get("summary", "")
            ebook.difficulty_level = analysis.get("difficulty_level", "intermediate")
            
            # Parse topics and concepts
            for topic_data in analysis.get("topics", []):
                concepts = [
                    Concept(
                        name=c["name"],
                        difficulty_level=c.get("difficulty_level", "intermediate"),
                        prerequisites=c.get("prerequisites", []),
                        description=c.get("description", "")
                    )
                    for c in topic_data.get("concepts", [])
                ]
                
                topic = Topic(
                    name=topic_data["name"],
                    description=topic_data.get("description", ""),
                    concepts=concepts
                )
                ebook.topics.append(topic)
            
            return ebook
        
        except Exception as e:
            print(f"Error analyzing ebook {ebook.title}: {e}")
            return ebook
