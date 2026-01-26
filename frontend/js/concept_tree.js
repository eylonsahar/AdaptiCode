/**
 * Concept Tree visualization and interaction
 */

class ConceptTree {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.concepts = [];
    }

    async load() {
        try {
            const data = await apiClient.getConceptTree();
            this.concepts = data.concepts;
            this.render();
        } catch (error) {
            console.error('Failed to load concept tree:', error);
            this.container.innerHTML = '<p class="error">Failed to load learning path</p>';
        }
    }

    render() {
        this.container.innerHTML = '';

        this.concepts.forEach(concept => {
            const item = this.createConceptItem(concept);
            this.container.appendChild(item);
        });
    }

    createConceptItem(concept) {
        const item = document.createElement('div');
        item.className = `concept-item ${concept.status}`;
        
        const info = document.createElement('div');
        info.className = 'concept-info';
        
        const name = document.createElement('div');
        name.className = 'concept-name';
        name.textContent = concept.name;
        
        const status = document.createElement('div');
        status.className = 'concept-status';
        status.textContent = this.getStatusText(concept.status);
        
        const theta = document.createElement('div');
        theta.className = 'concept-theta';
        theta.textContent = `Ability: θ = ${concept.theta}`;
        
        info.appendChild(name);
        info.appendChild(status);
        info.appendChild(theta);
        
        const progress = document.createElement('div');
        progress.className = 'concept-progress';
        progress.innerHTML = `
            <div class="progress-bar" style="width: 100px; height: 20px;">
                <div class="progress-fill" style="width: ${concept.progress_percent}%"></div>
            </div>
            <span style="font-size: 0.9em; margin-left: 10px;">${Math.round(concept.progress_percent)}%</span>
        `;
        
        item.appendChild(info);
        item.appendChild(progress);
        
        // Add click handler for opened/mastered concepts
        if (concept.status !== 'locked') {
            item.style.cursor = 'pointer';
            item.addEventListener('click', () => {
                this.onConceptClick(concept);
            });
        }
        
        return item;
    }

    getStatusText(status) {
        const statusMap = {
            'locked': '🔒 Locked',
            'opened': '📖 In Progress',
            'mastered': '✅ Mastered'
        };
        return statusMap[status] || status;
    }

    async onConceptClick(concept) {
        // Could show recommended questions for this topic
        console.log('Concept clicked:', concept);
        
        try {
            const recommendations = await apiClient.getRecommendedQuestions(concept.name, 3);
            
            if (recommendations.recommendations.length > 0) {
                const message = `Recommended questions for ${concept.name}:\n\n` +
                    recommendations.recommendations.map((q, i) => 
                        `${i + 1}. ${q.name} (Difficulty: ${q.difficulty_level})`
                    ).join('\n');
                
                alert(message);
            }
        } catch (error) {
            console.error('Failed to get recommendations:', error);
        }
    }

    async refresh() {
        await this.load();
    }
}

