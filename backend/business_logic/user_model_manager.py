"""
User Model Manager.

Manages user state including ability estimates (theta) per topic,
concept mastery status, and answer history.
"""
from typing import Dict, List, Optional
from datetime import datetime
from backend.data.models import UserProfile, AnswerRecord, Question, ConceptStatus
from backend.data.prerequisite_graph import PrerequisiteGraph
from backend.business_logic.irt_engine import IRTEngine
from backend.config import Config


class UserModelManager:
    """
    Manages user model state and updates.
    
    Responsibilities:
    - Track theta (ability) per topic
    - Manage concept status (locked, opened, mastered)
    - Update mastery based on performance
    - Maintain answer history
    """
    
    def __init__(self, user_profile: UserProfile, prerequisite_graph: PrerequisiteGraph):
        """
        Initialize user model manager.
        
        Args:
            user_profile: User profile to manage
            prerequisite_graph: Graph of concept dependencies
        """
        self.profile = user_profile
        self.graph = prerequisite_graph
        self.irt_engine = IRTEngine()
    
    def get_theta(self, topic: str) -> float:
        """Get current ability estimate for a topic."""
        return self.profile.theta_by_topic.get(topic, Config.IRT_INITIAL_THETA)
    
    def set_theta(self, topic: str, theta: float):
        """Set ability estimate for a topic."""
        self.profile.theta_by_topic[topic] = theta
    
    def get_concept_status(self, concept: str) -> str:
        """Get status of a concept."""
        return self.profile.concept_status.get(concept, ConceptStatus.LOCKED.value)
    
    def set_concept_status(self, concept: str, status: ConceptStatus):
        """Set status of a concept."""
        self.profile.concept_status[concept] = status.value
    
    def update_theta(self, topic: str, question: Question, correct: bool) -> float:
        """
        Update ability estimate based on answer.
        
        Args:
            topic: Topic of the question
            question: Question that was answered
            correct: Whether answer was correct
            
        Returns:
            New theta value
        """
        current_theta = self.get_theta(topic)

        # Use per-topic recent answers for a stable EAP update.
        # We include the new answer explicitly; IRTEngine enforces N>1.
        topic_history = [
            record for record in self.profile.answer_history
            if getattr(record, 'topic', None) == topic
        ]

        new_theta = self.irt_engine.update_theta(
            current_theta=current_theta,
            question=question,
            correct=correct,
            answer_history=topic_history
        )
        
        self.set_theta(topic, new_theta)
        
        return new_theta
    
    def record_answer(self, question: Question, correct: bool, 
                     time_taken: float, test_results: Dict = None,
                     subjective_feedback: Dict = None):
        """
        Record an answer in the history.
        
        Args:
            question: Question that was answered
            correct: Whether answer was correct
            time_taken: Time taken in seconds
            test_results: Detailed test results
            subjective_feedback: User's subjective feedback
        """
        theta_before = self.get_theta(question.topic)
        
        # Update theta
        theta_after = self.update_theta(question.topic, question, correct)
        
        # Create answer record
        record = AnswerRecord(
            question_name=question.name,
            topic=question.topic,
            alpha=question.alpha,
            beta=question.beta,
            c=question.c,
            timestamp=datetime.now().isoformat(),
            correct=correct,
            time_taken=time_taken,
            theta_before=theta_before,
            theta_after=theta_after,
            test_results=test_results,
            subjective_feedback=subjective_feedback
        )
        
        self.profile.answer_history.append(record)
        
        # Check if concept should be mastered or unlocked
        self._update_concept_status(question.topic)
    
    def _update_concept_status(self, topic: str):
        """
        Update concept status based on performance.
        
        A concept becomes mastered when theta exceeds mastery threshold.
        When a concept is mastered, dependent concepts may be unlocked.
        """
        current_status = self.get_concept_status(topic)
        current_theta = self.get_theta(topic)
        
        # Check if concept should be mastered
        if current_status == ConceptStatus.OPENED.value:
            if current_theta >= Config.MASTERY_THRESHOLD:
                self.set_concept_status(topic, ConceptStatus.MASTERED)
                
                # Try to unlock dependent concepts
                self._unlock_dependent_concepts(topic)
    
    def _unlock_dependent_concepts(self, mastered_concept: str):
        """
        Unlock concepts that depend on a newly mastered concept.
        
        Args:
            mastered_concept: Concept that was just mastered
        """
        # Get concepts that depend on this one
        dependents = self.graph.get_dependents(mastered_concept)
        
        for dependent in dependents:
            # Check if it should be unlocked
            if self.graph.should_unlock(dependent, self.profile.concept_status):
                self.set_concept_status(dependent, ConceptStatus.OPENED)
    
    def get_available_topics(self) -> List[str]:
        """
        Get topics that are available for learning (opened or mastered).
        
        Returns:
            List of topic names
        """
        return self.graph.get_available_concepts(self.profile.concept_status)
    
    def get_locked_topics(self) -> List[str]:
        """Get topics that are locked."""
        return [
            topic for topic in self.graph.all_concepts
            if self.get_concept_status(topic) == ConceptStatus.LOCKED.value
        ]
    
    def get_mastered_topics(self) -> List[str]:
        """Get topics that are mastered."""
        return [
            topic for topic in self.graph.all_concepts
            if self.get_concept_status(topic) == ConceptStatus.MASTERED.value
        ]
    
    def get_current_focus_topic(self) -> Optional[str]:
        """
        Get the topic that should be the current focus.
        
        Returns the first opened (not mastered) topic, or None if all mastered.
        """
        return self.graph.get_next_concept_to_learn(self.profile.concept_status)
    
    def get_topic_progress(self, topic: str) -> Dict:
        """
        Get progress information for a topic.
        
        Returns:
            Dictionary with progress metrics
        """
        theta = self.get_theta(topic)
        status = self.get_concept_status(topic)
        
        # Calculate progress percentage (0-100)
        # Based on theta relative to mastery threshold
        if status == ConceptStatus.MASTERED.value:
            progress = 100.0
        elif status == ConceptStatus.LOCKED.value:
            progress = 0.0
        else:
            # Linear interpolation from 0 to mastery threshold
            progress = min(100.0, max(0.0, 
                (theta - Config.IRT_INITIAL_THETA) / 
                (Config.MASTERY_THRESHOLD - Config.IRT_INITIAL_THETA) * 100
            ))
        
        # Count attempts for this topic
        attempts = sum(
            1 for record in self.profile.answer_history
            # We'd need to check topic via question lookup, simplified here
        )
        
        return {
            'topic': topic,
            'theta': theta,
            'status': status,
            'progress_percent': progress,
            'attempts': attempts,
            'mastery_threshold': Config.MASTERY_THRESHOLD
        }
    
    def get_overall_progress(self) -> Dict:
        """
        Get overall learning progress across all topics.
        
        Returns:
            Dictionary with overall metrics
        """
        all_topics = self.graph.all_concepts
        
        mastered_count = len(self.get_mastered_topics())
        opened_count = len([
            t for t in all_topics
            if self.get_concept_status(t) == ConceptStatus.OPENED.value
        ])
        locked_count = len(self.get_locked_topics())
        
        overall_progress = (mastered_count / len(all_topics)) * 100 if all_topics else 0
        
        return {
            'total_topics': len(all_topics),
            'mastered': mastered_count,
            'in_progress': opened_count,
            'locked': locked_count,
            'overall_progress_percent': overall_progress,
            'total_attempts': len(self.profile.answer_history),
            'current_focus': self.get_current_focus_topic()
        }
    
    def get_recent_performance(self, n: int = 10) -> Dict:
        """
        Get recent performance statistics.
        
        Args:
            n: Number of recent attempts to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        recent = self.profile.answer_history[-n:] if self.profile.answer_history else []
        
        if not recent:
            return {
                'attempts': 0,
                'correct': 0,
                'accuracy': 0.0,
                'avg_time': 0.0
            }
        
        correct_count = sum(1 for r in recent if r.correct)
        avg_time = sum(r.time_taken for r in recent) / len(recent)
        
        return {
            'attempts': len(recent),
            'correct': correct_count,
            'accuracy': correct_count / len(recent),
            'avg_time': avg_time
        }
    
    def reset_topic(self, topic: str):
        """
        Reset a topic to initial state.
        
        Args:
            topic: Topic to reset
        """
        self.set_theta(topic, Config.IRT_INITIAL_THETA)
        
        # Reset status based on prerequisites
        if self.graph.can_unlock(topic, self.profile.concept_status):
            self.set_concept_status(topic, ConceptStatus.OPENED)
        else:
            self.set_concept_status(topic, ConceptStatus.LOCKED)
    
    def get_profile(self) -> UserProfile:
        """Get the user profile."""
        return self.profile
