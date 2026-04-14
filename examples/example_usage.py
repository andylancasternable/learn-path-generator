"""
Example usage of the Learning Path Generator with sample ebooks
"""
from src.loaders import PDFLoader, EPUBLoader
from src.analyzers import ContentAnalyzer
from src.graph import KnowledgeGraph, PathGenerator
from src.models import Ebook, Topic, Concept


def example_with_sample_data():
    """Example using hardcoded sample ebook data (no actual files needed)"""
    
    print("🎓 Learning Path Generator - Sample Data Example\n")
    
    # Create sample ebooks with predefined data
    python_basics = Ebook(
        title="Python Programming Basics",
        author="John Doe",
        file_path="python_basics.pdf",
        difficulty_level="beginner",
        total_pages=250,
        summary="Introduction to Python programming",
        topics=[
            Topic(
                name="Variables and Data Types",
                concepts=[
                    Concept(
                        name="Variables",
                        difficulty_level="beginner",
                        prerequisites=[]
                    ),
                    Concept(
                        name="Strings",
                        difficulty_level="beginner",
                        prerequisites=["Variables"]
                    )
                ]
            ),
            Topic(
                name="Control Flow",
                concepts=[
                    Concept(
                        name="If Statements",
                        difficulty_level="beginner",
                        prerequisites=["Variables"]
                    ),
                    Concept(
                        name="Loops",
                        difficulty_level="beginner",
                        prerequisites=["If Statements"]
                    )
                ]
            )
        ]
    )
    
    data_science = Ebook(
        title="Introduction to Data Science",
        author="Jane Smith",
        file_path="data_science.pdf",
        difficulty_level="intermediate",
        total_pages=350,
        summary="Fundamentals of data science and analysis",
        topics=[
            Topic(
                name="Data Analysis",
                concepts=[
                    Concept(
                        name="Pandas",
                        difficulty_level="intermediate",
                        prerequisites=["Python Basics"]
                    ),
                    Concept(
                        name="Data Cleaning",
                        difficulty_level="intermediate",
                        prerequisites=["Pandas"]
                    )
                ]
            ),
            Topic(
                name="Visualization",
                concepts=[
                    Concept(
                        name="Matplotlib",
                        difficulty_level="intermediate",
                        prerequisites=["Pandas"]
                    )
                ]
            )
        ]
    )
    
    ml_basics = Ebook(
        title="Machine Learning Fundamentals",
        author="Bob Johnson",
        file_path="ml_basics.pdf",
        difficulty_level="advanced",
        total_pages=400,
        summary="Core concepts and algorithms in machine learning",
        topics=[
            Topic(
                name="Supervised Learning",
                concepts=[
                    Concept(
                        name="Linear Regression",
                        difficulty_level="intermediate",
                        prerequisites=["Statistics"]
                    ),
                    Concept(
                        name="Classification",
                        difficulty_level="advanced",
                        prerequisites=["Linear Regression"]
                    )
                ]
            )
        ]
    )
    
    # Build knowledge graph
    print("🔗 Building knowledge graph from sample data...\n")
    kg = KnowledgeGraph()
    kg.build_from_ebooks([python_basics, data_science, ml_basics])
    
    print(f"✅ Loaded {len(kg.get_all_ebooks())} ebooks")
    print(f"✅ {len(kg.get_all_concepts())} concepts indexed\n")
    
    # Display ebooks
    print("📚 Available Ebooks:")
    for ebook in kg.get_all_ebooks():
        print(f"  - {ebook.title} ({ebook.difficulty_level})")
        for topic in ebook.topics:
            print(f"    • {topic.name}: {len(topic.concepts)} concepts")
    
    print("\n" + "="*60 + "\n")
    
    # Generate learning path
    print("🎯 Generating Learning Paths:\n")
    
    path_generator = PathGenerator(kg)
    
    goals = [
        "Learn machine learning starting from Python basics",
        "Become proficient in data analysis and visualization"
    ]
    
    for goal in goals:
        print(f"Goal: {goal}")
        path = path_generator.generate(goal)
        
        if path.steps:
            print(f"  Recommended learning steps:")
            for step in path.steps:
                print(f"    {step.order}. {step.ebook_title}")
                print(f"       Estimated: {step.estimated_hours}h")
            print(f"  Total estimated time: {path.estimated_total_hours} hours\n")
        else:
            print(f"  ⚠️  Unable to generate path with current data\n")


if __name__ == "__main__":
    example_with_sample_data()
