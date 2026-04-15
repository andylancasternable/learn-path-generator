import json
import os
import re
from pathlib import Path
from typing import List, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from src.analyzers import ContentAnalyzer
from src.config import settings
from src.loaders import EPUBLoader, PDFLoader
from src.main import discover_subject_folders
from src.models import Ebook

TOPIC_OVERLAP_THRESHOLD = 0.25


class AnalyzedBook(TypedDict):
    title: str
    file_name: str
    topics: List[str]
    summary: str


class GroupRecommendation(TypedDict):
    subject: str
    books: List[str]
    reason: str
    shared_topics: List[str]


def _collect_books(ebooks_dir: Path) -> List[AnalyzedBook]:
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()
    analyzed_books: List[AnalyzedBook] = []

    subjects = discover_subject_folders(ebooks_dir)
    for _, _, ebook_files in subjects:
        for ebook_path in ebook_files:
            if ebook_path.suffix.lower() == ".pdf":
                content, metadata = pdf_loader.load(str(ebook_path))
                ebook_path = Path(metadata.get("file_path", str(ebook_path)))
            else:
                content, metadata = epub_loader.load(str(ebook_path))

            if not content:
                continue

            ebook = Ebook(
                title=metadata.get("title") or ebook_path.stem,
                author=metadata.get("author", "Unknown"),
                file_path=str(ebook_path),
                difficulty_level="intermediate",
                total_pages=metadata.get("pages"),
            )
            ebook = analyzer.analyze(ebook, content)
            analyzed_books.append(
                {
                    "title": ebook.title,
                    "file_name": ebook_path.name,
                    "topics": [topic.name for topic in ebook.topics],
                    "summary": ebook.summary or "",
                }
            )

    return analyzed_books


def _topic_overlap(topics_a: List[str], topics_b: List[str]) -> float:
    set_a = {topic.strip().casefold() for topic in topics_a if topic.strip()}
    set_b = {topic.strip().casefold() for topic in topics_b if topic.strip()}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _fallback_groupings(books: List[AnalyzedBook]) -> List[GroupRecommendation]:
    groups: List[GroupRecommendation] = []
    used_indexes = set()

    for index, book in enumerate(books):
        if index in used_indexes:
            continue

        current_group = [book]
        used_indexes.add(index)
        current_topics = list(book.get("topics", []))

        for candidate_index, candidate in enumerate(books):
            if candidate_index in used_indexes:
                continue
            if _topic_overlap(current_topics, candidate.get("topics", [])) >= TOPIC_OVERLAP_THRESHOLD:
                current_group.append(candidate)
                current_topics.extend(candidate.get("topics", []))
                used_indexes.add(candidate_index)

        unique_topics = sorted(
            {
                topic
                for entry in current_group
                for topic in entry.get("topics", [])
                if topic
            }
        )
        groups.append(
            {
                "subject": unique_topics[0] if unique_topics else "General Studies",
                "books": [entry.get("title", "") for entry in current_group],
                "reason": "Grouped by overlapping extracted topics.",
                "shared_topics": unique_topics[:5],
            }
        )

    return groups


def _group_books_with_claude(books: List[AnalyzedBook]) -> List[GroupRecommendation]:
    if not books:
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    if not api_key:
        return _fallback_groupings(books)

    llm = ChatAnthropic(
        api_key=api_key,
        model_name=settings.model_name,
        temperature=0.2,
        max_tokens=settings.max_tokens,
    )

    grouping_prompt = ChatPromptTemplate.from_template(
        """You are organizing a digital ebook library.

Group these books into logical subject clusters using semantic similarity and topic overlap.
Return ONLY valid JSON in this format:
{{
  "groups": [
    {{
      "subject": "Subject Name",
      "books": ["Book A", "Book B"],
      "reason": "Why these books belong together",
      "shared_topics": ["topic1", "topic2"]
    }}
  ]
}}

Books:
{books_json}
"""
    )

    try:
        chain = grouping_prompt | llm
        response = chain.invoke({"books_json": json.dumps(books, indent=2)})
        content = response.content
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in Claude response")
        parsed = json.loads(json_match.group(0))
        groups = parsed.get("groups", [])
        return groups if isinstance(groups, list) else _fallback_groupings(books)
    except Exception as error:
        print(f"⚠️  Claude grouping fallback: {error}")
        return _fallback_groupings(books)


def main() -> None:
    print("📚 Book Discovery & Auto-Grouping Analysis\n")
    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)

    books = _collect_books(ebooks_dir)
    if not books:
        print("⚠️  No loadable ebooks found in ./ebooks")
        return

    print(f"🔍 Analyzed {len(books)} book(s)\n")
    for book in books:
        topics = ", ".join(book["topics"]) if book["topics"] else "No topics extracted"
        print(f"- {book['title']} ({book['file_name']})")
        print(f"  Topics: {topics}")

    print("\n🧠 Suggested Subject Groupings\n")
    groups = _group_books_with_claude(books)
    for index, group in enumerate(groups, start=1):
        print(f"{index}. {group.get('subject', 'General')}")
        print(f"   Books: {', '.join(group.get('books', []))}")
        shared_topics = group.get("shared_topics", [])
        if shared_topics:
            print(f"   Shared topics: {', '.join(shared_topics)}")
        print(f"   Why: {group.get('reason', 'Similar topics and learning progression.')}\n")


if __name__ == "__main__":
    main()
