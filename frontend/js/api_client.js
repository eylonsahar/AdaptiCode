/**
 * API Client for AdaptiCode Backend
 */

const API_BASE_URL = 'http://localhost:5000/api';

class APIClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Question endpoints
    async getNextQuestion() {
        return this.request('/question/next');
    }

    async getQuestion(questionName) {
        return this.request(`/question/${encodeURIComponent(questionName)}`);
    }

    // Code submission
    async submitCode(questionName, code, startTime) {
        return this.request('/code/submit', {
            method: 'POST',
            body: JSON.stringify({
                question_name: questionName,
                code: code,
                start_time: startTime
            })
        });
    }

    async runCode(code) {
        return this.request('/code/run', {
            method: 'POST',
            body: JSON.stringify({ code })
        });
    }

    // Feedback
    async submitFeedback(questionName, difficultyRating, confidenceLevel, notes = '') {
        return this.request('/feedback/submit', {
            method: 'POST',
            body: JSON.stringify({
                question_name: questionName,
                difficulty_rating: difficultyRating,
                confidence_level: confidenceLevel,
                notes: notes
            })
        });
    }

    // Progress
    async getProgress() {
        return this.request('/progress');
    }

    // Explanation
    async getExplanation(questionName) {
        return this.request(`/explanation?question_name=${encodeURIComponent(questionName)}`);
    }

    // Concepts
    async getConceptTree() {
        return this.request('/concepts/tree');
    }

    async getTopics() {
        return this.request('/topics');
    }

    async getRecommendedQuestions(topic, n = 5) {
        return this.request(`/questions/recommended?topic=${encodeURIComponent(topic)}&n=${n}`);
    }

    // Health check
    async healthCheck() {
        return this.request('/health');
    }
}

// Create global API client instance
const apiClient = new APIClient();

