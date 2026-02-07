document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');

    if (!sessionId) {
        alert("No Session ID found. Redirecting to home.");
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch(`/api/dashboard/${sessionId}`);
        if (!response.ok) throw new Error("Failed to fetch dashboard data");

        const data = await response.json();
        renderDashboard(data);
    } catch (error) {
        console.error(error);
        document.getElementById('loading-text').innerText = "Error loading data: " + error.message;
        document.getElementById('loading-text').classList.add('text-danger');
    }
});

function renderDashboard(data) {
    // Hide loading, show content
    document.getElementById('loading-overlay').classList.add('d-none');
    document.getElementById('dashboard-content').classList.remove('d-none');

    const plan = data.plan;
    if (!plan) return;

    // Executive Summary
    const execSummaryText = marked.parse(plan.executive_summary);
    document.getElementById('exec-summary').innerHTML = execSummaryText;
    // Add Chat Button to Exec Summary Card Title
    addChatButton(
        document.querySelector('#exec-summary').previousElementSibling, // The h2 title
        "Executive Summary",
        () => plan.executive_summary
    );

    // Business Model Canvas
    const bmcMappings = [
        { id: 'bmc-partners', topic: 'Key Partners', data: plan.business_model.key_partners },
        { id: 'bmc-activities', topic: 'Key Activities', data: plan.business_model.key_activities },
        { id: 'bmc-resources', topic: 'Key Resources', data: plan.business_model.key_resources },
        { id: 'bmc-value', topic: 'Value Proposition', data: plan.business_model.value_proposition },
        { id: 'bmc-relationships', topic: 'Customer Relationships', data: plan.business_model.customer_relationships },
        { id: 'bmc-channels', topic: 'Channels', data: plan.business_model.channels },
        { id: 'bmc-customers', topic: 'Customer Segments', data: plan.business_model.customer_segments },
        { id: 'bmc-costs', topic: 'Cost Structure', data: plan.business_model.cost_structure },
        { id: 'bmc-revenue', topic: 'Revenue Streams', data: plan.business_model.revenue_streams },
    ];

    bmcMappings.forEach(item => {
        populateList(item.id, item.data);
        // Find the header (h6) inside the card wrapper of this list
        const wrapper = document.getElementById(item.id).closest('.bmc-card');
        addChatButton(wrapper, item.topic, () => item.data.join('\n'));
    });

    // Market Analysis
    const marketHtml = `
        <p><strong>Market Size:</strong> ${plan.market_analysis.market_size}</p>
        <h6>Growth Trends:</h6>
        <ul>${plan.market_analysis.growth_trends.map(x => `<li>${x}</li>`).join('')}</ul>
        <h6>Competitors:</h6>
        <ul>${plan.market_analysis.competitors.map(x => `<li>${x}</li>`).join('')}</ul>
    `;
    const marketContainer = document.getElementById('market-analysis-text');
    marketContainer.innerHTML = marketHtml;
    addChatButton(
        marketContainer.closest('.card').querySelector('.card-title'),
        "Market Analysis",
        () => `Market Size: ${plan.market_analysis.market_size}\nTrends: ${plan.market_analysis.growth_trends.join(', ')}\nCompetitors: ${plan.market_analysis.competitors.join(', ')}`
    );

    // KPIs
    const kpiContainer = document.getElementById('kpi-container');
    plan.kpis.forEach(kpi => {
        const div = document.createElement('div');
        div.className = 'mb-3 pb-2 border-bottom border-secondary';
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
               <h6 class="fw-bold mb-0">${kpi.name}</h6>
               <!-- Individual KPI chat? Maybe overkill, let's put one main KPI button -->
            </div>
            <p class="small text-dim mb-1">${kpi.description}</p>
            <div class="d-flex justify-content-between small">
                <span class="text-highlight">Freq: ${kpi.frequency}</span>
                <span class="text-warning-custom">Imp: ${kpi.importance}</span>
            </div>
        `;
        kpiContainer.appendChild(div);
    });
    // Add Chat to KPI Card
    addChatButton(
        kpiContainer.closest('.card').querySelector('.card-title'),
        "KPIs",
        () => JSON.stringify(plan.kpis, null, 2)
    );

    // Risks & Recommendations
    populateList('risk-list', plan.market_analysis.risks);
    addChatButton(
        document.getElementById('risk-list').previousElementSibling, // h5 alert heading
        "Risks",
        () => plan.market_analysis.risks.join('\n')
    );

    document.getElementById('recommendations-text').innerHTML = marked.parse(plan.recommendations);
    addChatButton(
        document.getElementById('recommendations-text').previousElementSibling,
        "Recommendations",
        () => plan.recommendations
    );
}

function populateList(elementId, items) {
    const el = document.getElementById(elementId);
    if (!el || !items) return;
    el.innerHTML = items.map(item => `<li>${item}</li>`).join('');
}

// Theme Toggling
const themeToggleBtn = document.getElementById('theme-toggle');
const htmlElement = document.documentElement;

// Check saved theme
const savedTheme = localStorage.getItem('theme') || 'dark';
htmlElement.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

themeToggleBtn.addEventListener('click', () => {
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    htmlElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    const icon = themeToggleBtn.querySelector('i');
    if (theme === 'dark') {
        icon.classList.remove('bi-moon-stars');
        icon.classList.add('bi-sun');
    } else {
        icon.classList.remove('bi-sun');
        icon.classList.add('bi-moon-stars');
    }
}
// Chat State
let currentChatTopic = "";
let currentChatContext = "";
const chatHistoryMap = {}; // topic -> array of html strings

function openChat(topic, context) {
    currentChatTopic = topic;
    currentChatContext = context;

    // safe DOM elements
    const modalTitle = document.getElementById('chatModalLabel');
    const chatHistoryDiv = document.getElementById('modal-chat-history');

    modalTitle.innerText = `Discuss: ${topic}`;
    chatHistoryDiv.innerHTML = chatHistoryMap[topic] || '<div class="text-center text-muted small mt-5">Start a conversation about this section...</div>';

    const modal = new bootstrap.Modal(document.getElementById('chatModal'));
    modal.show();

    // Scroll to bottom
    setTimeout(() => {
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
        document.getElementById('modal-chat-input').focus();
    }, 500);
}

function addChatButton(container, topic, getContextFn) {
    // container can be an element or a selector string
    const parent = typeof container === 'string' ? document.querySelector(container) : container;
    if (!parent) return;

    // Create handy button
    const btn = document.createElement('button');
    btn.className = "btn btn-sm btn-outline-accent ms-2 border-0";
    btn.innerHTML = '<i class="bi bi-chat-dots-fill"></i>';
    btn.title = "Chat about this section";
    btn.onclick = (e) => {
        e.stopPropagation(); // prevent card clicks
        const context = getContextFn();
        openChat(topic, context);
    };

    // Attempt to append next to the header if possible, or just inside the container
    // If container is a header element (h1-h6), append directly
    if (['H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(parent.tagName)) {
        parent.appendChild(btn);
    } else {
        // Try to find a header inside
        const header = parent.querySelector('h1, h2, h3, h4, h5, h6, .card-title, .alert-heading');
        if (header) {
            header.appendChild(btn);
        } else {
            // Fallback: top right absolute or just append
            parent.appendChild(btn);
        }
    }
}

// Send Message
document.getElementById('modal-send-btn').addEventListener('click', sendChatMessage);
document.getElementById('modal-chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

async function sendChatMessage() {
    const input = document.getElementById('modal-chat-input');
    const text = input.value.trim();
    if (!text) return;

    const chatHistoryDiv = document.getElementById('modal-chat-history');
    const topic = currentChatTopic;

    // 1. Add User Message
    const userMsgHTML = `<div class="message-bubble user-msg ms-auto">${text}</div>`;

    // Clear initial placeholder if exists
    if (chatHistoryDiv.innerHTML.includes('Start a conversation')) chatHistoryDiv.innerHTML = '';

    chatHistoryDiv.innerHTML += userMsgHTML;
    input.value = '';
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;

    // Save to local cache
    chatHistoryMap[topic] = chatHistoryDiv.innerHTML;

    // 2. Add Loading Bubble
    const loadingId = 'chat-loading-' + Date.now();
    chatHistoryDiv.innerHTML += `<div id="${loadingId}" class="message-bubble ai-msg me-auto"><span class="spinner-border spinner-border-sm" role="status"></span> Thinking...</div>`;
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;

    try {
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session_id');

        const response = await fetch('/api/assistant/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                topic: topic,
                context: currentChatContext,
                message: text
            })
        });

        const data = await response.json();

        // Remove loading
        document.getElementById(loadingId).remove();

        if (response.ok) {
            // Add AI Message
            let replyHtml = data.reply;
            if (typeof marked !== 'undefined') replyHtml = marked.parse(replyHtml);

            chatHistoryDiv.innerHTML += `<div class="message-bubble ai-msg me-auto">${replyHtml}</div>`;
        } else {
            chatHistoryDiv.innerHTML += `<div class="message-bubble ai-msg me-auto text-danger">Error: ${data.detail || 'Unknown error'}</div>`;
        }

    } catch (e) {
        document.getElementById(loadingId).remove();
        chatHistoryDiv.innerHTML += `<div class="message-bubble ai-msg me-auto text-danger">Network Error: ${e.message}</div>`;
    }

    // Update cache
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
    chatHistoryMap[topic] = chatHistoryDiv.innerHTML;
}
