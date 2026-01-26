// Initialize the code editor
document.addEventListener('DOMContentLoaded', function () {
    // Only initialize if we're on the question page
    if (!document.getElementById('editor')) return;

    // Initialize Ace Editor
    const editor = ace.edit("editor");
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/python");
    editor.setOptions({
        fontSize: "14px",
        tabSize: 4,
        useSoftTabs: true,
        showPrintMargin: false,
        highlightActiveLine: true,
        enableBasicAutocompletion: true,
        enableLiveAutocompletion: true
    });

    // Line counter functionality
    function getLineCount() {
        return editor.session.getLength();
    }

    function updateLineCount() {
        const lineCount = getLineCount();
        const counter = document.getElementById('code-line-count');
        if (counter) {
            counter.textContent = lineCount;
            // Color coding based on line count
            if (lineCount >= 50) {
                counter.style.color = '#e74c3c';
                counter.style.fontWeight = 'bold';
            } else if (lineCount >= 45) {
                counter.style.color = '#f39c12';
            } else {
                counter.style.color = '#7f8c8d';
                counter.style.fontWeight = 'normal';
            }
        }
    }

    // Update line count on editor change
    editor.session.on('change', function () {
        updateLineCount();
    });

    // Initial line count
    updateLineCount();

    // Word counter functionality for feedback
    function countWords(text) {
        if (!text || text.trim() === '') return 0;
        return text.trim().split(/\s+/).filter(word => word.length > 0).length;
    }

    function updateWordCount() {
        const feedbackTextarea = document.getElementById('self-feelings');
        if (!feedbackTextarea) return;

        const wordCount = countWords(feedbackTextarea.value);
        const counter = document.getElementById('feedback-word-count');
        if (counter) {
            counter.textContent = wordCount;
            // Color coding based on word count
            if (wordCount >= 50) {
                counter.style.color = '#e74c3c';
                counter.style.fontWeight = 'bold';
            } else if (wordCount >= 45) {
                counter.style.color = '#f39c12';
            } else {
                counter.style.color = '#7f8c8d';
                counter.style.fontWeight = 'normal';
            }
        }
    }

    // Add event listener for feedback textarea
    const feedbackTextarea = document.getElementById('self-feelings');
    if (feedbackTextarea) {
        feedbackTextarea.addEventListener('input', updateWordCount);
        // Initial word count
        updateWordCount();
    }

    // Get DOM elements
    const runButton = document.getElementById('run-code');
    const submitButton = document.getElementById('submit-code');
    const hintButton = document.getElementById('hint-button');
    const hintDisplay = document.getElementById('hint-display');
    const hintContent = document.getElementById('hint-content');
    const closeHintButton = document.getElementById('close-hint');
    const hintsRemainingSpan = document.getElementById('hints-remaining');
    const feedbackModal = document.getElementById('feedback-modal');
    const closeModal = document.querySelector('.close');
    const feedbackForm = document.getElementById('feedback-form');
    const feedbackResult = document.getElementById('feedback-result');
    const nextQuestionBtn = document.getElementById('next-question-btn');
    const questionId = document.getElementById('question-id').value;
    const category = document.getElementById('category').value;

    // Track hint usage
    let hintsUsed = 0;
    const MAX_HINTS = 3;

    // Track time when the page loads
    // Time tracking removed as per requirements

    // Run code button click handler (runs tests and shows results)
    if (runButton) {
        runButton.addEventListener('click', async function () {
            const code = editor.getValue();

            try {
                const response = await fetch('/check_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        code: code,
                        question_id: questionId
                    })
                });

                const data = await response.json();

                if (!data.success) {
                    alert('Some tests failed. ' + (data.message || ''));
                }

                // Update test cases panel with actual results if provided
                if (Array.isArray(data.visible_tests)) {
                    const tests = data.visible_tests.map((t) => ({
                        input: t.input,
                        expected: t.expected_output,
                        actual: t.actual_output !== undefined ? t.actual_output : (t.error || ''),
                        passed: t.passed
                    }));
                    updateTestCases(tests);
                }

                // Show a short, readable summary in the output area
                const outputElement = document.getElementById('run-output');
                if (outputElement) {
                    const summary = data.message || (data.success ? 'All tests passed.' : 'Some tests failed.');
                    outputElement.textContent = summary;
                }
            } catch (error) {
                console.error('Error running code:', error);
                const outputElement = document.getElementById('run-output');
                if (outputElement) {
                    outputElement.textContent = 'Error running code: ' + error;
                } else {
                    alert('Error running code');
                }
            }
        });
    }

    // Hint button click handler
    if (hintButton) {
        hintButton.addEventListener('click', async function () {
            const code = editor.getValue();
            hintsUsed++;

            try {
                const response = await fetch('/get_hint', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        question_id: questionId,
                        code: code,
                        hint_number: hintsUsed
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Display hint
                    hintContent.textContent = data.hint;
                    hintDisplay.style.display = 'block';

                    // Update hints remaining
                    const remaining = MAX_HINTS - hintsUsed;
                    hintsRemainingSpan.textContent = remaining;

                    // Transform button after 3 hints
                    if (hintsUsed >= MAX_HINTS) {
                        hintButton.innerHTML = '🤷 I Don\'t Know';
                        hintButton.classList.remove('btn-hint');
                        hintButton.classList.add('btn-secondary');

                        // Change button behavior to submit with failing tests
                        hintButton.onclick = async function () {
                            // Open feedback modal directly without checking tests
                            feedbackModal.style.display = 'flex';
                        };
                    }
                } else {
                    alert('Failed to get hint: ' + (data.message || 'Unknown error'));
                    hintsUsed--; // Rollback on error
                }
            } catch (error) {
                console.error('Error getting hint:', error);
                alert('An error occurred while getting the hint.');
                hintsUsed--; // Rollback on error
            }
        });
    }

    // Close hint display
    if (closeHintButton) {
        closeHintButton.addEventListener('click', function () {
            hintDisplay.style.display = 'none';
        });
    }

    // Submit code button click handler
    if (submitButton) {
        submitButton.addEventListener('click', async function () {
            const code = editor.getValue();

            // Check line count limit
            const lineCount = getLineCount();
            if (lineCount > 50) {
                alert(`Your code has ${lineCount} lines. Please reduce it to 50 lines or fewer before submitting.`);
                return;
            }

            // Time tracking removed

            try {
                const response = await fetch('/check_code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        code: code,
                        question_id: questionId
                    })
                });

                const data = await response.json();

                if (data.success) {
                    feedbackModal.style.display = 'flex';
                } else {
                    alert('Try again! ' + (data.message || 'Some tests failed.'));
                }
            } catch (error) {
                console.error('Error submitting code:', error);
                alert('An error occurred while submitting your code.');
            }
        });
    }

    // Close modal button
    if (closeModal) {
        closeModal.addEventListener('click', function () {
            feedbackModal.style.display = 'none';
        });
    }

    // Close modal when clicking outside of it
    window.addEventListener('click', function (event) {
        if (event.target === feedbackModal) {
            feedbackModal.style.display = 'none';
        }
        if (event.target === feedbackResult) {
            feedbackResult.style.display = 'none';
        }
    });

    // Feedback form submission
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            // Check word count limit
            const feedbackText = document.getElementById('self-feelings').value;
            const wordCount = countWords(feedbackText);
            if (wordCount > 50) {
                alert(`Your feedback has ${wordCount} words. Please reduce it to 50 words or fewer before submitting.`);
                return;
            }

            // Show progress overlay and hide modal
            showProgressOverlay();
            feedbackModal.style.display = 'none';

            // Get form data
            const formData = new FormData(feedbackForm);
            const painPoints = [];

            // Get checked pain points
            document.querySelectorAll('input[name="pain_points"]:checked').forEach(checkbox => {
                painPoints.push(checkbox.value);
            });

            // Prepare data for submission
            const submissionData = {
                user_code: editor.getValue(),
                difficulty_rating: parseInt(document.querySelector('input[name="difficulty"]:checked').value),
                pain_points: painPoints,
                self_feelings: feedbackText,
                hints_used: hintsUsed,
                question_metadata: {
                    id: questionId,
                    category: category
                }
            };

            try {
                // Update progress: preparing
                updateProgress(20, 'Preparing feedback data...');
                await delay(400);

                // Update progress: sending
                updateProgress(50, 'Sending feedback to server...');

                const response = await fetch('/submit_feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(submissionData)
                });

                // Update progress: processing
                updateProgress(80, 'Processing response...');
                await delay(300);

                // Update progress: complete
                updateProgress(100, 'Feedback submitted successfully!');
                await delay(600);

                // Hide overlay and handle response
                hideProgressOverlay();

                const html = await response.text();
                document.open();
                document.write(html);
                document.close();
            } catch (error) {
                console.error('Error submitting feedback:', error);
                hideProgressOverlay();
                alert('An error occurred while submitting your feedback.');
            }
        });
    }

    // Progress overlay helper functions
    function showProgressOverlay() {
        const overlay = document.getElementById('progress-overlay');
        if (overlay) {
            overlay.classList.add('active');
            updateProgress(0, 'Initializing...');
        }
    }

    function hideProgressOverlay() {
        const overlay = document.getElementById('progress-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    function updateProgress(percent, status) {
        const progressBar = document.getElementById('progress-bar-fill');
        const progressStatus = document.getElementById('progress-status');

        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressStatus) progressStatus.textContent = status;
    }

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Next question button
    if (nextQuestionBtn) {
        nextQuestionBtn.addEventListener('click', function () {
            window.location.href = '/question';
        });
    }
    function formatTestCaseValue(value) {
        // אם זה מחרוזת JSON - נמיר
        if (typeof value === 'string') {
            const trimmed = value.trim();
            if (
                trimmed.startsWith('[') && trimmed.endsWith(']')
            ) {
                try {
                    value = JSON.parse(trimmed);
                } catch {
                    return trimmed;
                }
            }
        }

        // אם זה מערך, נוריד רק שכבה חיצונית אחת
        if (Array.isArray(value) && value.length === 1 && Array.isArray(value[0])) {
            value = value[0];
        }

        // במקרה שהמערך עצמו הוא מערך רגיל - פשוט נחזיר JSON כדי לשמור על מבנה
        if (Array.isArray(value)) {
            return JSON.stringify(value);
        }

        // אובייקט רגיל
        if (value !== null && typeof value === 'object') {
            return JSON.stringify(value);
        }

        // אחרת פשוט מחרוזת
        return String(value);
    }







    // Function to update test cases display (kept for future use)
    function updateTestCases(testCases) {
        const container = document.getElementById('test-cases-container');
        if (!container) return;

        container.innerHTML = '';

        testCases.forEach((testCase, index) => {
            const testCaseElement = document.createElement('div');
            testCaseElement.className = 'test-case';
            testCaseElement.innerHTML = `
                <div class="test-case-header">
                    <span>Test Case ${index + 1}</span>
                    <span class="test-status ${testCase.passed ? 'passed' : 'failed'}">
                        ${testCase.passed ? '✓ Passed' : '✗ Failed'}
                    </span>
                </div>
                <div class="test-case-content">
                    <p>Input: <code>${formatTestCaseValue(testCase.input)}</code></p>
                    <p>Expected Output: <code>${testCase.expected}</code></p>
                    <p>Actual Output: <code>${testCase.actual}</code></p>
                </div>
            `;

            container.appendChild(testCaseElement);
        });
    }
});
