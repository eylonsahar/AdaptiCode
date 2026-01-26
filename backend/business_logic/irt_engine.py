"""
Item Response Theory (IRT) Engine.

Implements the 3-Parameter Logistic (3PL) model for adaptive question selection
and Expected A Posteriori (EAP) method for ability estimation.

Based on the paper: "On the impact of adaptive test question selection for learning efficiency"
"""
import math
from dataclasses import dataclass
import numpy as np
from typing import List, Tuple, Dict, Optional, Sequence
from backend.data.models import Question, AnswerRecord
from backend.config import Config
from backend.utils import sigmoid, normal_pdf, safe_log


@dataclass(frozen=True)
class _IRTItemParams:
    """Lightweight IRT item params adapter for EAP updates."""

    alpha: float
    beta: float
    c: float

    @property
    def a(self) -> float:
        return self.alpha

    @property
    def b(self) -> float:
        return self.beta


class IRTEngine:
    """
    IRT Engine implementing 3PL model and EAP estimation.
    
    The 3PL model:
    P(θ) = c + (1 - c) / (1 + e^(-a(θ - b)))
    
    Where:
    - θ (theta): ability parameter of the learner
    - a (alpha): discrimination parameter of the question
    - b (beta): difficulty parameter of the question
    - c: guessing parameter (probability of guessing correctly)
    """
    
    def __init__(self):
        """Initialize IRT engine with configuration."""
        self.prior_mean = Config.EAP_PRIOR_MEAN
        self.prior_std = Config.EAP_PRIOR_STD
        self.n_quadrature = Config.EAP_QUADRATURE_POINTS
        self.theta_min = Config.EAP_THETA_MIN
        self.theta_max = Config.EAP_THETA_MAX

        self.answer_history_window = Config.EAP_ANSWER_HISTORY_WINDOW
        self.min_answers_for_update = Config.EAP_MIN_ANSWERS_FOR_UPDATE
        
        # Pre-compute quadrature points and weights for EAP
        self.quadrature_points = np.linspace(
            self.theta_min, 
            self.theta_max, 
            self.n_quadrature
        )
    
    def probability_correct(self, theta: float, question: Question) -> float:
        """
        Calculate probability of correct answer using 3PL model.
        
        P(θ) = c + (1 - c) / (1 + e^(-a(θ - b)))
        
        Args:
            theta: Ability parameter
            question: Question with IRT parameters
            
        Returns:
            Probability of correct answer (0 to 1)
        """
        a = question.a  # discrimination
        b = question.b  # difficulty
        c = question.c  # guessing
        
        # 3PL formula
        exponent = -a * (theta - b)
        
        # Prevent overflow
        if exponent > 500:
            return c
        if exponent < -500:
            return 1.0
        
        prob = c + (1 - c) / (1 + math.exp(exponent))
        
        return max(0.0, min(1.0, prob))
    
    def information(self, theta: float, question: Question) -> float:
        """
        Calculate Fisher information for a question at given ability level.
        
        Information indicates how much the question can tell us about
        the learner's ability at that level.
        
        For 3PL model:
        I(θ) = a² * (P'(θ))² / (P(θ) * (1 - P(θ)))
        
        Where P'(θ) is the derivative of P(θ).
        
        Args:
            theta: Ability parameter
            question: Question with IRT parameters
            
        Returns:
            Information value (higher = more informative)
        """
        a = question.a
        b = question.b
        c = question.c
        
        # Calculate probability
        p = self.probability_correct(theta, question)
        
        # Avoid division by zero
        if p <= 0.001 or p >= 0.999:
            return 0.0
        
        # Calculate derivative of P with respect to theta
        # P'(θ) = a * (1 - c) * e^(-a(θ-b)) / (1 + e^(-a(θ-b)))²
        exponent = -a * (theta - b)
        
        if abs(exponent) > 500:
            return 0.0
        
        exp_term = math.exp(exponent)
        denominator = (1 + exp_term) ** 2
        
        if denominator == 0:
            return 0.0
        
        p_prime = a * (1 - c) * exp_term / denominator
        
        # Fisher information
        info = (p_prime ** 2) / (p * (1 - p))
        
        return max(0.0, info)
    
    def likelihood(self, theta: float, answers: List[Tuple[Question, bool]]) -> float:
        """
        Calculate likelihood of observed answers given ability theta.
        
        L(θ) = ∏ P(θ)^correct * (1 - P(θ))^incorrect
        
        Args:
            theta: Ability parameter
            answers: List of (question, correct) tuples
            
        Returns:
            Likelihood value
        """
        likelihood = 1.0
        
        for question, correct in answers:
            p = self.probability_correct(theta, question)
            
            if correct:
                likelihood *= p
            else:
                likelihood *= (1 - p)
        
        return likelihood
    
    def log_likelihood(self, theta: float, answers: List[Tuple[Question, bool]]) -> float:
        """
        Calculate log-likelihood (more numerically stable).
        
        Args:
            theta: Ability parameter
            answers: List of (question, correct) tuples
            
        Returns:
            Log-likelihood value
        """
        log_lik = 0.0
        
        for question, correct in answers:
            p = self.probability_correct(theta, question)
            
            if correct:
                log_lik += safe_log(p)
            else:
                log_lik += safe_log(1 - p)
        
        return log_lik
    
    def posterior(self, theta: float, answers: List[Tuple[Question, bool]]) -> float:
        """
        Calculate posterior probability using Bayes' theorem.
        
        P(θ|answers) ∝ L(θ|answers) * P(θ)
        
        Args:
            theta: Ability parameter
            answers: List of (question, correct) tuples
            
        Returns:
            Unnormalized posterior probability
        """
        # Prior probability (normal distribution)
        prior = normal_pdf(theta, self.prior_mean, self.prior_std)
        
        # Likelihood
        lik = self.likelihood(theta, answers)
        
        # Posterior (unnormalized)
        return prior * lik
    
    def estimate_theta_eap(self, answers: List[Tuple[Question, bool]], 
                           current_theta: float = None) -> float:
        """
        Estimate ability using Expected A Posteriori (EAP) method.
        
        EAP is the mean of the posterior distribution:
        θ_EAP = ∫ θ * P(θ|answers) dθ / ∫ P(θ|answers) dθ
        
        We use numerical integration (quadrature) to approximate the integrals.
        
        Args:
            answers: List of (question, correct) tuples
            current_theta: Current ability estimate (for initialization)
            
        Returns:
            Updated ability estimate
        """
        if not answers:
            return current_theta if current_theta is not None else Config.IRT_INITIAL_THETA
        
        # Calculate unnormalized posterior weights on a discrete theta grid.
        # We operate in log space for stability, then normalize.
        log_weights: List[float] = []
        for theta in self.quadrature_points:
            log_prior = safe_log(normal_pdf(theta, self.prior_mean, self.prior_std))
            log_lik = self.log_likelihood(theta, answers)
            log_weights.append(log_prior + log_lik)

        log_w = np.array(log_weights, dtype=float)
        max_log_w = float(np.max(log_w))
        if not math.isfinite(max_log_w):
            return current_theta if current_theta is not None else Config.IRT_INITIAL_THETA

        weights = np.exp(log_w - max_log_w)
        denom = float(np.sum(weights))
        if denom <= 0.0 or not math.isfinite(denom):
            return current_theta if current_theta is not None else Config.IRT_INITIAL_THETA

        theta_eap = float(np.sum(self.quadrature_points * weights) / denom)
        return float(max(self.theta_min, min(self.theta_max, theta_eap)))
    
    def estimate_theta_mle(self, answers: List[Tuple[Question, bool]], 
                           initial_theta: float = None) -> float:
        """
        Estimate ability using Maximum Likelihood Estimation (MLE).
        
        This is an alternative to EAP, using Newton-Raphson method.
        
        Args:
            answers: List of (question, correct) tuples
            initial_theta: Starting point for optimization
            
        Returns:
            MLE estimate of ability
        """
        if not answers:
            return initial_theta if initial_theta is not None else Config.IRT_INITIAL_THETA
        
        # Newton-Raphson parameters
        theta = initial_theta if initial_theta is not None else Config.IRT_INITIAL_THETA
        max_iterations = 20
        tolerance = 0.001
        
        for _ in range(max_iterations):
            # Calculate first and second derivatives of log-likelihood
            first_deriv = 0.0
            second_deriv = 0.0
            
            for question, correct in answers:
                a = question.a
                b = question.b
                c = question.c
                
                p = self.probability_correct(theta, question)
                
                # Derivative calculations
                exponent = -a * (theta - b)
                if abs(exponent) > 500:
                    continue
                
                exp_term = math.exp(exponent)
                p_star = (p - c) / (1 - c)
                
                if correct:
                    first_deriv += a * (1 - p_star)
                    second_deriv -= a * a * p_star * (1 - p_star)
                else:
                    first_deriv -= a * p_star
                    second_deriv -= a * a * p_star * (1 - p_star)
            
            # Newton-Raphson update
            if second_deriv == 0:
                break
            
            delta = -first_deriv / second_deriv
            theta += delta
            
            # Check convergence
            if abs(delta) < tolerance:
                break
            
            # Keep theta in reasonable range
            theta = max(self.theta_min, min(self.theta_max, theta))
        
        return theta
    
    def update_theta(self, current_theta: float, question: Question, 
                     correct: bool, answer_history: List[AnswerRecord] = None) -> float:
        """
        Update ability estimate based on a new answer.
        
        Args:
            current_theta: Current ability estimate
            question: Question that was answered
            correct: Whether the answer was correct
            answer_history: Previous answer records (optional, for better estimation)
            
        Returns:
            Updated ability estimate
        """
        # Build an answer vector of recent responses (N > 1) for EAP.
        # We intentionally avoid updating theta from a single answer.
        answers: List[Tuple[Question, bool]] = []

        if answer_history:
            recent_history = answer_history[-self.answer_history_window:]
            for record in recent_history:
                if record.alpha is None or record.beta is None or record.c is None:
                    continue
                params = _IRTItemParams(alpha=float(record.alpha), beta=float(record.beta), c=float(record.c))
                answers.append((params, bool(record.correct)))

        # Append the new answer (as the most recent observation)
        answers.append((question, bool(correct)))

        if len(answers) < self.min_answers_for_update:
            return float(max(self.theta_min, min(self.theta_max, current_theta)))

        return self.estimate_theta_eap(answers, current_theta)
    
    def get_question_difficulty_match(self, theta: float, question: Question) -> float:
        """
        Calculate how well a question's difficulty matches the learner's ability.
        
        Returns a score where 0 = perfect match, higher = worse match.
        
        Args:
            theta: Learner's ability
            question: Question to evaluate
            
        Returns:
            Difficulty mismatch score
        """
        # For 3PL, optimal difficulty is close to theta
        # Questions with b ≈ θ provide maximum information
        return abs(question.b - theta)
    
    def select_best_question(self, theta: float, questions: List[Question]) -> Question:
        """
        Select the best question based on information criterion.
        
        Args:
            theta: Current ability estimate
            questions: List of candidate questions
            
        Returns:
            Question with highest information value
        """
        if not questions:
            return None
        
        best_question = None
        max_info = -1
        
        for question in questions:
            info = self.information(theta, question)
            if info > max_info:
                max_info = info
                best_question = question
        
        return best_question
    
    def rank_questions_by_information(self, theta: float, 
                                     questions: List[Question]) -> List[Tuple[Question, float]]:
        """
        Rank questions by their information value at given ability level.
        
        Args:
            theta: Current ability estimate
            questions: List of questions to rank
            
        Returns:
            List of (question, information) tuples, sorted by information (descending)
        """
        ranked = []
        
        for question in questions:
            info = self.information(theta, question)
            ranked.append((question, info))
        
        # Sort by information (descending)
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked
