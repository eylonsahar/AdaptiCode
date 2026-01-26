"""
Prerequisite graph for concept dependencies.
"""
from typing import Dict, List, Set, Optional
from backend.data.models import ConceptStatus


class PrerequisiteGraph:
    """
    Manages the prerequisite relationships between concepts.
    
    The dependency structure for recursion topics:
    Recursion Basics
        ↓
    Backtracking
        ↓
    Dynamic Programming & Advanced Recursion
    """
    
    def __init__(self):
        """Initialize the prerequisite graph."""
        # Define the graph structure: concept -> list of prerequisites
        self.prerequisites: Dict[str, List[str]] = {
            "Recursion Basics": [],
            "Backtracking": ["Recursion Basics"],
            "Dynamic Programming & Advanced Recursion": ["Backtracking"]
        }
        
        # Reverse mapping: concept -> list of concepts that depend on it
        self.dependents: Dict[str, List[str]] = self._build_dependents()
        
        # All concepts in order
        self.all_concepts = [
            "Recursion Basics",
            "Backtracking",
            "Dynamic Programming & Advanced Recursion"
        ]
    
    def _build_dependents(self) -> Dict[str, List[str]]:
        """Build reverse mapping of dependencies."""
        dependents = {concept: [] for concept in self.prerequisites.keys()}
        
        for concept, prereqs in self.prerequisites.items():
            for prereq in prereqs:
                dependents[prereq].append(concept)
        
        return dependents
    
    def get_prerequisites(self, concept: str) -> List[str]:
        """Get direct prerequisites for a concept."""
        return self.prerequisites.get(concept, [])
    
    def get_all_prerequisites(self, concept: str) -> Set[str]:
        """Get all prerequisites (transitive closure) for a concept."""
        all_prereqs = set()
        to_process = [concept]
        
        while to_process:
            current = to_process.pop()
            prereqs = self.prerequisites.get(current, [])
            
            for prereq in prereqs:
                if prereq not in all_prereqs:
                    all_prereqs.add(prereq)
                    to_process.append(prereq)
        
        return all_prereqs
    
    def get_dependents(self, concept: str) -> List[str]:
        """Get concepts that directly depend on this concept."""
        return self.dependents.get(concept, [])
    
    def can_unlock(self, concept: str, concept_status: Dict[str, str]) -> bool:
        """
        Check if a concept can be unlocked based on prerequisites.
        
        A concept can be unlocked if all its prerequisites are mastered.
        """
        prereqs = self.get_prerequisites(concept)
        
        if not prereqs:
            return True
        
        return all(
            concept_status.get(prereq) == ConceptStatus.MASTERED.value
            for prereq in prereqs
        )
    
    def should_unlock(self, concept: str, concept_status: Dict[str, str]) -> bool:
        """
        Check if a concept should be unlocked (prerequisites met and currently locked).
        """
        current_status = concept_status.get(concept, ConceptStatus.LOCKED.value)
        
        if current_status != ConceptStatus.LOCKED.value:
            return False
        
        return self.can_unlock(concept, concept_status)
    
    def get_unlockable_concepts(self, concept_status: Dict[str, str]) -> List[str]:
        """Get all concepts that can be unlocked."""
        return [
            concept for concept in self.all_concepts
            if self.should_unlock(concept, concept_status)
        ]
    
    def get_available_concepts(self, concept_status: Dict[str, str]) -> List[str]:
        """
        Get concepts that are available for learning (opened or mastered).
        """
        return [
            concept for concept in self.all_concepts
            if concept_status.get(concept) in [
                ConceptStatus.OPENED.value,
                ConceptStatus.MASTERED.value
            ]
        ]
    
    def get_next_concept_to_learn(self, concept_status: Dict[str, str]) -> Optional[str]:
        """
        Get the next concept that should be focused on.
        
        Priority:
        1. First opened concept (not yet mastered)
        2. First unlockable concept
        3. None if all mastered or nothing available
        """
        # First, try to find an opened but not mastered concept
        for concept in self.all_concepts:
            if concept_status.get(concept) == ConceptStatus.OPENED.value:
                return concept
        
        # If none found, try to unlock the next concept
        unlockable = self.get_unlockable_concepts(concept_status)
        if unlockable:
            return unlockable[0]
        
        return None
    
    def get_concept_level(self, concept: str) -> int:
        """
        Get the level/depth of a concept in the prerequisite tree.
        Level 0 = no prerequisites, Level 1 = depends on level 0, etc.
        """
        if not self.prerequisites.get(concept):
            return 0
        
        max_prereq_level = 0
        for prereq in self.prerequisites[concept]:
            prereq_level = self.get_concept_level(prereq)
            max_prereq_level = max(max_prereq_level, prereq_level)
        
        return max_prereq_level + 1
    
    def to_dict(self) -> Dict[str, any]:
        """Convert graph to dictionary representation."""
        return {
            'concepts': self.all_concepts,
            'prerequisites': self.prerequisites,
            'dependents': self.dependents,
            'levels': {
                concept: self.get_concept_level(concept)
                for concept in self.all_concepts
            }
        }
