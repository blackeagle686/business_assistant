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
    document.getElementById('exec-summary').innerHTML = marked.parse(plan.executive_summary);

    // Business Model Canvas
    populateList('bmc-partners', plan.business_model.key_partners);
    populateList('bmc-activities', plan.business_model.key_activities);
    populateList('bmc-resources', plan.business_model.key_resources);
    populateList('bmc-value', plan.business_model.value_proposition);
    populateList('bmc-relationships', plan.business_model.customer_relationships);
    populateList('bmc-channels', plan.business_model.channels);
    populateList('bmc-customers', plan.business_model.customer_segments);
    populateList('bmc-costs', plan.business_model.cost_structure);
    populateList('bmc-revenue', plan.business_model.revenue_streams);

    // Market Analysis
    const marketHtml = `
        <p><strong>Market Size:</strong> ${plan.market_analysis.market_size}</p>
        <h6>Growth Trends:</h6>
        <ul>${plan.market_analysis.growth_trends.map(x => `<li>${x}</li>`).join('')}</ul>
        <h6>Competitors:</h6>
        <ul>${plan.market_analysis.competitors.map(x => `<li>${x}</li>`).join('')}</ul>
    `;
    document.getElementById('market-analysis-text').innerHTML = marketHtml;

    // KPIs
    const kpiContainer = document.getElementById('kpi-container');
    plan.kpis.forEach(kpi => {
        const div = document.createElement('div');
        div.className = 'mb-3 pb-2 border-bottom border-secondary';
        div.innerHTML = `
            <h6 class="fw-bold">${kpi.name}</h6>
            <p class="small text-muted mb-1">${kpi.description}</p>
            <div class="d-flex justify-content-between small">
                <span class="text-info">Freq: ${kpi.frequency}</span>
                <span class="text-warning">Imp: ${kpi.importance}</span>
            </div>
        `;
        kpiContainer.appendChild(div);
    });

    // Risks & Recommendations
    populateList('risk-list', plan.market_analysis.risks);
    document.getElementById('recommendations-text').innerHTML = marked.parse(plan.recommendations);
}

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
