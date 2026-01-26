"""
Data manager for loading and persisting data.
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from backend.data.models import Question, Test, UserProfile, InteractionLog
from backend.data.prerequisite_graph import PrerequisiteGraph
from backend.config import Config


class DataManager:
    """Manages data loading, persistence, and access."""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize data manager.
        
        Args:
            data_dir: Directory containing data files
        """
        self.data_dir = data_dir
        self.questions_dir = os.path.join(data_dir, "questions")
        self.user_data_file = os.path.join(data_dir, "user_data.json")
        self.interaction_log_file = os.path.join(data_dir, "interaction_log.json")
        
        # In-memory storage
        self.questions: Dict[str, Question] = {}
        self.questions_by_topic: Dict[str, List[Question]] = {}
        self.user_profile: Optional[UserProfile] = None
        self.interaction_logs: List[InteractionLog] = []
        self.prerequisite_graph = PrerequisiteGraph()

        if Config.USER_MODE == 'reset':
            self._reset_user_state_files()
        
        # Load data
        self._load_questions()
        self._load_user_profile()
        self._load_interaction_logs()

    def _reset_user_state_files(self):
        """Reset persisted user state so the app starts as a new user."""
        for path in (self.user_data_file, self.interaction_log_file):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
    
    def _load_questions(self):
        """Load all questions from JSON files."""
        question_files = [
            "basecase_recursion_questions.json",  # For Recursion Basics
            "backtracking_questions.json",       # For Backtracking
            "advanced_dp_recursion.json"         # For Dynamic Programming & Advanced Recursion
        ]
        
        for filename in question_files:
            filepath = os.path.join(self.questions_dir, filename)
            
            if not os.path.exists(filepath):
                print(f"Warning: Question file not found: {filepath}")
                continue
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            topic = data.get('topic')
            if not topic:
                # For tree_recursion and backtracking files that don't have top-level topic
                questions_data = data.get('questions', [])
                if questions_data and 'topic' in questions_data[0]:
                    topic = questions_data[0]['topic']
            
            questions_data = data.get('questions', [])
            
            if topic not in self.questions_by_topic:
                self.questions_by_topic[topic] = []
            
            for q_data in questions_data:
                # Parse tests
                tests = [Test(**t) for t in q_data.get('tests', [])]
                hidden_tests = [Test(**t) for t in q_data.get('hidden_tests', [])]
                
                question = Question(
                    name=q_data['name'],
                    topic=q_data.get('topic', topic),
                    description=q_data['description'],
                    alpha=q_data['alpha'],
                    beta=q_data['beta'],
                    tests=tests,
                    hidden_tests=hidden_tests,
                    c=q_data.get('c', 0.25),
                    init_code=q_data.get('init_code', 'solve()')
                )
                
                self.questions[question.name] = question
                self.questions_by_topic[question.topic].append(question)
        
        print(f"Loaded {len(self.questions)} questions across {len(self.questions_by_topic)} topics")
    
    def _load_user_profile(self):
        """Load user profile from JSON file."""
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r') as f:
                data = json.load(f)
                self.user_profile = UserProfile.from_dict(data)
        else:
            # Create new user profile
            self.user_profile = UserProfile()
            self.save_user_profile()
    
    def _load_interaction_logs(self):
        """Load interaction logs from JSON file."""
        if os.path.exists(self.interaction_log_file):
            with open(self.interaction_log_file, 'r') as f:
                data = json.load(f)
                self.interaction_logs = [InteractionLog(**log) for log in data]
        else:
            self.interaction_logs = []
    
    def save_user_profile(self):
        """Save user profile to JSON file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        with open(self.user_data_file, 'w') as f:
            json.dump(self.user_profile.to_dict(), f, indent=2)
    
    def save_interaction_logs(self):
        """Save interaction logs to JSON file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        with open(self.interaction_log_file, 'w') as f:
            json.dump([log.to_dict() for log in self.interaction_logs], f, indent=2)
    
    def log_interaction(self, action: str, details: Dict):
        """Log a user interaction."""
        log = InteractionLog(
            timestamp=datetime.now().isoformat(),
            action=action,
            details=details
        )
        self.interaction_logs.append(log)
        self.save_interaction_logs()
    
    def get_question(self, question_name: str) -> Optional[Question]:
        """Get a question by name."""
        return self.questions.get(question_name)
    
    def get_questions_by_topic(self, topic: str) -> List[Question]:
        """Get all questions for a topic."""
        return self.questions_by_topic.get(topic, [])
    
    def get_all_questions(self) -> List[Question]:
        """Get all questions."""
        return list(self.questions.values())
    
    def get_all_topics(self) -> List[str]:
        """Get all available topics."""
        return list(self.questions_by_topic.keys())
    
    def get_user_profile(self) -> UserProfile:
        """Get the user profile."""
        return self.user_profile
    
    def update_user_profile(self, profile: UserProfile):
        """Update and save user profile."""
        self.user_profile = profile
        self.save_user_profile()
    
    def get_prerequisite_graph(self) -> PrerequisiteGraph:
        """Get the prerequisite graph."""
        return self.prerequisite_graph
    
    def get_recent_questions(self, topic: str, n: int = 5) -> List[str]:
        """
        Get the names of the n most recently answered questions for a topic.
        
        Args:
            topic: The topic to filter by
            n: Number of recent questions to return
            
        Returns:
            List of question names
        """
        recent = []
        
        # Iterate through answer history in reverse (most recent first)
        for record in reversed(self.user_profile.answer_history):
            question = self.get_question(record.question_name)
            if question and question.topic == topic:
                if record.question_name not in recent:
                    recent.append(record.question_name)
                    if len(recent) >= n:
                        break
        
        return recent
    
    def get_question_attempt_count(self, question_name: str) -> int:
        """Get the number of times a question has been attempted."""
        count = 0
        for record in self.user_profile.answer_history:
            if record.question_name == question_name:
                count += 1
        return count
    
    def get_topic_statistics(self, topic: str) -> Dict:
        """Get statistics for a topic."""
        questions = self.get_questions_by_topic(topic)
        attempts = [
            record for record in self.user_profile.answer_history
            if self.get_question(record.question_name) and 
            self.get_question(record.question_name).topic == topic
        ]
        
        correct_attempts = [a for a in attempts if a.correct]
        
        return {
            'topic': topic,
            'total_questions': len(questions),
            'total_attempts': len(attempts),
            'correct_attempts': len(correct_attempts),
            'accuracy': len(correct_attempts) / len(attempts) if attempts else 0,
            'current_theta': self.user_profile.theta_by_topic.get(topic, 0.0),
            'status': self.user_profile.concept_status.get(topic, 'locked')
        }
