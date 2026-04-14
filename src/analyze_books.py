import json
import os
import re
from pathlib import Path
from typing import Dict, List, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from src.analyzers import ContentAnalyzer
from src.book_discovery import list_ebook_files
from src.config import settings
from src.ebook_pipeline import load_and_analyze_ebooks
from src.loaders import EPUBLoader, PDFLoader
from src.models import Ebook


class BookGroupingAnalyzer:
    """Analyzes books and suggests logical subject groupings."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
        self.llm = ChatAnthropic(
            api_key=api_key,
            model_name=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
        self.grouping_prompt = ChatPromptTemplate.from_template(
            """You are an expert learning librarian.
Given the analyzed books below, suggest logical subject groups by semantic similarity and topic overlap.

Books:
{books_info}

Respond with ONLY valid JSON:
{{
  "groups": [
    {{
      "name": "Group Name",
      "books": ["book1.pdf", "book2.epub"],
      "reason": "Why these books belong together"
    }}
  ]
}}"""
        )

    def suggest_groups(self, ebooks: List[Ebook]) -> List["BookGroup"]:
        """Use Claude to suggest groups. Falls back to first-topic grouping if needed."""
        try:
            books_info = "\n".join(
                [
                    (
                        f"- File: {Path(ebook.file_path).name}\n"
                        f"  Title: {ebook.title}\n"
                        f"  Summary: {ebook.summary or 'N/A'}\n"
                        f"  Topics: {', '.join(topic.name for topic in ebook.topics) or 'N/A'}"
                    )
                    for ebook in ebooks
                ]
            )
            chain = self.grouping_prompt | self.llm
            response = chain.invoke({"books_info": books_info})
            content = response.content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in grouping response")

            group_data = json.loads(json_match.group(0))
            groups = group_data.get("groups", [])
            return groups if isinstance(groups, list) else []
        except Exception as exc:
            print(f"⚠️  Could not generate semantic groups from Claude: {exc}")
            return self._fallback_groups(ebooks)

    @staticmethod
    def _fallback_groups(ebooks: List[Ebook]) -> List["BookGroup"]:
        grouped: Dict[str, List[Ebook]] = {}
        for ebook in ebooks:
            if ebook.topics:
                group_name = ebook.topics[0].name
            else:
                group_name = "General"
            grouped.setdefault(group_name, []).append(ebook)

        groups: List[BookGroup] = []
        for group_name, group_ebooks in grouped.items():
            groups.append(
                {
                    "name": group_name,
                    "books": [Path(ebook.file_path).name for ebook in group_ebooks],
                    "reason": "Grouped by primary extracted topic.",
                }
            )
        return groups


class BookGroup(TypedDict):
    name: str
    books: List[str]
    reason: str


def main():
    print("📚 Book Analysis & Grouping Suggestions\n")

    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)

    ebook_paths = list_ebook_files(ebooks_dir)
    if not ebook_paths:
        print("⚠️  No ebooks found in ./ebooks directory")
        print("Please add PDF or EPUB files to get started.\n")
        return

    print(f"📚 Found {len(ebook_paths)} ebook(s) for analysis\n")

    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()

    loaded_ebooks = load_and_analyze_ebooks(
        ebook_paths=ebook_paths,
        pdf_loader=pdf_loader,
        epub_loader=epub_loader,
        analyzer=analyzer,
    )

    if not loaded_ebooks:
        print("❌ No ebooks could be loaded")
        return

    grouping_analyzer = BookGroupingAnalyzer()
    groups = grouping_analyzer.suggest_groups(loaded_ebooks)

    if not groups:
        print("⚠️  Could not suggest groups")
        return

    print("\nSuggested Subject Groups:")
    for index, group in enumerate(groups, start=1):
        print(f"  {index}. {group.get('name', 'Unnamed Group')}")
        for book_name in group.get("books", []):
            print(f"     - {book_name}")
        print(f"     Reason: {group.get('reason', 'N/A')}\n")


if __name__ == "__main__":
    main()
