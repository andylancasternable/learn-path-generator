from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from src.models import Chapter, Concept, Ebook, Topic
from src.config import settings
import json
import re
import os


class ContentAnalyzer:
    """Analyzes ebook content to extract topics and concepts"""
    MIN_PAGES_PER_CHAPTER = 1
    
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
    ],
    "chapters": [
        {{
            "title": "Chapter title",
            "chapter_number": 1,
            "start_page": 1,
            "end_page": 20,
            "sections": ["section A", "section B"],
            "concepts": ["concept A", "concept B"]
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

            for chapter_data in analysis.get("chapters", []):
                ebook.chapters.append(
                    Chapter(
                        title=chapter_data.get("title", ""),
                        chapter_number=chapter_data.get("chapter_number"),
                        start_page=chapter_data.get("start_page"),
                        end_page=chapter_data.get("end_page"),
                        sections=chapter_data.get("sections", []),
                        concepts=chapter_data.get("concepts", []),
                    )
                )

            if not ebook.chapters:
                ebook.chapters = self._extract_chapters_from_text(content, ebook.total_pages)
            
            return ebook
        
        except Exception as e:
            print(f"Error analyzing ebook {ebook.title}: {e}")
            if not ebook.chapters:
                ebook.chapters = self._extract_chapters_from_text(content, ebook.total_pages)
            return ebook

    def _extract_chapters_from_text(self, content: str, total_pages: int | None = None) -> list[Chapter]:
        """Fallback chapter extraction from plain text headings."""
        chapter_lines = []
        for raw_line in content.splitlines():
            line = " ".join(raw_line.split()).strip()
            if not line:
                continue
            if re.match(r"^(chapter|ch\.?)\s+\d+[:.\-\s]+", line, re.IGNORECASE):
                chapter_lines.append(line)
            elif re.match(r"^\d+(\.\d+)*\s+[A-Za-z].+$", line) and " " in line:
                chapter_lines.append(line)

        if not chapter_lines:
            return []

        unique_lines = []
        seen = set()
        for line in chapter_lines:
            lowered = line.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            unique_lines.append(line)

        chapter_count = len(unique_lines)
        pages_per_chapter = None
        if total_pages and chapter_count > 0:
            pages_per_chapter = max(self.MIN_PAGES_PER_CHAPTER, int(total_pages / chapter_count))
        chapters: list[Chapter] = []
        for index, line in enumerate(unique_lines, start=1):
            title = re.sub(r"^(chapter|ch\.?)\s+\d+[:.\-\s]*", "", line, flags=re.IGNORECASE).strip()
            title = re.sub(r"^\d+(\.\d+)*\s+", "", title).strip() or line
            start_page = None
            end_page = None
            if pages_per_chapter:
                start_page = ((index - 1) * pages_per_chapter) + 1
                end_page = start_page + pages_per_chapter - 1
                if total_pages and index == chapter_count:
                    end_page = total_pages
            chapters.append(
                Chapter(
                    title=title,
                    chapter_number=index,
                    start_page=start_page,
                    end_page=end_page,
                    sections=[],
                    concepts=[],
                )
            )
        return chapters
