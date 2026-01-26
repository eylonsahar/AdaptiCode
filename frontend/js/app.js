/**
 * Main Application Logic
 */

class AdaptiCodeApp {
    constructor() {
        this.currentQuestion = null;
        this.startTime = null;
        this.codeEditor = null;
        this.conceptTree = null;

        this.init();
    }

    async init() {
        // Initialize components
        this.codeEditor = new CodeEditor('code-editor');
        this.conceptTree = new ConceptTree('concept-tree');

        // Setup event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadProgress();
        await this.conceptTree.load();

        console.log('AdaptiCode initialized');
    }

    setupEventListeners() {
        // Next Question button
        document.getElementById('next-question-btn').addEventListener('click', () => {
            this.loadNextQuestion();
        });

        // Submit Code button
        document.getElementById('submit-code-btn').addEventListener('click', () => {
            this.submitCode();
        });

        // Run Code button
        document.getElementById('run-code-btn').addEventListener('click', () => {
            this.runCode();
        });

        // Get Explanation button
        document.getElementById('get-explanation-btn').addEventListener('click', () => {
            this.getExplanation();
        });

        // Feedback modal buttons
        document.getElementById('submit-feedback-btn').addEventListener('click', () => {
            this.submitFeedback();
        });

        document.getElementById('skip-feedback-btn').addEventListener('click', () => {
            this.closeFeedbackModal();
        });
    }

    async loadProgress() {
        try {
            const progress = await apiClient.getProgress();
            this.updateProgressDisplay(progress);
        } catch (error) {
            console.error('Failed to load progress:', error);
        }
    }

    updateProgressDisplay(progress) {
        const overall = progress.overall;

        // Update progress bar
        const progressFill = document.getElementById('overall-progress');
        progressFill.style.width = `${overall.overall_progress_percent}%`;
        progressFill.textContent = `${Math.round(overall.overall_progress_percent)}%`;

        // Update progress text
        document.getElementById('progress-text').textContent =
            `${overall.mastered} of ${overall.total_topics} topics mastered`;

        // Update stats
        document.getElementById('mastered-count').textContent = overall.mastered;
        document.getElementById('in-progress-count').textContent = overall.in_progress;
        document.getElementById('attempts-count').textContent = overall.total_attempts;
    }

    async loadNextQuestion() {
        try {
            const btn = document.getElementById('next-question-btn');
            btn.disabled = true;
            btn.textContent = 'Loading...';

            const data = await apiClient.getNextQuestion();

            this.currentQuestion = data.question;
            this.startTime = new Date().toISOString();

            this.displayQuestion(data);
            this.codeEditor.clear();

            // Hide results if visible
            document.getElementById('results-panel').style.display = 'none';
            document.getElementById('explanation-content').style.display = 'none';

            btn.disabled = false;
            btn.textContent = 'Get Next Question';

        } catch (error) {
            console.error('Failed to load question:', error);
            alert('Failed to load question: ' + error.message);

            const btn = document.getElementById('next-question-btn');
            btn.disabled = false;
            btn.textContent = 'Get Next Question';
        }
    }

    displayQuestion(data) {
        const question = data.question;
        const metadata = data.metadata;

        // Update title
        document.getElementById('question-title').textContent = question.name;

        // Update content
        const content = document.getElementById('question-content');
        content.innerHTML = `
            <div class="question-description">
                ${this.formatDescription(question.description)}
            </div>
        `;

        // Update metadata
        document.getElementById('question-metadata').style.display = 'block';
        document.getElementById('user-theta').textContent = metadata.your_theta;
        document.getElementById('question-difficulty').textContent = metadata.question_difficulty;
        document.getElementById('selection-reason').textContent = metadata.selection_reason;

        // Display test cases
        this.displayTestCases(question.tests);

        // Show explanation button
        document.getElementById('get-explanation-btn').style.display = 'inline-block';
    }

    formatDescription(description) {
        // Convert newlines to <br> and preserve formatting
        return description
            .split('\n\n')
            .map(para => `<p>${para.replace(/\n/g, '<br>')}</p>`)
            .join('');
    }

    displayTestCases(tests) {
        const container = document.getElementById('test-cases');
        const list = document.getElementById('test-cases-list');

        list.innerHTML = '';

        tests.forEach((test, index) => {
            const testCase = document.createElement('div');
            testCase.className = 'test-case';
            testCase.innerHTML = `
                <strong>Test ${index + 1}:</strong><br>
                <strong>Input:</strong> ${this.formatValue(test.input)}<br>
                <strong>Expected Output:</strong> ${this.formatValue(test.output)}
            `;
            list.appendChild(testCase);
        });

        container.style.display = 'block';
    }

    formatValue(value) {
        if (typeof value === 'object') {
            return '<code>' + JSON.stringify(value) + '</code>';
        }
        return '<code>' + value + '</code>';
    }

    async submitCode() {
        if (!this.currentQuestion) {
            alert('Please load a question first');
            return;
        }

        const code = this.codeEditor.getValue().trim();
        if (!code) {
            alert('Please write some code first');
            return;
        }

        try {
            const btn = document.getElementById('submit-code-btn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Testing...';

            const result = await apiClient.submitCode(
                this.currentQuestion.name,
                code,
                this.startTime
            );

            this.displayResults(result);

            // Refresh progress
            await this.loadProgress();
            await this.conceptTree.refresh();

            // Show feedback modal if tests passed
            if (result.test_results.all_passed) {
                this.showFeedbackModal();
            }

            btn.disabled = false;
            btn.textContent = '✓ Submit Solution';

        } catch (error) {
            console.error('Failed to submit code:', error);
            alert('Failed to submit code: ' + error.message);

            const btn = document.getElementById('submit-code-btn');
            btn.disabled = false;
            btn.textContent = '✓ Submit Solution';
        }
    }

    displayResults(result) {
        const panel = document.getElementById('results-panel');
        const content = document.getElementById('results-content');

        const testResults = result.test_results;
        const feedback = result.feedback;

        let html = '';

        // Summary
        html += `<div class="message ${testResults.all_passed ? 'message-success' : 'message-error'}">`;
        html += `<strong>${result.summary}</strong>`;
        html += `</div>`;

        // Visible test results
        if (testResults.visible_tests && testResults.visible_tests.length > 0) {
            html += '<h4>Visible Tests:</h4>';
            testResults.visible_tests.forEach(test => {
                html += this.formatTestResult(test);
            });
        }

        // Hidden tests summary
        if (testResults.hidden_tests_summary) {
            const hidden = testResults.hidden_tests_summary;
            html += `<div class="test-result ${hidden.passed === hidden.total ? 'passed' : 'failed'}">`;
            html += `<div class="test-result-header">Hidden Tests: ${hidden.passed}/${hidden.total} passed</div>`;
            html += `</div>`;
        }

        // Feedback
        if (feedback && feedback.recommendations) {
            html += '<h4>Recommendations:</h4>';
            html += '<ul>';
            feedback.recommendations.forEach(rec => {
                html += `<li>${rec}</li>`;
            });
            html += '</ul>';
        }

        content.innerHTML = html;
        panel.style.display = 'block';
        panel.className = testResults.all_passed ? 'results-panel result-success' : 'results-panel result-failure';
    }

    formatTestResult(test) {
        let html = `<div class="test-result ${test.passed ? 'passed' : 'failed'}">`;
        html += `<div class="test-result-header">`;
        html += test.passed ? '✓' : '✗';
        html += ` Test ${test.test_num}`;
        html += `</div>`;

        if (!test.passed && test.visible) {
            html += `<div class="test-result-details">`;
            if (test.input !== undefined) {
                html += `<div><strong>Input:</strong> ${this.formatValue(test.input)}</div>`;
            }
            if (test.expected_output !== undefined) {
                html += `<div><strong>Expected:</strong> ${this.formatValue(test.expected_output)}</div>`;
            }
            if (test.actual_output !== undefined) {
                html += `<div><strong>Got:</strong> ${this.formatValue(test.actual_output)}</div>`;
            }
            if (test.error) {
                html += `<div><strong>Error:</strong> ${test.error}</div>`;
            }
            html += `</div>`;
        }

        html += `</div>`;
        return html;
    }

    async runCode() {
        const code = this.codeEditor.getValue().trim();
        if (!code) {
            alert('Please write some code first');
            return;
        }

        try {
            const btn = document.getElementById('run-code-btn');
            btn.disabled = true;
            btn.textContent = 'Running...';

            const result = await apiClient.runCode(code);

            const panel = document.getElementById('results-panel');
            const content = document.getElementById('results-content');

            let html = '<h4>Execution Result:</h4>';

            if (result.success) {
                html += '<div class="message message-success">Code executed successfully</div>';
                if (result.output) {
                    html += `<pre>${result.output}</pre>`;
                }
            } else {
                html += '<div class="message message-error">Execution failed</div>';
                if (result.error) {
                    html += `<pre>${result.error}</pre>`;
                }
            }

            content.innerHTML = html;
            panel.style.display = 'block';

            btn.disabled = false;
            btn.textContent = '▶ Run Code';

        } catch (error) {
            console.error('Failed to run code:', error);
            alert('Failed to run code: ' + error.message);

            const btn = document.getElementById('run-code-btn');
            btn.disabled = false;
            btn.textContent = '▶ Run Code';
        }
    }

    async getExplanation() {
        if (!this.currentQuestion) {
            return;
        }

        try {
            const btn = document.getElementById('get-explanation-btn');
            btn.disabled = true;
            btn.textContent = 'Loading...';

            const result = await apiClient.getExplanation(this.currentQuestion.name);

            const content = document.getElementById('explanation-content');
            content.innerHTML = `
                <h4>💡 Explanation</h4>
                <div>${this.formatDescription(result.explanation)}</div>
                <br>
                <h4>💭 Hint</h4>
                <div><em>${result.hint}</em></div>
            `;
            content.style.display = 'block';

            btn.disabled = false;
            btn.textContent = '💡 Get Explanation';

        } catch (error) {
            console.error('Failed to get explanation:', error);
            alert('Failed to get explanation: ' + error.message);

            const btn = document.getElementById('get-explanation-btn');
            btn.disabled = false;
            btn.textContent = '💡 Get Explanation';
        }
    }

    showFeedbackModal() {
        document.getElementById('feedback-modal').style.display = 'flex';
    }

    closeFeedbackModal() {
        document.getElementById('feedback-modal').style.display = 'none';
    }

    async submitFeedback() {
        if (!this.currentQuestion) {
            return;
        }

        const difficulty = document.querySelector('input[name="difficulty"]:checked').value;
        const confidence = document.querySelector('input[name="confidence"]:checked').value;
        const notes = document.getElementById('feedback-notes').value;

        // Show progress overlay
        this.showProgressOverlay();
        this.closeFeedbackModal();

        try {
            // Update progress: preparing
            this.updateProgress(20, 'Preparing feedback data...');
            await this.delay(400);

            // Update progress: sending
            this.updateProgress(50, 'Sending feedback to server...');

            await apiClient.submitFeedback(
                this.currentQuestion.name,
                parseInt(difficulty),
                parseInt(confidence),
                notes
            );

            // Update progress: processing
            this.updateProgress(80, 'Processing response...');
            await this.delay(300);

            // Update progress: complete
            this.updateProgress(100, 'Feedback submitted successfully!');
            await this.delay(600);

            // Hide overlay
            this.hideProgressOverlay();

            // Reset form
            document.getElementById('feedback-notes').value = '';

        } catch (error) {
            console.error('Failed to submit feedback:', error);
            this.hideProgressOverlay();
            alert('Failed to submit feedback: ' + error.message);
        }
    }

    showProgressOverlay() {
        const overlay = document.getElementById('progress-overlay');
        overlay.classList.add('active');
        this.updateProgress(0, 'Initializing...');
    }

    hideProgressOverlay() {
        const overlay = document.getElementById('progress-overlay');
        overlay.classList.remove('active');
    }

    updateProgress(percent, status) {
        const progressBar = document.getElementById('progress-bar-fill');
        const progressStatus = document.getElementById('progress-status');

        progressBar.style.width = `${percent}%`;
        progressStatus.textContent = status;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AdaptiCodeApp();
});

