"""
Data models for AdaptiCode system.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ConceptStatus(Enum):
    """Status of a concept in the learning path."""
    LOCKED = "locked"
    OPENED = "opened"
    MASTERED = "mastered"


@dataclass
class Test:
    """Represents a test case for a question."""
    input: Any
    output: Any
    is_unordered: bool = False  # Whether the output order matters


@dataclass
class Question:
    """Represents a programming question."""
    name: str
    topic: str
    description: str
    alpha: float  # IRT discrimination parameter (a)
    beta: float   # IRT difficulty parameter (b)
    tests: List[Test]
    hidden_tests: List[Test]
    c: float = 0.25  # IRT guessing parameter (default)
    init_code: str = "solve()"  # Initial code template for the question
    is_unordered: bool = False  # Whether the output order matters for this question
    
    @property
    def a(self) -> float:
        """IRT discrimination parameter."""
        return self.alpha
    
    @property
    def b(self) -> float:
        """IRT difficulty parameter."""
        return self.beta
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'topic': self.topic,
            'description': self.description,
            'alpha': self.alpha,
            'beta': self.beta,
            'c': self.c,
            'is_unordered': self.is_unordered,
            'tests': [{'input': t.input, 'output': t.output, 'is_unordered': t.is_unordered} 
                     for t in self.tests],
            'hidden_tests': [{'input': t.input, 'output': t.output, 'is_unordered': t.is_unordered} 
                           for t in self.hidden_tests]
        }


@dataclass
class AnswerRecord:
    """Record of a user's answer to a question."""
    question_name: str
    timestamp: str
    correct: bool
    time_taken: float  # in seconds
    theta_before: float
    theta_after: float
    topic: Optional[str] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    c: Optional[float] = None
    test_results: Optional[Dict[str, Any]] = None
    subjective_feedback: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class UserProfile:
    """User profile with learning state."""
    user_id: str = "default_user"
    theta_by_topic: Dict[str, float] = field(default_factory=dict)
    concept_status: Dict[str, str] = field(default_factory=dict)
    answer_history: List[AnswerRecord] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default values if not provided."""
        if not self.theta_by_topic:
            self.theta_by_topic = {
                "Recursion Basics": 0.0,
                "Backtracking": 0.0,
                "Dynamic Programming & Advanced Recursion": 0.0
            }
        if not self.concept_status:
            # TODO: uncomment when questions ready
            # self.concept_status = {
            #     "Recursion Basics": ConceptStatus.OPENED.value,
            #     "Call Stack & Linear Recursion": ConceptStatus.LOCKED.value,
            #     "Tree Recursion": ConceptStatus.LOCKED.value,
            #     "Backtracking": ConceptStatus.LOCKED.value
            # }
            self.concept_status = {
                "Recursion Basics": ConceptStatus.OPENED.value,
                "Backtracking": ConceptStatus.LOCKED.value,
                "Dynamic Programming & Advanced Recursion": ConceptStatus.LOCKED.value
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'theta_by_topic': self.theta_by_topic,
            'concept_status': self.concept_status,
            'answer_history': [
                record.to_dict() if isinstance(record, AnswerRecord) else record
                for record in self.answer_history
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create UserProfile from dictionary."""
        answer_history = []
        for record in data.get('answer_history', []):
            if isinstance(record, dict):
                answer_history.append(AnswerRecord(**record))
            else:
                answer_history.append(record)
        
        return cls(
            user_id=data.get('user_id', 'default_user'),
            theta_by_topic=data.get('theta_by_topic', {}),
            concept_status=data.get('concept_status', {}),
            answer_history=answer_history
        )


@dataclass
class InteractionLog:
    """Log of user interactions."""
    timestamp: str
    action: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TreeNode:
    """Binary tree node for tree-based questions."""
    val: Any
    left: Optional['TreeNode'] = None
    right: Optional['TreeNode'] = None
    
    def to_list(self) -> List[Any]:
        """Convert tree to level-order list representation."""
        if not self:
            return []
        
        result = []
        queue = [self]
        
        while queue:
            node = queue.pop(0)
            if node:
                result.append(node.val)
                queue.append(node.left)
                queue.append(node.right)
            else:
                result.append(None)
        
        # Remove trailing None values
        while result and result[-1] is None:
            result.pop()
        
        return result
    
    @classmethod
    def from_list(cls, arr: List[Any]) -> Optional['TreeNode']:
        """Create tree from level-order list representation."""
        if not arr or arr[0] is None:
            return None
        
        root = cls(arr[0])
        queue = [root]
        i = 1
        
        while queue and i < len(arr):
            node = queue.pop(0)
            
            # Left child
            if i < len(arr) and arr[i] is not None:
                node.left = cls(arr[i])
                queue.append(node.left)
            i += 1
            
            # Right child
            if i < len(arr) and arr[i] is not None:
                node.right = cls(arr[i])
                queue.append(node.right)
            i += 1
        
        return root


@dataclass
class ListNode:
    """Linked list node for list-based questions."""
    val: Any
    next: Optional['ListNode'] = None
    
    def to_list(self) -> List[Any]:
        """Convert linked list to array."""
        result = []
        current = self
        while current:
            result.append(current.val)
            current = current.next
        return result
    
    @classmethod
    def from_list(cls, arr: List[Any]) -> Optional['ListNode']:
        """Create linked list from array."""
        if not arr:
            return None
        
        head = cls(arr[0])
        current = head
        
        for val in arr[1:]:
            current.next = cls(val)
            current = current.next
        
        return head
