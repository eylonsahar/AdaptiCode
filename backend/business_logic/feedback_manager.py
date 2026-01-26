"""
Feedback Manager for processing subjective and objective feedback.

Combines user's subjective feedback (difficulty rating, confidence)
with objective metrics (test results, time, code quality) to enhance
the learning model.
"""
from typing import Dict, Optional
from backend.data.models import Question
from backend.config import Config


class FeedbackManager:
    """
    Manages feedback processing and integration.
    
    Combines:
    - Objective metrics: test pass rate, time taken, code quality
    - Subjective feedback: perceived difficulty, confidence level
    """
    
    def __init__(self):
        """Initialize feedback manager."""
        self.objective_weight = Config.OBJECTIVE_WEIGHT
        self.subjective_weight = Config.SUBJECTIVE_WEIGHT
    
    def process_feedback(self, question: Question, test_results: Dict,
                        time_taken: float, subjective_feedback: Optional[Dict] = None) -> Dict:
        """
        Process all feedback and generate combined assessment.
        
        Args:
            question: Question that was attempted
            test_results: Results from test runner
            time_taken: Time taken in seconds
            subjective_feedback: Optional user feedback
            
        Returns:
            Combined feedback assessment
        """
        # Extract objective metrics
        objective = self._process_objective_metrics(test_results, time_taken)
        
        # Extract subjective metrics
        subjective = self._process_subjective_feedback(subjective_feedback)
        
        # Combine metrics
        combined = self._combine_metrics(objective, subjective)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            question, objective, subjective, combined
        )
        
        return {
            'objective_metrics': objective,
            'subjective_metrics': subjective,
            'combined_assessment': combined,
            'recommendations': recommendations
        }
    
    def _process_objective_metrics(self, test_results: Dict, time_taken: float) -> Dict:
        """
        Process objective metrics from test results and timing.
        
        Args:
            test_results: Test execution results
            time_taken: Time in seconds
            
        Returns:
            Processed objective metrics
        """
        if not test_results.get('success'):
            return {
                'success': False,
                'pass_rate': 0.0,
                'time_taken': time_taken,
                'performance_score': 0.0,
                'error': test_results.get('error', 'Unknown error')
            }
        
        pass_rate = test_results.get('pass_rate', 0.0)
        all_passed = test_results.get('all_passed', False)
        
        # Calculate performance score (0-1)
        # Based on pass rate only (time is no longer a factor)
        time_score = 1.0  # Always give full points for time
        performance_score = pass_rate  # Simple pass rate determines score
        
        return {
            'success': True,
            'pass_rate': pass_rate,
            'all_passed': all_passed,
            'passed_tests': test_results.get('passed_tests', 0),
            'total_tests': test_results.get('total_tests', 0),
            'time_taken': time_taken,
            'time_score': time_score,
            'performance_score': performance_score
        }
    
    def _calculate_time_score(self, time_taken: float) -> float:
        """
        Calculate time efficiency score.
        
        Args:
            time_taken: Time in seconds
            
        Returns:
            Score from 0 to 1 (higher is better)
        """
        """
        Calculate time efficiency score.
        
        Args:
            time_taken: Time in seconds
            
        Returns:
            Always returns 1.0 as time is no longer tracked.
        """
        return 1.0
    
    def _process_subjective_feedback(self, feedback: Optional[Dict]) -> Dict:
        """
        Process subjective feedback from user.
        
        Args:
            feedback: User's subjective feedback
            
        Returns:
            Processed subjective metrics
        """
        if not feedback:
            return {
                'provided': False,
                'difficulty_rating': None,
                'confidence_level': None,
                'subjective_score': 0.5  # Neutral if not provided
            }
        
        # Extract ratings (assumed to be on 1-5 scale)
        difficulty = feedback.get('difficulty_rating', 3)  # 1=easy, 5=hard
        confidence = feedback.get('confidence_level', 3)   # 1=low, 5=high
        
        # Normalize to 0-1 scale
        difficulty_norm = (difficulty - 1) / 4  # 0=easy, 1=hard
        confidence_norm = (confidence - 1) / 4  # 0=low, 1=high
        
        # Calculate subjective score
        # High confidence and appropriate difficulty = good
        # Inverse difficulty for score (easier = better for confidence)
        subjective_score = confidence_norm * 0.7 + (1 - difficulty_norm) * 0.3
        
        return {
            'provided': True,
            'difficulty_rating': difficulty,
            'confidence_level': confidence,
            'difficulty_normalized': difficulty_norm,
            'confidence_normalized': confidence_norm,
            'subjective_score': subjective_score,
            'notes': feedback.get('notes', '')
        }
    
    def _combine_metrics(self, objective: Dict, subjective: Dict) -> Dict:
        """
        Combine objective and subjective metrics.
        
        Args:
            objective: Objective metrics
            subjective: Subjective metrics
            
        Returns:
            Combined assessment
        """
        obj_score = objective.get('performance_score', 0.0)
        subj_score = subjective.get('subjective_score', 0.5)
        
        # Weighted combination
        if subjective.get('provided'):
            combined_score = (obj_score * self.objective_weight + 
                            subj_score * self.subjective_weight)
        else:
            # If no subjective feedback, use only objective
            combined_score = obj_score
        
        # Determine overall assessment
        if combined_score >= 0.8:
            assessment = "excellent"
        elif combined_score >= 0.6:
            assessment = "good"
        elif combined_score >= 0.4:
            assessment = "fair"
        else:
            assessment = "needs_improvement"
        
        # Check for discrepancies between objective and subjective
        discrepancy = None
        if subjective.get('provided'):
            diff = abs(obj_score - subj_score)
            if diff > 0.3:
                if obj_score > subj_score:
                    discrepancy = "overestimating_difficulty"
                else:
                    discrepancy = "underestimating_difficulty"
        
        return {
            'combined_score': combined_score,
            'assessment': assessment,
            'discrepancy': discrepancy,
            'objective_weight_used': self.objective_weight if subjective.get('provided') else 1.0,
            'subjective_weight_used': self.subjective_weight if subjective.get('provided') else 0.0
        }
    
    def _generate_recommendations(self, question: Question, objective: Dict,
                                 subjective: Dict, combined: Dict) -> list:
        """
        Generate personalized recommendations based on feedback.
        
        Args:
            question: Question attempted
            objective: Objective metrics
            subjective: Subjective metrics
            combined: Combined assessment
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Based on test results
        if not objective.get('all_passed'):
            pass_rate = objective.get('pass_rate', 0)
            if pass_rate == 0:
                recommendations.append(
                    "Review the problem description carefully and ensure you understand the requirements."
                )
            elif pass_rate < 0.5:
                recommendations.append(
                    "You're on the right track, but there are some edge cases to handle. "
                    "Check the failed test cases for patterns."
                )
            else:
                recommendations.append(
                    "Almost there! Review the hidden test cases - they often test boundary conditions."
                )
        
            pass
        
        # Based on subjective feedback
        if subjective.get('provided'):
            difficulty = subjective.get('difficulty_rating', 3)
            confidence = subjective.get('confidence_level', 3)
            
            if difficulty >= 4 and confidence <= 2:
                recommendations.append(
                    "This problem was challenging for you. Consider reviewing the concept fundamentals "
                    "before attempting similar problems."
                )
            elif difficulty <= 2 and confidence >= 4:
                recommendations.append(
                    "Great job! You found this easy. You're ready for more challenging problems in this topic."
                )
        
        # Based on discrepancy
        discrepancy = combined.get('discrepancy')
        if discrepancy == "overestimating_difficulty":
            recommendations.append(
                "You did better than you thought! Trust your skills more."
            )
        elif discrepancy == "underestimating_difficulty":
            recommendations.append(
                "This was trickier than it seemed. Pay attention to edge cases and problem constraints."
            )
        
        # General encouragement
        if combined.get('assessment') == 'excellent':
            recommendations.append("Excellent work! Keep up the great progress.")
        elif combined.get('assessment') == 'good':
            recommendations.append("Good job! You're making solid progress.")
        
        return recommendations
    
    def adjust_difficulty_perception(self, question: Question, 
                                    actual_performance: float,
                                    perceived_difficulty: float) -> Dict:
        """
        Analyze the gap between actual performance and perceived difficulty.
        
        Args:
            question: Question attempted
            actual_performance: Actual performance score (0-1)
            perceived_difficulty: User's difficulty rating (0-1, normalized)
            
        Returns:
            Analysis of perception vs reality
        """
        # Calculate expected difficulty based on IRT parameters
        # Higher beta = harder question
        expected_difficulty = (question.b + 4) / 8  # Normalize to 0-1
        
        # Compare all three
        perception_gap = perceived_difficulty - expected_difficulty
        performance_gap = expected_difficulty - actual_performance
        
        analysis = {
            'expected_difficulty': expected_difficulty,
            'perceived_difficulty': perceived_difficulty,
            'actual_performance': actual_performance,
            'perception_gap': perception_gap,
            'performance_gap': performance_gap
        }
        
        # Interpretation
        if abs(perception_gap) < 0.2:
            analysis['perception_accuracy'] = 'accurate'
        elif perception_gap > 0:
            analysis['perception_accuracy'] = 'overestimating'
        else:
            analysis['perception_accuracy'] = 'underestimating'
        
        return analysis
    
    def should_adjust_theta(self, objective: Dict, subjective: Dict) -> bool:
        """
        Determine if theta should be adjusted based on feedback.
        
        Args:
            objective: Objective metrics
            subjective: Subjective metrics
            
        Returns:
            True if theta adjustment is warranted
        """
        # Always adjust based on objective results
        if objective.get('success'):
            return True
        
        # Don't adjust if there was an error
        return False
    
    def get_feedback_summary(self, feedback_result: Dict) -> str:
        """
        Generate human-readable feedback summary.
        
        Args:
            feedback_result: Result from process_feedback
            
        Returns:
            Summary string
        """
        combined = feedback_result['combined_assessment']
        objective = feedback_result['objective_metrics']
        
        if not objective.get('success'):
            return f"Error: {objective.get('error', 'Unknown error')}"
        
        assessment = combined['assessment'].replace('_', ' ').title()
        score = combined['combined_score']
        
        summary = f"{assessment} (Score: {score:.2f})\n"
        
        if objective.get('all_passed'):
            summary += "✓ All tests passed!\n"
        else:
            passed = objective.get('passed_tests', 0)
            total = objective.get('total_tests', 0)
            summary += f"Tests: {passed}/{total} passed\n"
        
        # Time display removed from summary
        # summary += f"Time: {time_taken:.1f}s\n"
        
        return summary

