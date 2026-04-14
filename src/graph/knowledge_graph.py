from typing import List, Dict, Set, Optional
from src.models import Ebook, Topic, Concept
import networkx as nx


class KnowledgeGraph:
    """Builds and manages a knowledge graph of ebooks and concepts"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.ebooks: Dict[str, Ebook] = {}
        self.concept_to_ebooks: Dict[str, Set[str]] = {}
        self.topic_to_concepts: Dict[str, List[str]] = {}
    
    def add_ebook(self, ebook: Ebook) -> None:
        """Add an ebook to the knowledge graph"""
        self.ebooks[ebook.title] = ebook
        
        # Add ebook node
        self.graph.add_node(
            ebook.title,
            type="ebook",
            difficulty=ebook.difficulty_level,
            author=ebook.author
        )
        
        # Add topics and concepts
        for topic in ebook.topics:
            topic_key = f"{ebook.title}:{topic.name}"
            self.graph.add_node(topic_key, type="topic", name=topic.name)
            self.graph.add_edge(ebook.title, topic_key, relationship="contains_topic")
            
            for concept in topic.concepts:
                concept_key = f"{concept.name}"
                
                if concept_key not in self.concept_to_ebooks:
                    self.concept_to_ebooks[concept_key] = set()
                self.concept_to_ebooks[concept_key].add(ebook.title)
                
                # Add concept node if not exists
                if not self.graph.has_node(concept_key):
                    self.graph.add_node(
                        concept_key,
                        type="concept",
                        difficulty=concept.difficulty_level
                    )
                
                # Add edges
                self.graph.add_edge(topic_key, concept_key, relationship="teaches")
                
                # Add prerequisite edges
                for prereq in concept.prerequisites:
                    if not self.graph.has_node(prereq):
                        self.graph.add_node(prereq, type="concept")
                    self.graph.add_edge(prereq, concept_key, relationship="prerequisite_for")
    
    def build_from_ebooks(self, ebooks: List[Ebook]) -> None:
        """Build knowledge graph from a list of ebooks"""
        for ebook in ebooks:
            self.add_ebook(ebook)
    
    def get_ebook_for_concept(self, concept_name: str) -> List[str]:
        """Get ebooks that teach a specific concept"""
        return list(self.concept_to_ebooks.get(concept_name, set()))
    
    def get_prerequisites(self, concept_name: str) -> List[str]:
        """Get prerequisites for a concept"""
        prerequisites = []
        for predecessor in self.graph.predecessors(concept_name):
            if self.graph[predecessor][concept_name].get("relationship") == "prerequisite_for":
                prerequisites.append(predecessor)
        return prerequisites
    
    def get_dependents(self, concept_name: str) -> List[str]:
        """Get concepts that depend on this one"""
        dependents = []
        for successor in self.graph.successors(concept_name):
            if self.graph[concept_name][successor].get("relationship") == "prerequisite_for":
                dependents.append(successor)
        return dependents
    
    def get_related_concepts(self, concept_name: str, depth: int = 2) -> List[str]:
        """Get related concepts within a certain depth"""
        related = set()
        
        # BFS to find related concepts
        visited = set()
        queue = [(concept_name, 0)]
        
        while queue:
            node, current_depth = queue.pop(0)
            if node in visited or current_depth > depth:
                continue
            
            visited.add(node)
            if node != concept_name and node not in related:
                related.add(node)
            
            for neighbor in self.graph.neighbors(node):
                if neighbor not in visited:
                    queue.append((neighbor, current_depth + 1))
        
        return list(related)
    
    def get_all_ebooks(self) -> List[Ebook]:
        """Get all ebooks in the knowledge graph"""
        return list(self.ebooks.values())
    
    def get_all_concepts(self) -> List[str]:
        """Get all unique concepts in the knowledge graph"""
        return [node for node, attr in self.graph.nodes(data=True) 
                if attr.get("type") == "concept"]
