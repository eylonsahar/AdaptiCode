"""
Selection Engine for adaptive question selection.

Implements three-stage selection process from the paper:
1. Topic Selection: Based on prerequisite graph and concept mastery
2. IRT-based Selection: Filter k-best questions by information gain
3. History-based Prioritization: Avoid recently asked questions
"""
from typing import List, Optional, Dict, Tuple
import random
from datetime import datetime
from backend.data.models import Question
from backend.data.data_manager import DataManager
from backend.business_logic.irt_engine import IRTEngine
from backend.business_logic.user_model_manager import UserModelManager
from backend.business_logic.llm_gateway import LLMGateway
from backend.config import Config


class SelectionEngine:
    """
    Adaptive question selection engine.
    
    Combines topic selection, IRT-based difficulty matching,
    and history-based filtering for optimal question selection.
    """

    HISTORY_POLICY_LRU_PROBABILITY = 0.95
    HISTORY_POLICY_WRONG_RECENCY_MULTIPLIER = 2.0
    
    def __init__(self, data_manager: DataManager, user_model_manager: UserModelManager):
        """
        Initialize selection engine.
        
        Args:
            data_manager: Data manager for accessing questions
            user_model_manager: User model manager for user state
        """
        self.data_manager = data_manager
        self.user_model = user_model_manager
        self.irt_engine = IRTEngine()
        self.graph = data_manager.get_prerequisite_graph()
        self.llm_gateway = LLMGateway()
        
        # Store the last selection explanation
        self.last_selection_explanation = None
    
    def select_next_question(self) -> Optional[Question]:
        """
        Select the next question using three-stage process.
        
        Returns:
            Selected question, or None if no suitable question found
        """
        # Stage 1: Topic Selection
        target_topic = self._select_topic()
        
        if not target_topic:
            return None
        
        # Stage 2: IRT-based Selection
        candidate_questions = self._get_candidate_questions(target_topic)
        
        if not candidate_questions:
            return None
        
        # Stage 3: History-based selection policy (95% LRU, 5% difficult re-ask)
        selected = self._select_question_by_history_policy(candidate_questions, target_topic)
        if selected is not None:
            return selected

        # Fallback: select best question by information --selected is None
        theta = self.user_model.get_theta(target_topic)
        return self.irt_engine.select_best_question(theta, candidate_questions)
    
    def _select_topic(self) -> Optional[str]:
        """
        Stage 1: Select the topic to focus on.
        
        Priority:
        1. First opened (not mastered) topic in prerequisite order
        2. If all mastered, select first mastered topic for review
        
        Returns:
            Selected topic name, or None if no topics available
        """
        # Get the next concept to learn from the graph
        focus_topic = self.user_model.get_current_focus_topic()
        
        if focus_topic:
            return focus_topic
        
        # If all mastered, select first mastered topic for review
        mastered = self.user_model.get_mastered_topics()
        if mastered:
            return mastered[0]
        
        return None
    
    def _get_candidate_questions(self, topic: str) -> List[Question]:
        """
        Stage 2: Get candidate questions using IRT-based selection.
        
        Select k-best questions based on information gain at current ability level.
        
        Args:
            topic: Topic to select questions from
            
        Returns:
            List of candidate questions
        """
        # Get all questions for the topic
        all_questions = self.data_manager.get_questions_by_topic(topic)
        
        if not all_questions:
            return []
        
        # Get current ability
        theta = self.user_model.get_theta(topic)
        
        # Rank questions by information
        ranked = self.irt_engine.rank_questions_by_information(theta, all_questions)
        
        # Select top k questions
        k = min(Config.K_BEST_QUESTIONS, len(ranked))
        candidates = [q for q, info in ranked[:k]]
        
        return candidates
    
    def _select_question_by_history_policy(self, questions: List[Question], topic: str) -> Optional[Question]:
        """Select a single question from candidates using RAG-enhanced history-based policy.

        New Policy:
        - Get top 3 questions using LRU with wrong-weighted recency
        - Use LLM (RAG) to select the best question from these 3
        - Store the explanation for display on question page
        - Never select the last attempted question again immediately

        """
        if not questions:
            return None

        history = self._build_question_history(topic)
        if not history:
            # No history yet: deterministically pick the most informative question.
            theta = self.user_model.get_theta(topic)
            selected = self.irt_engine.select_best_question(theta, questions)
            self.last_selection_explanation = "This is your first question in this topic. It's designed to assess your current understanding."
            return selected

        # Get the last attempted question
        last_attempted = None
        last_timestamp = None
        for q_name, stats in history.items():
            if stats['last_ts'] and (last_timestamp is None or stats['last_ts'] > last_timestamp):
                last_attempted = q_name
                last_timestamp = stats['last_ts']

        # Filter out the last attempted question from candidates if it exists
        filtered_questions = [q for q in questions if q.name != last_attempted] if last_attempted else questions
        
        # If we filtered out all questions, return None to trigger fallback
        if not filtered_questions:
            return None

        # Get top 3 questions using LRU wrong-weighted scoring
        top_3_questions = self._get_top_n_lru_questions(filtered_questions, history, n=3)
        
        # Use RAG to select best question from top 3
        theta = self.user_model.get_theta(topic)
        recent_performance = self._get_recent_performance_stats(topic)
        
        rag_result = self.llm_gateway.select_question_with_rag(
            candidate_questions=top_3_questions,
            student_theta=theta,
            topic=topic,
            recent_performance=recent_performance
        )
        
        # Store explanation for later retrieval
        self.last_selection_explanation = rag_result.get('explanation', '')
        
        # Find and return the selected question
        selected_name = rag_result.get('selected_question')
        for q in top_3_questions:
            if q.name == selected_name:
                return q
        
        # Fallback if something went wrong
        return top_3_questions[0] if top_3_questions else None
    
    def _get_top_n_lru_questions(self, questions: List[Question], history: Dict[str, Dict[str, object]], n: int = 3) -> List[Question]:
        """Get top N questions by LRU wrong-weighted scoring."""
        from datetime import datetime
        
        now = datetime.now()

        def score(q: Question) -> Tuple[float, str]:
            entry = history.get(q.name)
            if not entry or entry.get('last_ts') is None:
                base_age = float('inf')
                last_correct = None
                wrong_count = 0
            else:
                base_age = (now - entry['last_ts']).total_seconds()
                last_correct = entry.get('last_correct')
                wrong_count = int(entry.get('wrong', 0))

            multiplier = 1.0
            if last_correct is False:
                multiplier *= self.HISTORY_POLICY_WRONG_RECENCY_MULTIPLIER
            multiplier *= (1.0 + 0.1 * wrong_count)

            return (base_age * multiplier, q.name)

        # Sort by score (descending) and take top n
        sorted_questions = sorted(questions, key=score, reverse=True)
        return sorted_questions[:min(n, len(sorted_questions))]
    
    def _get_recent_performance_stats(self, topic: str) -> Dict:
        """Get recent performance statistics for the topic."""
        profile = self.data_manager.get_user_profile()
        
        total_attempts = 0
        correct_attempts = 0
        
        # Look at last 5 attempts in this topic
        recent_count = 0
        for record in reversed(profile.answer_history):
            q = self.data_manager.get_question(record.question_name)
            if q and q.topic == topic:
                total_attempts += 1
                if record.correct:
                    correct_attempts += 1
                recent_count += 1
                if recent_count >= 5:
                    break
        
        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts
        }
    
    def get_last_selection_explanation(self) -> Optional[str]:
        """Get the explanation for the last selected question."""
        return self.last_selection_explanation

    def _build_question_history(self, topic: str) -> Dict[str, Dict[str, object]]:
        """Build per-question history stats for a topic.

        Returns a dict keyed by question name.
        Each value contains:
        - last_ts: datetime of last attempt (or None)
        - last_correct: Optional[bool]
        - wrong: int
        - correct: int
        """
        stats: Dict[str, Dict[str, object]] = {}

        for record in self.data_manager.get_user_profile().answer_history:
            q = self.data_manager.get_question(record.question_name)
            if not q or q.topic != topic:
                continue

            entry = stats.setdefault(record.question_name, {
                'last_ts': None,
                'last_correct': None,
                'wrong': 0,
                'correct': 0,
            })

            ts = None
            try:
                ts = datetime.fromisoformat(record.timestamp)
            except Exception:
                ts = None

            if ts is not None:
                last_ts = entry['last_ts']
                if last_ts is None or ts >= last_ts:
                    entry['last_ts'] = ts
                    entry['last_correct'] = bool(record.correct)

            if record.correct:
                entry['correct'] += 1
            else:
                entry['wrong'] += 1

        return stats

    def _select_lru_wrong_weighted(self, questions: List[Question], history: Dict[str, Dict[str, object]]) -> Question:
        """Deterministically select question by (wrong-weighted) LRU.

        We treat wrong answers as *more important*, meaning they get a boost in priority
        even if they were seen recently.

        Higher score wins.
        """
        now = datetime.now()

        def score(q: Question) -> Tuple[float, str]:
            entry = history.get(q.name)
            if not entry or entry.get('last_ts') is None:
                base_age = float('inf')
                last_correct = None
                wrong_count = 0
            else:
                base_age = (now - entry['last_ts']).total_seconds()
                last_correct = entry.get('last_correct')
                wrong_count = int(entry.get('wrong', 0))

            multiplier = 1.0
            if last_correct is False:
                multiplier *= self.HISTORY_POLICY_WRONG_RECENCY_MULTIPLIER
            multiplier *= (1.0 + 0.1 * wrong_count)

            return (base_age * multiplier, q.name)

        return max(questions, key=score)

    def _select_difficult_question(self, questions: List[Question], history: Dict[str, Dict[str, object]]) -> Optional[Question]:
        """Deterministically select a previously difficult question.

        "Difficult" = many wrong and few correct attempts.
        Only considers questions that have been attempted at least once.
        """
        now = datetime.now()
        attempted: List[Question] = [q for q in questions if q.name in history]
        if not attempted:
            return None

        def score(q: Question) -> Tuple[float, float, str]:
            entry = history.get(q.name, {})
            wrong = float(entry.get('wrong', 0))
            correct = float(entry.get('correct', 0))
            attempts = wrong + correct

            wrong_rate = (wrong / attempts) if attempts > 0 else 0.0
            difficulty_score = (wrong - correct) + wrong_rate

            last_ts = entry.get('last_ts')
            recency_age = (now - last_ts).total_seconds() if isinstance(last_ts, datetime) else 0.0
            return (difficulty_score, recency_age, q.name)

        return max(attempted, key=score)
    
    def get_recommended_questions(self, topic: str, n: int = 5) -> List[Question]:
        """
        Get n recommended questions for a specific topic.
        
        Args:
            topic: Topic to get recommendations for
            n: Number of questions to recommend
            
        Returns:
            List of recommended questions
        """
        # Get all questions for topic
        all_questions = self.data_manager.get_questions_by_topic(topic)
        
        if not all_questions:
            return []
        
        # Get current ability
        theta = self.user_model.get_theta(topic)
        
        # Rank by information
        ranked = self.irt_engine.rank_questions_by_information(theta, all_questions)
        
        # Filter by history
        recent = set(self.data_manager.get_recent_questions(topic, Config.QUESTION_HISTORY_WINDOW))
        filtered_ranked = [(q, info) for q, info in ranked if q.name not in recent]
        
        # If not enough after filtering, include some recent ones
        if len(filtered_ranked) < n:
            filtered_ranked = ranked
        
        # Return top n
        return [q for q, info in filtered_ranked[:n]]
    
    def get_questions_by_difficulty(self, topic: str, difficulty: str) -> List[Question]:
        """
        Get questions filtered by difficulty level.
        
        Args:
            topic: Topic to filter
            difficulty: 'easy', 'medium', or 'hard'
            
        Returns:
            List of questions matching difficulty
        """
        questions = self.data_manager.get_questions_by_topic(topic)
        theta = self.user_model.get_theta(topic)
        
        filtered = []
        
        for q in questions:
            # Classify difficulty relative to user's ability
            diff = q.b - theta
            
            if difficulty == 'easy' and diff < -0.5:
                filtered.append(q)
            elif difficulty == 'medium' and -0.5 <= diff <= 0.5:
                filtered.append(q)
            elif difficulty == 'hard' and diff > 0.5:
                filtered.append(q)
        
        return filtered
    
    def should_move_to_next_topic(self, topic: str) -> bool:
        """
        Determine if learner should move to next topic.
        
        Args:
            topic: Current topic
            
        Returns:
            True if should move to next topic
        """
        # Check if topic is mastered
        theta = self.user_model.get_theta(topic)
        
        return theta >= Config.MASTERY_THRESHOLD
    
    def get_selection_explanation(self, question: Question) -> Dict:
        """
        Get explanation for why a question was selected.
        
        Args:
            question: Selected question
            
        Returns:
            Dictionary with selection reasoning
        """
        topic = question.topic
        theta = self.user_model.get_theta(topic)
        
        # Calculate metrics
        prob_correct = self.irt_engine.probability_correct(theta, question)
        information = self.irt_engine.information(theta, question)
        difficulty_match = abs(question.b - theta)
        
        # Determine difficulty level
        diff = question.b - theta
        if diff < -0.5:
            difficulty_level = "easy"
        elif diff > 0.5:
            difficulty_level = "hard"
        else:
            difficulty_level = "medium"
        
        return {
            'question_name': question.name,
            'topic': topic,
            'your_ability': round(theta, 2),
            'question_difficulty': round(question.b, 2),
            'difficulty_level': difficulty_level,
            'probability_correct': round(prob_correct, 2),
            'information_value': round(information, 2),
            'difficulty_match': round(difficulty_match, 2),
            'reason': self._generate_selection_reason(
                difficulty_level, prob_correct, information
            )
        }
    
    def _generate_selection_reason(self, difficulty: str, prob: float, info: float) -> str:
        """Generate human-readable reason for selection."""
        if info > 1.0:
            info_desc = "very informative"
        elif info > 0.5:
            info_desc = "informative"
        else:
            info_desc = "moderately informative"
        
        if prob > 0.8:
            prob_desc = "high chance of success"
        elif prob > 0.5:
            prob_desc = "good chance of success"
        else:
            prob_desc = "challenging"
        
        return (
            f"This {difficulty} question is {info_desc} for your current level "
            f"and offers a {prob_desc}. It will help us better understand your abilities."
        )
    
    def get_topic_readiness(self, topic: str) -> Dict:
        """
        Assess readiness for a topic.
        
        Args:
            topic: Topic to assess
            
        Returns:
            Dictionary with readiness information
        """
        status = self.user_model.get_concept_status(topic)
        theta = self.user_model.get_theta(topic)
        
        # Check prerequisites
        prereqs = self.graph.get_prerequisites(topic)
        prereqs_met = all(
            self.user_model.get_concept_status(p) == "mastered"
            for p in prereqs
        )
        
        # Calculate readiness score (0-100)
        if status == "mastered":
            readiness = 100
        elif status == "opened":
            readiness = 50 + min(50, (theta / Config.MASTERY_THRESHOLD) * 50)
        else:
            readiness = 0
        
        return {
            'topic': topic,
            'status': status,
            'theta': round(theta, 2),
            'readiness_score': round(readiness, 1),
            'prerequisites_met': prereqs_met,
            'prerequisites': prereqs,
            'can_start': status in ["opened", "mastered"]
        }

