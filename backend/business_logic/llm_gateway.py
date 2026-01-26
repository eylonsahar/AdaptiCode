"""
LLM Gateway for generating personalized explanations.

Supports multiple LLM providers (OpenAI, Anthropic, Gemini, local models)
and can use RAG for context-aware explanations.
"""
from typing import Dict, List, Optional
from backend.data.models import Question
from backend.config import Config


class LLMGateway:
    """
    Gateway to Large Language Models for generating explanations.
    """

    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.temperature = Config.LLM_TEMPERATURE
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.api_key = Config.get_llm_api_key()

        self.client = self._initialize_client()

    # ------------------------------------------------------------------
    # Client initialization
    # ------------------------------------------------------------------

    def _initialize_client(self):
        if self.provider == "openai":
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            try:
                import openai
                openai.api_key = self.api_key
                return openai
            except ImportError:
                raise RuntimeError("openai package not installed")

        elif self.provider == "anthropic":
            if not self.api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            try:
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("anthropic package not installed")

        elif self.provider == "gemini":
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            try:
                from google import genai
                return genai.Client(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("google-genai package not installed")
                
        elif self.provider == "groq":
            if not self.api_key:
                raise RuntimeError("GROQ_API_KEY is not set")
            try:
                import groq
                return groq.Groq(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("groq package not installed. Install with: pip install groq")

        elif self.provider == "local":
            try:
                import requests
                return requests
            except ImportError:
                raise RuntimeError("requests package not installed")

        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    # ------------------------------------------------------------------
    # Core explanation flow
    # ------------------------------------------------------------------

    def generate_explanation(
        self,
        question: Question,
        user_theta: float,
        context: Optional[Dict] = None,
    ) -> str:
        prompt = self._build_explanation_prompt(question, user_theta, context)

        try:
            if self.provider == "openai":
                return self._generate_openai(prompt)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt)
            elif self.provider == "gemini":
                return self._generate_gemini(prompt)
            elif self.provider == "groq":
                return self._generate_groq(prompt)
            elif self.provider == "local":
                return self._generate_local(prompt)
        except Exception as e:
            print(f"LLM error: {e}")

        return self._generate_fallback_explanation(question)

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_explanation_prompt(
        self,
        question: Question,
        user_theta: float,
        context: Optional[Dict],
    ) -> str:
        if user_theta < -1:
            level = "beginner"
        elif user_theta < 1:
            level = "intermediate"
        else:
            level = "advanced"

        if question.b < -1:
            difficulty = "easy"
        elif question.b < 1:
            difficulty = "medium"
        else:
            difficulty = "hard"

        prompt = f"""You are a helpful programming tutor teaching recursion.

Question: {question.name}
Topic: {question.topic}
Difficulty: {difficulty}
Student Level: {level}

Problem Description:
{question.description}
"""

        if context:
            if context.get("previous_attempts"):
                prompt += f"\nPrevious attempts: {context['previous_attempts']}\n"
            if context.get("common_errors"):
                prompt += f"\nCommon errors: {', '.join(context['common_errors'])}\n"
            if context.get("failed_tests"):
                prompt += "\nSome test cases failed.\n"

        prompt += """
Instructions:
1. Explain the key recursive idea
2. Give a hint (no full solution)
3. Mention common pitfalls
4. Encourage the student

Limit to 200 words.
"""

        return prompt.strip()

    # ------------------------------------------------------------------
    # Provider-specific implementations
    # ------------------------------------------------------------------

    def _generate_openai(self, prompt: str) -> str:
        response = self.client.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a programming tutor."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()

    def _generate_anthropic(self, prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    def _generate_gemini(self, prompt: str) -> str:
        for _ in range(2):  # retry for free-tier instability
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
        return "Unable to generate explanation at this time."

    def _generate_groq(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful programming tutor."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()

    def _generate_local(self, prompt: str) -> str:
        response = self.client.post(
            "http://localhost:11434/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        return "Local model failed."

    # ------------------------------------------------------------------
    # Fallback logic
    # ------------------------------------------------------------------

    def _generate_fallback_explanation(self, question: Question) -> str:
        hints = {
            "Recursion Basics": (
                "Identify the base case and the recursive step. "
                "Ensure each call moves closer to the base case."
            ),
            "Backtracking": (
                "Try a choice, explore recursively, and undo the choice if it fails."
            ),
            "Dynamic Programming & Advanced Recursion": (
                "Look for overlapping subproblems and consider memoization."
            ),
        }

        hint = hints.get(
            question.topic,
            "Break the problem into smaller subproblems and define a clear base case.",
        )

        return f"""
{question.name}

Key Idea:
{hint}

Tip:
Write the base case first, then define the recursive step.
""".strip()

    # ------------------------------------------------------------------
    # Generic call
    # ------------------------------------------------------------------

    def generate_hint(
        self,
        question: Question,
        user_code: str,
        hint_number: int
    ) -> str:
        """
        Generate a helpful hint for the question without revealing the solution.
        
        Args:
            question: Question object
            user_code: User's current code attempt
            hint_number: Which hint this is (1-3)
            
        Returns:
            Hint text
        """
        system_prompt = """You are a helpful programming tutor. Your job is to provide hints that guide students toward the solution WITHOUT giving away the answer.

IMPORTANT RULES:
1. DO NOT provide the complete solution or code
2. DO NOT write the recursive function for them
3. DO provide conceptual guidance and direction
4. DO ask guiding questions that help them think
5. DO point out what they might be missing in their approach
6. Keep hints concise (2-3 sentences max)"""

        # Escalate hint helpfulness based on hint number
        if hint_number == 1:
            hint_level = "Give a very gentle hint about the general approach or concept they should consider."
        elif hint_number == 2:
            hint_level = "Give a more specific hint about what their code might be missing or what pattern to use."
        else:  # hint_number == 3
            hint_level = "Give a detailed hint about the key insight or technique needed, but still don't write the code for them."

        prompt = f"""Question: {question.name}
Topic: {question.topic}
Description: {question.description}

Student's Current Code:
```python
{user_code}
```

This is hint #{hint_number} of 3.
{hint_level}

Provide a helpful hint (2-3 sentences max):"""

        try:
            hint = self.generic_llm_call(prompt, system_prompt)
            return hint if hint else self._generate_fallback_hint(question, hint_number)
        except Exception as e:
            print(f"Error generating hint: {e}")
            return self._generate_fallback_hint(question, hint_number)

    def select_question_with_rag(
        self,
        candidate_questions: List[Question],
        student_theta: float,
        topic: str,
        recent_performance: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Use LLM to select the best question from candidates based on student model.
        
        Args:
            candidate_questions: List of 3 candidate questions (from LRU)
            student_theta: Student's current ability level
            topic: Current topic
            recent_performance: Optional dict with recent performance stats
            
        Returns:
            Dict with 'selected_question' (name) and 'explanation' (max 3 sentences)
        """
        if not candidate_questions:
            return {
                'selected_question': None,
                'explanation': 'No questions available.'
            }
        
        # If only one question, return it with simple explanation
        if len(candidate_questions) == 1:
            return {
                'selected_question': candidate_questions[0].name,
                'explanation': 'This is the next question in your learning path.'
            }
        
        # Build student profile summary
        if student_theta < -1:
            level = "beginner"
        elif student_theta < 1:
            level = "intermediate"
        else:
            level = "advanced"
        
        # Build performance summary
        perf_summary = ""
        if recent_performance:
            total = recent_performance.get('total_attempts', 0)
            correct = recent_performance.get('correct_attempts', 0)
            if total > 0:
                success_rate = (correct / total) * 100
                perf_summary = f"Recent success rate: {success_rate:.0f}% ({correct}/{total} correct)"
        
        # Build candidate descriptions
        candidates_text = ""
        for i, q in enumerate(candidate_questions, 1):
            diff_delta = q.b - student_theta
            if diff_delta < -0.5:
                rel_diff = "easier than current level"
            elif diff_delta > 0.5:
                rel_diff = "harder than current level"
            else:
                rel_diff = "well-matched to current level"
            
            desc_preview = q.description[:150] + "..." if len(q.description) > 150 else q.description
            candidates_text += f"{i}. **{q.name}** (Difficulty: {q.b:.2f}, {rel_diff})\n   Description: {desc_preview}\n\n"
        
        system_prompt = """You are an adaptive learning system selecting the best question for a student.
Your goal is to maximize learning while maintaining appropriate challenge level.

IMPORTANT: 
- Respond ONLY with valid JSON
- Keep explanation to exactly 3 short sentences
- Focus on why this question NOW and what they'll learn"""

        prompt = f"""Student Profile:
- Current ability (theta): {student_theta:.2f} ({level} level)
- Topic: {topic}
{f"- {perf_summary}" if perf_summary else ""}

Candidate Questions:
{candidates_text}

Select the BEST question for this student right now. Consider:
1. Optimal difficulty match (not too easy, not too hard)
2. Learning progression and skill building
3. Maintaining engagement and motivation

Respond with JSON in this exact format:
{{
  "selected_question": "question_name",
  "explanation": "Three short sentences: why this question, what makes it appropriate now, and what the student will learn from it."
}}"""

        try:
            response = self.generic_llm_call(prompt, system_prompt)
            result = self._parse_question_selection_response(response, candidate_questions)
            return result
        except Exception as e:
            print(f"Error in RAG question selection: {e}")
            # Fallback: select middle difficulty question
            return self._fallback_question_selection(candidate_questions, student_theta)

    def _parse_question_selection_response(
        self,
        response: str,
        candidate_questions: List[Question]
    ) -> Dict[str, str]:
        """Parse LLM response for question selection."""
        import json
        
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
            
            selected_name = parsed.get('selected_question', '')
            explanation = parsed.get('explanation', '')
            
            # Validate selected question exists in candidates
            valid_names = [q.name for q in candidate_questions]
            if selected_name not in valid_names:
                # Try to find partial match
                for name in valid_names:
                    if selected_name.lower() in name.lower() or name.lower() in selected_name.lower():
                        selected_name = name
                        break
                else:
                    # No match found, use first candidate
                    selected_name = candidate_questions[0].name
            
            # Ensure explanation is concise (max 3 sentences)
            sentences = explanation.split('.')
            if len(sentences) > 3:
                explanation = '. '.join(sentences[:3]) + '.'
            
            return {
                'selected_question': selected_name,
                'explanation': explanation.strip()
            }
            
        except Exception as e:
            print(f"Error parsing question selection response: {e}")
            return self._fallback_question_selection(candidate_questions, 0)

    def _fallback_question_selection(
        self,
        candidate_questions: List[Question],
        student_theta: float
    ) -> Dict[str, str]:
        """Fallback question selection if LLM fails."""
        # Select question with difficulty closest to student ability
        best_question = min(
            candidate_questions,
            key=lambda q: abs(q.b - student_theta)
        )
        
        return {
            'selected_question': best_question.name,
            'explanation': 'This question matches your current skill level and will help you progress in your learning journey.'
        }

    def _generate_fallback_hint(self, question: Question, hint_number: int) -> str:
        """Generate a simple fallback hint if LLM fails."""
        hints = {
            1: "Think about the base case first. What's the simplest input that doesn't need recursion?",
            2: "Consider how you can break down the problem into a smaller version of itself.",
            3: "Make sure your recursive call is moving toward the base case with each step."
        }
        return hints.get(hint_number, "Try breaking the problem into smaller pieces.")

    def generic_llm_call(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            if self.provider == "gemini":
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=full_prompt,
                )
                return response.text.strip() if response.text else ""

            if self.provider == "openai":
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content.strip()

            if self.provider == "groq":
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Generic LLM call failed: {e}")

        return ""
