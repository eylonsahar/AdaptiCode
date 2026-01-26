"""
Configuration for AdaptiCode system.
"""
import os
from typing import Optional


class Config:
    """Application configuration."""
    
    # Flask settings
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5001))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    # USE_RELOADER = os.getenv('USE_RELOADER', 'False')
    USE_RELOADER = False
    # Data directories
    DATA_DIR = os.getenv('DATA_DIR', 'data')

    # Startup behavior
    # - keep: load existing user profile if present
    # - reset: start as a new user (recreate persisted user state)
    USER_MODE_DEFAULT = 'reset'
    USER_MODE = os.getenv('ADAPTICODE_USER_MODE', USER_MODE_DEFAULT).strip().lower()
    
    # IRT parameters
    IRT_INITIAL_THETA = float(os.getenv('IRT_INITIAL_THETA', 0.0))
    MASTERY_THRESHOLD = float(os.getenv('MASTERY_THRESHOLD', 1.2))
    DEFAULT_GUESSING_PARAM = float(os.getenv('DEFAULT_GUESSING_PARAM', 0.25))
    
    # Question selection parameters
    QUESTION_HISTORY_WINDOW = int(os.getenv('QUESTION_HISTORY_WINDOW', 5))
    K_BEST_QUESTIONS = int(os.getenv('K_BEST_QUESTIONS', 10))
    
    # Code execution settings
    CODE_EXECUTION_TIMEOUT = int(os.getenv('CODE_EXECUTION_TIMEOUT', 5))
    MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', 256))
    
    # LLM settings
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # openai, anthropic, gemini, groq, local
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    LLM_MODEL = os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', 500))
    
    # EAP estimation parameters
    EAP_PRIOR_MEAN = float(os.getenv('EAP_PRIOR_MEAN', 0.0))
    EAP_PRIOR_STD = float(os.getenv('EAP_PRIOR_STD', 1.0))
    EAP_QUADRATURE_POINTS = int(os.getenv('EAP_QUADRATURE_POINTS', 41))
    EAP_THETA_MIN = float(os.getenv('EAP_THETA_MIN', -4.0))
    EAP_THETA_MAX = float(os.getenv('EAP_THETA_MAX', 4.0))

    # Theta update stability
    # We intentionally avoid updating theta from a single response.
    EAP_ANSWER_HISTORY_WINDOW = int(os.getenv('EAP_ANSWER_HISTORY_WINDOW', 4))
    EAP_MIN_ANSWERS_FOR_UPDATE = int(os.getenv('EAP_MIN_ANSWERS_FOR_UPDATE', 2))
    
    # Feedback weights
    OBJECTIVE_WEIGHT = float(os.getenv('OBJECTIVE_WEIGHT', 0.7))
    SUBJECTIVE_WEIGHT = float(os.getenv('SUBJECTIVE_WEIGHT', 0.3))
    
    @classmethod
    def get_llm_api_key(cls) -> Optional[str]:
        """Get the appropriate API key based on LLM provider."""
        if cls.LLM_PROVIDER == 'openai':
            return cls.OPENAI_API_KEY
        elif cls.LLM_PROVIDER == 'anthropic':
            return cls.ANTHROPIC_API_KEY
        elif cls.LLM_PROVIDER == 'gemini':
            return cls.GEMINI_API_KEY
        elif cls.LLM_PROVIDER == 'groq':
            return cls.GROQ_API_KEY
        return None

