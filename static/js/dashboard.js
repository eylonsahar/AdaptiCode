/**
 * Dashboard JavaScript - Handles data fetching, visualization, and interactivity
 */

// Global variables
let dashboardData = null;
let topicSuccessChart = null;
let topicAttemptsChart = null;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function () {
    loadDashboardData();
});

/**
 * Fetch dashboard data from API
 */
async function loadDashboardData() {
    try {
        const response = await fetch('/api/dashboard/data');

        if (!response.ok) {
            throw new Error('Failed to fetch dashboard data');
        }

        dashboardData = await response.json();

        // Hide loading, show content
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';

        // Render all dashboard components
        renderStatistics();
        renderRoadmaps();
        renderCharts();
        renderHistoryTable();
        setupFilters();

    } catch (error) {
        console.error('Error loading dashboard:', error);
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('error-state').style.display = 'block';
    }
}

/**
 * Render statistics overview cards
 */
function renderStatistics() {
    const stats = dashboardData.statistics;

    document.getElementById('total-questions').textContent = stats.total_questions;
    document.getElementById('passed-questions').textContent = stats.passed_questions;
    document.getElementById('success-rate').textContent = stats.success_rate.toFixed(1) + '%';
}

/**
 * Render theta roadmaps for each topic
 */
function renderRoadmaps() {
    const container = document.getElementById('roadmap-container');
    container.innerHTML = '';

    const topics = dashboardData.topics;

    // Define topic order based on prerequisite graph
    // This ensures roadmaps appear in learning order
    const topicOrder = [
        'Recursion Basics',
        'Backtracking',
        'Dynamic Programming & Advanced Recursion'
    ];

    // Render roadmaps in prerequisite order
    for (const topicName of topicOrder) {
        if (topics[topicName]) {
            const roadmapCard = createRoadmapCard(topicName, topics[topicName]);
            container.appendChild(roadmapCard);
        }
    }
}

/**
 * Create a roadmap card for a single topic
 */
function createRoadmapCard(topicName, topicData) {
    const card = document.createElement('div');
    card.className = 'roadmap-card';

    const currentTheta = topicData.current_theta;
    const masteryThreshold = topicData.mastery_threshold;
    const progressPercent = topicData.progress_percent;
    const status = topicData.status;

    // Calculate positions for visualization
    // Use fixed range of -3 to 3 for all topics
    const minTheta = -3;
    const maxTheta = 3;
    const thetaRange = maxTheta - minTheta; // 6

    // Calculate current position as percentage (0-100%)
    const currentPosition = Math.max(0, Math.min(100, ((currentTheta - minTheta) / thetaRange) * 100));

    // Calculate mastery position as percentage
    const masteryPosition = Math.max(0, Math.min(100, ((masteryThreshold - minTheta) / thetaRange) * 100));

    // Status badge color
    let statusClass = 'status-locked';
    if (status === 'opened') statusClass = 'status-opened';
    if (status === 'mastered') statusClass = 'status-mastered';

    card.innerHTML = `
        <div class="roadmap-header">
            <h3>${topicName}</h3>
            <span class="status-badge ${statusClass}">${status}</span>
        </div>
        
        <div class="roadmap-stats">
            <div class="roadmap-stat">
                <span class="label">Current θ:</span>
                <span class="value">${currentTheta.toFixed(2)}</span>
            </div>
            <div class="roadmap-stat">
                <span class="label">Mastery θ:</span>
                <span class="value">${masteryThreshold.toFixed(2)}</span>
            </div>
            <div class="roadmap-stat">
                <span class="label">Progress:</span>
                <span class="value">${progressPercent.toFixed(1)}%</span>
            </div>
        </div>
        
        <div class="roadmap-visual">
            <div class="roadmap-track">
                <div class="roadmap-milestone start">
                    <div class="milestone-marker"></div>
                    <div class="milestone-label">Start<br/>θ = -3.0</div>
                </div>
                
                <div class="roadmap-progress-bar">
                    <div class="progress-fill" style="width: ${currentPosition}%"></div>
                    <div class="current-position" style="left: ${currentPosition}%">
                        <div class="position-marker"></div>
                        <div class="position-label">You are here<br/>θ = ${currentTheta.toFixed(2)}</div>
                    </div>
                    <div class="mastery-position" style="left: ${masteryPosition}%">
                        <div class="mastery-marker"></div>
                        <div class="mastery-label">Mastery<br/>θ = ${masteryThreshold.toFixed(2)}</div>
                    </div>
                </div>
                
                <div class="roadmap-milestone end">
                    <div class="milestone-marker"></div>
                    <div class="milestone-label">Max<br/>θ = 3.0</div>
                </div>
            </div>
        </div>
        
        <div class="roadmap-footer">
            <p>${getMotivationalMessage(progressPercent, status)}</p>
        </div>
    `;

    return card;
}

/**
 * Get motivational message based on progress
 */
function getMotivationalMessage(progressPercent, status) {
    if (status === 'mastered') {
        return '🎉 Congratulations! You\'ve mastered this topic!';
    } else if (status === 'locked') {
        return '🔒 Complete prerequisites to unlock this topic';
    } else if (progressPercent >= 75) {
        return '🔥 Almost there! Keep up the great work!';
    } else if (progressPercent >= 50) {
        return '💪 You\'re making excellent progress!';
    } else if (progressPercent >= 25) {
        return '🚀 Good start! Keep practicing!';
    } else {
        return '🌱 Just getting started. You got this!';
    }
}

/**
 * Render charts using Chart.js
 */
function renderCharts() {
    const topicStats = dashboardData.statistics.topic_stats;

    // Use prerequisite graph order for consistent chart display
    const topicOrder = [
        'Recursion Basics',
        'Backtracking',
        'Dynamic Programming & Advanced Recursion'
    ];

    // Filter to only include topics that have stats
    const topics = topicOrder.filter(topic => topicStats[topic]);
    const successRates = topics.map(topic => topicStats[topic].success_rate);
    const attempts = topics.map(topic => topicStats[topic].total_attempted);

    // Success Rate Chart
    const successCtx = document.getElementById('topic-success-chart').getContext('2d');
    if (topicSuccessChart) topicSuccessChart.destroy();

    topicSuccessChart = new Chart(successCtx, {
        type: 'bar',
        data: {
            labels: topics,
            datasets: [{
                label: 'Success Rate (%)',
                data: successRates,
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Attempts Chart
    const attemptsCtx = document.getElementById('topic-attempts-chart').getContext('2d');
    if (topicAttemptsChart) topicAttemptsChart.destroy();

    topicAttemptsChart = new Chart(attemptsCtx, {
        type: 'doughnut',
        data: {
            labels: topics,
            datasets: [{
                data: attempts,
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(245, 87, 108, 0.8)',
                    'rgba(0, 242, 254, 0.8)'
                ],
                borderColor: '#ffffff',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Render practice history table
 */
function renderHistoryTable() {
    const history = dashboardData.answer_history;
    const tbody = document.getElementById('history-tbody');
    tbody.innerHTML = '';

    if (history.length === 0) {
        document.getElementById('no-history').style.display = 'block';
        document.querySelector('.table-container').style.display = 'none';
        document.querySelector('.filter-controls').style.display = 'none';
        return;
    }

    // Render each record (already ordered oldest to newest from backend)
    history.forEach((record, index) => {
        const row = createHistoryRow(record, index + 1);
        tbody.appendChild(row);
    });
}

/**
 * Create a table row for a history record
 */
function createHistoryRow(record, rowNumber) {
    const row = document.createElement('tr');
    row.className = record.passed ? 'row-passed' : 'row-failed';
    row.dataset.topic = record.topic;
    row.dataset.result = record.passed ? 'passed' : 'failed';

    const thetaChange = record.theta_after - record.theta_before;
    const thetaChangeClass = thetaChange > 0 ? 'theta-increase' : thetaChange < 0 ? 'theta-decrease' : 'theta-neutral';
    const thetaChangeSymbol = thetaChange > 0 ? '↑' : thetaChange < 0 ? '↓' : '→';

    row.innerHTML = `
        <td>${rowNumber}</td>
        <td class="question-name">${escapeHtml(record.question_name)}</td>
        <td><span class="topic-badge">${escapeHtml(record.topic)}</span></td>
        <td><span class="test-rate">${record.test_pass_rate}%</span></td>
        <td><span class="code-quality">${escapeHtml(record.code_quality)}</span></td>
        <td class="self-feelings">${escapeHtml(record.self_feelings || 'N/A')}</td>
        <td><span class="result-badge ${record.passed ? 'badge-passed' : 'badge-failed'}">${record.passed ? 'Passed' : 'Failed'}</span></td>
        <td><span class="theta-change ${thetaChangeClass}">${thetaChangeSymbol} ${Math.abs(thetaChange).toFixed(2)}</span></td>
    `;

    return row;
}

/**
 * Setup filter controls
 */
function setupFilters() {
    const topicFilter = document.getElementById('topic-filter');
    const resultFilter = document.getElementById('result-filter');

    // Populate topic filter in prerequisite graph order
    const topicOrder = [
        'Recursion Basics',
        'Backtracking',
        'Dynamic Programming & Advanced Recursion'
    ];

    topicOrder.forEach(topic => {
        if (dashboardData.topics[topic]) {
            const option = document.createElement('option');
            option.value = topic;
            option.textContent = topic;
            topicFilter.appendChild(option);
        }
    });

    // Add event listeners
    topicFilter.addEventListener('change', applyFilters);
    resultFilter.addEventListener('change', applyFilters);
}

/**
 * Apply filters to history table
 */
function applyFilters() {
    const topicFilter = document.getElementById('topic-filter').value;
    const resultFilter = document.getElementById('result-filter').value;

    const rows = document.querySelectorAll('#history-tbody tr');

    rows.forEach(row => {
        let showRow = true;

        // Apply topic filter
        if (topicFilter !== 'all' && row.dataset.topic !== topicFilter) {
            showRow = false;
        }

        // Apply result filter
        if (resultFilter !== 'all' && row.dataset.result !== resultFilter) {
            showRow = false;
        }

        row.style.display = showRow ? '' : 'none';
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
