/**
 * Onboarding Modal Manager
 * Handles the interactive onboarding experience for first-time users
 */

class OnboardingModal {
    constructor() {
        this.currentStep = 0;
        this.totalSteps = 5;
        this.storageKey = 'adapticode_onboarding_completed';
        this.init();
    }

    init() {
        // Check if onboarding has been completed in this session
        if (this.hasCompletedOnboarding()) {
            return;
        }

        // Show modal on page load
        this.showModal();
        this.attachEventListeners();
        this.updateStepDisplay();
    }

    hasCompletedOnboarding() {
        // Use sessionStorage instead of localStorage
        // This means onboarding will show again on each new browser session (server restart)
        return sessionStorage.getItem(this.storageKey) === 'true';
    }

    markOnboardingComplete() {
        // Store in sessionStorage - will reset when browser tab/window closes or server restarts
        sessionStorage.setItem(this.storageKey, 'true');
    }

    showModal() {
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        }
    }

    hideModal() {
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
            document.body.style.overflow = ''; // Restore scrolling
        }
    }

    attachEventListeners() {
        // Next button
        const nextBtn = document.getElementById('onboarding-next');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextStep());
        }

        // Previous button
        const prevBtn = document.getElementById('onboarding-prev');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.previousStep());
        }

        // Finish button
        const finishBtn = document.getElementById('onboarding-finish');
        if (finishBtn) {
            finishBtn.addEventListener('click', () => this.finish());
        }

        // Step dots
        const dots = document.querySelectorAll('.step-dot');
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => this.goToStep(index));
        });

        // Close on overlay click (optional - commented out for safety)
        // const overlay = document.getElementById('onboarding-overlay');
        // overlay.addEventListener('click', (e) => {
        //     if (e.target === overlay) {
        //         this.finish();
        //     }
        // });
    }

    nextStep() {
        if (this.currentStep < this.totalSteps - 1) {
            this.currentStep++;
            this.updateStepDisplay();
        }
    }

    previousStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.updateStepDisplay();
        }
    }

    goToStep(stepIndex) {
        if (stepIndex >= 0 && stepIndex < this.totalSteps) {
            this.currentStep = stepIndex;
            this.updateStepDisplay();
        }
    }

    updateStepDisplay() {
        // Hide all steps
        const steps = document.querySelectorAll('.onboarding-step');
        steps.forEach(step => step.classList.remove('active'));

        // Show current step
        const currentStepElement = document.getElementById(`step-${this.currentStep}`);
        if (currentStepElement) {
            currentStepElement.classList.add('active');
        }

        // Update step indicators
        const dots = document.querySelectorAll('.step-dot');
        dots.forEach((dot, index) => {
            if (index === this.currentStep) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });

        // Update button visibility
        this.updateButtons();
    }

    updateButtons() {
        const prevBtn = document.getElementById('onboarding-prev');
        const nextBtn = document.getElementById('onboarding-next');
        const finishBtn = document.getElementById('onboarding-finish');

        // Previous button
        if (prevBtn) {
            prevBtn.style.display = this.currentStep === 0 ? 'none' : 'inline-block';
        }

        // Next button
        if (nextBtn) {
            nextBtn.style.display = this.currentStep === this.totalSteps - 1 ? 'none' : 'inline-block';
        }

        // Finish button
        if (finishBtn) {
            finishBtn.style.display = this.currentStep === this.totalSteps - 1 ? 'inline-block' : 'none';
        }
    }

    finish() {
        this.markOnboardingComplete();
        this.hideModal();
    }

    // Public method to replay onboarding (for guide page)
    replay() {
        this.currentStep = 0;
        this.updateStepDisplay();
        this.showModal();
    }
}

/**
 * Dashboard Help Banner Manager
 * Handles the dismissible help banner on the dashboard
 */
class DashboardHelpBanner {
    constructor() {
        this.storageKey = 'adapticode_dashboard_banner_dismissed';
        this.init();
    }

    init() {
        const banner = document.getElementById('dashboard-help-banner');
        if (!banner) return;

        // Check if banner has been dismissed
        if (this.isDismissed()) {
            banner.classList.add('hidden');
            return;
        }

        // Show banner
        banner.classList.remove('hidden');

        // Attach close button listener
        const closeBtn = document.getElementById('banner-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.dismiss());
        }
    }

    isDismissed() {
        return localStorage.getItem(this.storageKey) === 'true';
    }

    dismiss() {
        localStorage.setItem(this.storageKey, 'true');
        const banner = document.getElementById('dashboard-help-banner');
        if (banner) {
            banner.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                banner.classList.add('hidden');
            }, 300);
        }
    }
}

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-20px);
        }
    }
`;
document.head.appendChild(style);

/**
 * Initialize onboarding system
 */
function initOnboarding() {
    // Initialize onboarding modal (only on home page or first visit)
    if (document.getElementById('onboarding-overlay')) {
        window.onboardingModal = new OnboardingModal();
    }

    // Initialize dashboard help banner (only on dashboard page)
    if (document.getElementById('dashboard-help-banner')) {
        window.dashboardBanner = new DashboardHelpBanner();
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOnboarding);
} else {
    initOnboarding();
}

// Export for manual control if needed
window.OnboardingModal = OnboardingModal;
window.DashboardHelpBanner = DashboardHelpBanner;
