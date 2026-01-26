"""
Pass/Fail Evaluator using LLM.

This module provides functionality to evaluate whether a student has truly
mastered a recursion problem based on test results, code quality, and context.
"""
import json
import os
import time
from typing import Dict, List, Optional, Any
from backend.business_logic.llm_gateway import LLMGateway
from backend.data.models import Question


class PassFailEvaluator:
    """
    Evaluates pass/fail decisions using LLM with externalized prompts.
    """
    
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        """
        Initialize pass/fail evaluator.
        
        Args:
            llm_gateway: Optional LLM gateway instance
        """
        self.llm_gateway = llm_gateway or LLMGateway()
        self.prompt_file_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'prompts', 'pass_fail_decision.txt'
        )
    
    def load_prompt(self) -> str:
        """
        Load the pass/fail decision prompt from external file.
        
        Returns:
            The prompt text as string
        """
        try:
            with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            # Fallback prompt if file not found
            return self._get_fallback_prompt()
        except Exception as e:
            print(f"Error loading pass/fail prompt: {e}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """
        Fallback prompt if external file cannot be loaded.
        
        Returns:
            Basic fallback prompt
        """
        return """You are evaluating a student's recursion solution.
Return JSON with:
- decision: 0 (fail) or 1 (pass)
- explanation: Brief justification

Pass if: ≥80% tests passed AND code uses recursion properly.
Fail if: No recursion used OR <70% tests passed OR poor recursive design.

Format: {"decision": 0 or 1, "explanation": "..."}"""
    
    def evaluate_pass_fail(
        self,
        user_code: str,
        question: Question,
        hidden_pass_rate: float,
        code_quality_score: str,
        code_quality_explanation: str,
        theta_before: float,
        hidden_tests: List[Dict],
        subjective_feedback: Optional[Dict] = None,
        hints_used: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate whether the student should pass or fail.
        
        Args:
            user_code: The user's Python code
            question: Question object with metadata
            hidden_pass_rate: Percentage of hidden tests passed (0.0 to 1.0)
            code_quality_score: Score string like "7/10"
            code_quality_explanation: Explanation of code quality score
            theta_before: User's skill level before this question
            hidden_tests: List of hidden test results
            subjective_feedback: Optional user feedback dict
            hints_used: Number of hints used (0-3)
            
        Returns:
            Dictionary with 'decision' (0 or 1) and 'explanation' keys
        """
        # Automatic fail if hints were used
        if hints_used > 0:
            return {
                "decision": 0,
                "explanation": f"Not Passed: You used {hints_used} hint(s). To demonstrate mastery, you must solve the problem independently without hints."
            }
        
        # Quick validation
        if not user_code or not user_code.strip():
            return {
                "decision": 0,
                "explanation": "Not Passed: No code provided to evaluate."
            }
        
        # Build the evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(
            user_code=user_code,
            question=question,
            hidden_pass_rate=hidden_pass_rate,
            code_quality_score=code_quality_score,
            code_quality_explanation=code_quality_explanation,
            theta_before=theta_before,
            hidden_tests=hidden_tests,
            subjective_feedback=subjective_feedback
        )
        
        # Load base prompt
        base_prompt = self.load_prompt()
        
        # Combine prompts
        full_prompt = f"{base_prompt}\n\n{evaluation_prompt}"
        
        # Get LLM response
        try:
            # Small delay to help with rate limiting
            time.sleep(0.5)
            
            response = self.llm_gateway.generic_llm_call(full_prompt)
            
            # Parse JSON response
            result = self._parse_llm_response(response)
            
            # Validate result
            if self._is_valid_result(result):
                return result
            else:
                # Fallback if invalid
                return self._generate_fallback_decision(
                    hidden_pass_rate, code_quality_score
                )
                
        except Exception as e:
            print(f"Error in pass/fail evaluation: {e}")
            return self._generate_fallback_decision(
                hidden_pass_rate, code_quality_score
            )
    
    def _build_evaluation_prompt(
        self,
        user_code: str,
        question: Question,
        hidden_pass_rate: float,
        code_quality_score: str,
        code_quality_explanation: str,
        theta_before: float,
        hidden_tests: List[Dict],
        subjective_feedback: Optional[Dict]
    ) -> str:
        """
        Build the evaluation prompt with all context.
        
        Args:
            All parameters from evaluate_pass_fail
            
        Returns:
            Formatted prompt string
        """
        # Calculate test statistics
        total_hidden = len(hidden_tests)
        passed_hidden = sum(1 for t in hidden_tests if t.get('passed', False))
        hidden_pass_percentage = int(hidden_pass_rate * 100)
        
        # Determine skill level description
        if theta_before < -1:
            skill_level = "Beginner"
        elif theta_before < 1:
            skill_level = "Intermediate"
        else:
            skill_level = "Advanced"
        
        # Determine difficulty description
        beta = question.beta
        if beta < -1:
            difficulty = "Easy"
        elif beta < 1:
            difficulty = "Medium"
        else:
            difficulty = "Hard"
        
        # Build prompt
        prompt = f"""📋 Submission to Evaluate

**Question Information:**
- Name: {question.name}
- Topic: {question.topic}
- Difficulty (beta): {beta:.2f} ({difficulty})
- Description: {question.description[:200]}{"..." if len(question.description) > 200 else ""}

**Student Performance:**
- Hidden Test Pass Rate: {hidden_pass_percentage}% ({passed_hidden}/{total_hidden} tests passed)
- Code Quality Score: {code_quality_score}
- Code Quality Explanation: {code_quality_explanation}

**Student Context:**
- Skill Level (theta): {theta_before:.2f} ({skill_level})

**User's Code:**
```python
{user_code}
```
"""
        
        # Add subjective feedback if available
        if subjective_feedback:
            prompt += "\n**Student's Self-Reported Feedback:**\n"
            
            difficulty_rating = subjective_feedback.get('difficulty_rating')
            if difficulty_rating:
                prompt += f"- Difficulty Rating: {difficulty_rating}\n"
            
            pain_points = subjective_feedback.get('pain_points', [])
            if pain_points:
                if isinstance(pain_points, list):
                    pain_points_str = ", ".join(pain_points)
                else:
                    pain_points_str = str(pain_points)
                prompt += f"- Pain Points: {pain_points_str}\n"
            
            self_feelings = subjective_feedback.get('self_feelings', '')
            if self_feelings:
                prompt += f"- Self-Assessment: {self_feelings}\n"
        
        # Add failed test details if any
        failed_tests = [t for t in hidden_tests if not t.get('passed', False)]
        if failed_tests and len(failed_tests) <= 3:
            prompt += "\n**Failed Test Details:**\n"
            for i, test in enumerate(failed_tests[:3], 1):
                prompt += f"- Test {i}: {test.get('error', 'Failed')}\n"
        
        prompt += "\n---\n\nBased on the above information, make your pass/fail decision."
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract decision and explanation.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Dictionary with 'decision' and 'explanation'
        """
        try:
            # Clean response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith('```json'):
                response = response[7:]
            elif response.startswith('```'):
                response = response[3:]
            
            if response.endswith('```'):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            parsed = json.loads(response)
            
            # Extract decision and explanation
            decision = parsed.get("decision")
            explanation = parsed.get("explanation", "")
            
            # Validate decision is 0 or 1
            if decision not in [0, 1]:
                # Try to convert
                if isinstance(decision, bool):
                    decision = 1 if decision else 0
                elif isinstance(decision, (int, float)):
                    decision = 1 if decision > 0.5 else 0
                else:
                    raise ValueError("Invalid decision value")
            
            return {
                "decision": int(decision),
                "explanation": str(explanation)
            }
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Try to extract decision from text
            return self._extract_decision_from_text(response)
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return self._extract_decision_from_text(response)
    
    def _extract_decision_from_text(self, text: str) -> Dict[str, Any]:
        """
        Fallback: Extract decision from non-JSON text.
        
        Args:
            text: Raw text response
            
        Returns:
            Best-effort dictionary with decision and explanation
        """
        text_lower = text.lower()
        
        # Look for decision indicators
        if "decision: 1" in text_lower or "\"decision\": 1" in text_lower:
            decision = 1
        elif "decision: 0" in text_lower or "\"decision\": 0" in text_lower:
            decision = 0
        elif "passed" in text_lower and "not passed" not in text_lower:
            decision = 1
        elif "not passed" in text_lower or "fail" in text_lower:
            decision = 0
        else:
            # Default to fail if unclear
            decision = 0
        
        return {
            "decision": decision,
            "explanation": text[:300] if text else "Unable to generate explanation."
        }
    
    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """
        Check if result is valid.
        
        Args:
            result: Result dictionary
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(result, dict):
            return False
        
        if "decision" not in result or "explanation" not in result:
            return False
        
        if result["decision"] not in [0, 1]:
            return False
        
        if not isinstance(result["explanation"], str) or not result["explanation"].strip():
            return False
        
        return True
    
    def _generate_fallback_decision(
        self,
        hidden_pass_rate: float,
        code_quality_score: str
    ) -> Dict[str, Any]:
        """
        Generate a rule-based fallback decision if LLM fails.
        
        Args:
            hidden_pass_rate: Pass rate (0.0 to 1.0)
            code_quality_score: Score string like "7/10"
            
        Returns:
            Dictionary with decision and explanation
        """
        # Extract numeric quality score
        quality_numeric = self._extract_numeric_score(code_quality_score)
        
        # Rule-based decision
        if quality_numeric == 0:
            # No recursion used
            return {
                "decision": 0,
                "explanation": "Not Passed: Code does not use recursion. This is a recursion learning platform - please rewrite using a recursive approach."
            }
        elif hidden_pass_rate >= 0.8 and quality_numeric >= 5:
            return {
                "decision": 1,
                "explanation": f"Passed: {int(hidden_pass_rate * 100)}% tests passed with code quality {code_quality_score}. Demonstrates adequate recursion mastery."
            }
        elif hidden_pass_rate < 0.7 or quality_numeric < 5:
            return {
                "decision": 0,
                "explanation": f"Not Passed: {int(hidden_pass_rate * 100)}% tests passed, code quality {code_quality_score}. More practice needed to master this recursion pattern."
            }
        else:
            # Borderline - lean toward retry
            return {
                "decision": 0,
                "explanation": f"Not Passed: {int(hidden_pass_rate * 100)}% tests passed (borderline), code quality {code_quality_score}. Recommend practicing this question again to solidify understanding."
            }
    
    def _extract_numeric_score(self, score_string: str) -> float:
        """
        Extract numeric score from string like "7/10".
        
        Args:
            score_string: Score string
            
        Returns:
            Numeric score (0-10)
        """
        try:
            if '/' in score_string:
                numerator = score_string.split('/')[0].strip()
                return float(numerator)
            else:
                # Try to extract number
                import re
                match = re.search(r'\d+(\.\d+)?', score_string)
                if match:
                    return float(match.group())
        except (ValueError, AttributeError):
            pass
        
        return 0.0

