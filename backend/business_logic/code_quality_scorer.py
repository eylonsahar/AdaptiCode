"""
Code quality scoring module using LLM.

This module provides functionality to score code quality using LLM
while keeping the scoring logic separate from the LLM gateway.
"""
import json
import os
from typing import Dict, Optional, Tuple
from backend.business_logic.llm_gateway import LLMGateway


class CodeQualityScorer:
    """
    Scores code quality using LLM with externalized prompts.
    """
    
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        """
        Initialize code quality scorer.
        
        Args:
            llm_gateway: Optional LLM gateway instance
        """
        self.llm_gateway = llm_gateway or LLMGateway()
        self.prompt_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', 'code_quality.txt')
    
    def load_prompt(self) -> str:
        """
        Load the code quality scoring prompt from external file.
        
        Returns:
            The prompt text as string
        """
        try:
            with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            # Fallback prompt if file not found
            return "You are an experienced Python technical interviewer. Score the following code from 0-10 and provide a brief explanation."
        except Exception as e:
            print(f"Error loading prompt: {e}")
            return "You are an experienced Python technical interviewer. Score the following code from 0-10 and provide a brief explanation."
    
    def score_code_quality(self, user_code: str, question_context: Optional[str] = None) -> Dict[str, str]:
        """
        Score code quality using LLM.
        
        Args:
            user_code: The user's Python code to evaluate
            question_context: Optional context about the question/problem
            
        Returns:
            Dictionary with 'Score' and 'Explanation' keys
        """
        if not user_code or not user_code.strip():
            return {
                "Score": "0/10",
                "Explanation": "No code provided to evaluate."
            }
        
        # Load the prompt
        base_prompt = self.load_prompt()
        
        # Build the full prompt with user code
        full_prompt = f"{base_prompt}\n\nUser Code:\n```python\n{user_code}\n```"
        
        if question_context:
            full_prompt += f"\n\nQuestion Context:\n{question_context}"
        
        # Get LLM response
        try:
            response = self.llm_gateway.generic_llm_call(full_prompt)
            
            # Try to parse JSON response
            try:
                # Look for JSON in the response
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:-3]  # Remove ```json and ```
                elif response.startswith('```'):
                    response = response[3:-3]  # Remove ``` and ```
                
                parsed = json.loads(response)
                
                # Ensure required keys exist
                result = {
                    "Score": parsed.get("Score", "N/A"),
                    "Explanation": parsed.get("Explanation", "No explanation provided.")
                }
                
                return result
                
            except json.JSONDecodeError:
                # Fallback: try to extract score and explanation from text
                lines = response.split('\n')
                score = "N/A"
                explanation = response
                
                for line in lines:
                    if 'score' in line.lower() or '/' in line:
                        score = line.strip()
                        break
                
                return {
                    "Score": score,
                    "Explanation": explanation[:200] + "..." if len(explanation) > 200 else explanation
                }
                
        except Exception as e:
            print(f"Error in code quality scoring: {e}")
            return {
                "Score": "Error",
                "Explanation": f"Unable to score code due to error: {str(e)}"
            }
    
    def get_numeric_score(self, score_string: str) -> float:
        """
        Extract numeric score from score string like "7/10".
        
        Args:
            score_string: Score string from LLM response
            
        Returns:
            Numeric score as float
        """
        try:
            if '/' in score_string:
                numerator = score_string.split('/')[0].strip()
                return float(numerator)
            else:
                # Try to extract number from string
                import re
                match = re.search(r'\d+(\.\d+)?', score_string)
                if match:
                    return float(match.group())
        except (ValueError, AttributeError):
            pass
        
        return 0.0
