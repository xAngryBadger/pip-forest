/**
 * SRF V2 - Application JavaScript
 * Modern, smooth interactions
 */

// ========================================
// State Management
// ========================================
const AppState = {
    currentScreen: 'dashboard',
    modalsOpen: [],
    notifications: [],
    session: {
        active: true,
        version: '6.1',
        mode: 'BETA'
    }
};

// ========================================
// Navigation
// ========================================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const screenId = item.getAttribute('data-screen');
            if (screenId) {
                showScreen(screenId);
                updateActiveNav(item);
            }
        });
    });
}

function showScreen(screenId) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Show target screen
    const targetScreen = document.getElementById(`screen-${screenId}`);
    if (targetScreen) {
        targetScreen.classList.add('active');
        AppState.currentScreen = screenId;
        
        // Update page title
        updatePageTitle(screenId);
        
        // Screen-specific initialization
        onScreenShow(screenId);
    }
}

function updateActiveNav(activeItem) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    activeItem.classList.add('active');
}

function updatePageTitle(screenId) {
    const titles = {
        'dashboard': { title: 'Dashboard', subtitle: 'Visão geral do sistema' },
        'fazendas': { title: 'Fazendas', subtitle: 'Gerenciamento de propriedades' },
        'cronograma': { title: 'Cronograma', subtitle: 'Planejamento temporal' },
        'tarifas': { title: 'Tarifas & Centro de Trabalho', subtitle: 'Gestão de CT317 e CT Real' },
        'equipes': { title: 'Equipes', subtitle: 'Configuração de equipes' },
        'relatorios': { title: 'Dossiês & Relatórios', subtitle: 'Relatórios executivos' },
        'monitor': { title: 'Monitor', subtitle: 'Acompanhamento em tempo real' }
    };
    
    const pageInfo = titles[screenId] || titles['dashboard'];
    const titleEl = document.querySelector('.page-title');
    const subtitleEl = document.querySelector('.page-subtitle');
    
    if (titleEl) titleEl.textContent = pageInfo.title;
    if (subtitleEl) subtitleEl.textContent = pageInfo.subtitle;
}

function onScreenShow(screenId) {
    // Screen-specific logic
    switch(screenId) {
        case 'monitor':
            // Could initialize live monitoring here
            break;
        case 'fazendas':
            // Could load farm data
            break;
    }
}

// ========================================
// Modals
// ========================================
function initModals() {
    // Close on backdrop click
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) {
                closeModal(modal.id.replace('modal-', ''));
            }
        });
    });
}

function showModal(modalId) {
    const modal = document.getElementById(`modal-${modalId}`);
    if (modal) {
        modal.classList.add('active');
        AppState.modalsOpen.push(modalId);
        
        // Focus first input
        const firstInput = modal.querySelector('input, select');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(`modal-${modalId}`);
    if (modal) {
        modal.classList.remove('active');
        AppState.modalsOpen = AppState.modalsOpen.filter(id => id !== modalId);
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal.active').forEach(modal => {
        modal.classList.remove('active');
    });
    AppState.modalsOpen = [];
}

// ========================================
// Keyboard Shortcuts
// ========================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl + K for search
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-box input');
            if (searchInput) searchInput.focus();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            if (AppState.modalsOpen.length > 0) {
                closeModal(AppState.modalsOpen[AppState.modalsOpen.length - 1]);
            }
        }
        
        // Navigation shortcuts
        if (e.altKey) {
            const shortcuts = {
                '1': 'dashboard',
                '2': 'fazendas',
                '3': 'cronograma',
                '4': 'tarifas',
                '5': 'equipes',
                '6': 'relatorios',
                '7': 'monitor'
            };
            
            if (shortcuts[e.key]) {
                e.preventDefault();
                showScreen(shortcuts[e.key]);
                updateActiveNav(document.querySelector(`[data-screen="${shortcuts[e.key]}"]`));
            }
        }
    });
}

// ========================================
// Toast Notifications
// ========================================
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close">×</button>
    `;
    
    // Styles injected via CSS
    toast.style.cssText = `
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 20px;
        background: rgba(17, 24, 17, 0.95);
        border: 1px solid rgba(74, 222, 128, 0.2);
        border-radius: 12px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
        animation: slide-in-right 0.3s ease;
        min-width: 300px;
        max-width: 400px;
    `;
    
    const colors = {
        success: '#4ade80',
        error: '#fb7185',
        warning: '#fbbf24',
        info: '#60a5fa'
    };
    
    toast.style.borderLeft = `3px solid ${colors[type] || colors.info}`;
    
    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => {
        removeToast(toast);
    });
    
    container.appendChild(toast);
    
    // Auto remove
    if (duration > 0) {
        setTimeout(() => removeToast(toast), duration);
    }
    
    return toast;
}

function removeToast(toast) {
    toast.style.animation = 'slide-out-right 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
}

// ========================================
// File Upload
// ========================================
function initFileUploads() {
    const fileDrops = document.querySelectorAll('.file-drop');
    
    fileDrops.forEach(drop => {
        const input = drop.querySelector('input[type="file"]');
        
        // Drag events
        drop.addEventListener('dragover', (e) => {
            e.preventDefault();
            drop.classList.add('dragover');
        });
        
        drop.addEventListener('dragleave', () => {
            drop.classList.remove('dragover');
        });
        
        drop.addEventListener('drop', (e) => {
            e.preventDefault();
            drop.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        
        // Input change
        if (input) {
            input.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFileUpload(e.target.files[0]);
                }
            });
        }
    });
}

function handleFileUpload(file) {
    console.log('File uploaded:', file.name);
    showToast(`Arquivo "${file.name}" selecionado`, 'info', 3000);
    
    // Here you would integrate with atm_v6.1
    // e.g., send to Python backend
}

// ========================================
// Wizard Navigation
// ========================================
function initWizard() {
    const wizardSteps = document.querySelectorAll('.wizard-steps .step');
    
    wizardSteps.forEach(step => {
        step.addEventListener('click', () => {
            const stepNum = step.getAttribute('data-step');
            goToWizardStep(stepNum);
        });
    });
}

function goToWizardStep(stepNum) {
    document.querySelectorAll('.wizard-steps .step').forEach(step => {
        step.classList.remove('active');
        if (step.getAttribute('data-step') === stepNum) {
            step.classList.add('active');
        }
    });
}

// ========================================
// Search
// ========================================
function initSearch() {
    const searchInput = document.querySelector('.search-box input');
    
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 300);
        });
    }
}

function performSearch(query) {
    if (query.length < 2) return;
    
    console.log('Searching for:', query);
    // Here you would integrate search with atm_v6.1 data
}

// ========================================
// Session Management
// ========================================
function initSession() {
    // Could set up session monitoring here
    // e.g., ping backend to keep session alive
    
    setInterval(() => {
        // Session keepalive
        console.log('Session ping:', new Date().toISOString());
    }, 60000);
}

// ========================================
// Initialize
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initModals();
    initKeyboardShortcuts();
    initFileUploads();
    initWizard();
    initSearch();
    initSession();
    
    // Welcome toast
    setTimeout(() => {
        showToast('Bem-vindo ao SRF v6.1! 🌲', 'success', 4000);
    }, 500);
    
    console.log('SRF V2 initialized');
});

// ========================================
// Global Exports (for onclick handlers)
// ========================================
window.showScreen = showScreen;
window.showModal = showModal;
window.closeModal = closeModal;
window.showToast = showToast;
