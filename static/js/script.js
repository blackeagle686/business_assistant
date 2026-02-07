const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const loadingIndicator = document.getElementById('ai-loading');

let sessionId = null;
let currentStatus = 'initial'; // initial, clarification, done

// Auto-resize textarea
messageInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Send Message
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    // UI Updates
    addMessage(text, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto';
    showLoading(true);

    try {
        if (currentStatus === 'initial') {
            await handleIdeaSubmission(text);
        } else if (currentStatus === 'clarification') {
            await handleClarification(text);
        }
    } catch (error) {
        addMessage("Error: " + error.message, 'ai');
        console.error(error);
    } finally {
        showLoading(false);
    }
}

async function handleIdeaSubmission(ideaText) {
    const response = await fetch('/api/idea/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea_text: ideaText, session_id: "" }) // New session
    });

    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errorMessage = errData.detail || response.statusText || "Unknown API Error";
        throw new Error(`API Error (${response.status}): ${errorMessage}`);
    }

    const data = await response.json();
    sessionId = data.session_id;

    if (data.status === 'clarification_required') {
        currentStatus = 'clarification';

        // Render detailed questions
        const questionsList = data.questions.map(q => `<li class="mb-2">${q.question_text}</li>`).join('');
        const msg = `
            <p><strong>${data.message || 'I need a few more details to build a solid plan:'}</strong></p>
            <ul>${questionsList}</ul>
            <p class="small mt-2"><em>Please answer these questions in your next message.</em></p>
        `;
        addMessage(msg, 'ai');

        // Store questions
        window.currentQuestions = data.questions;
    } else {
        // Direct success (unlikely given logic, but handle it)
        addMessage("Idea accepted without clarification. Generating plan...", 'ai');
        // Logic to jump straight to results if supported
    }
}

async function handleClarification(answerText) {
    // For this MVP, we treat the whole block as answers to all questions.
    // We map the same answer text to all question IDs just to satisfy the backend schema if it requires a map.
    // Ideally, the backend should be smart enough to take one big string, but let's see.

    // Looking at main.py, it expects `answers: Dict[str, str]` (question_id -> answer)
    // We will just map the single text to all IDs or a special 'general_answer' key if backend supports it.
    // But since backend likely uses the values, we will just assign the full text to the first question
    // or distribute it. Let's send it as a single block for all for now to be safe.

    const answersMap = {};
    if (window.currentQuestions) {
        window.currentQuestions.forEach((q, idx) => {
            answersMap[q.question_id] = idx === 0 ? answerText : "See above";
            // OR better: just pass the full text to all? No, that confuses RAG.
            // Best approach without structured form: 
            // Send the full text associated with the first question, others get "Same as above" 
            // This is a hack. Ideally we should have a form. 
            // BUT, for now let's just send the full text for EACH to ensure context is there, 
            // or modify backend. 
            // Let's stick to the previous logic but clearer:
            answersMap[q.question_id] = answerText;
        });
    }

    const response = await fetch('/api/idea/clarify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: sessionId,
            answers: answersMap
        })
    });

    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errorMessage = errData.detail || response.statusText || "Unknown API Error";
        throw new Error(`API Error (${response.status}): ${errorMessage}`);
    }

    const data = await response.json();

    if (data.status === 'complete') {
        addMessage(`
            <i class="bi bi-check-circle-fill text-success me-2"></i>
            <strong>Plan Generated Successfully!</strong>
            <p>Redirecting you to your dashboard in a moment...</p>
        `, 'ai');

        setTimeout(() => {
            window.location.href = `/static/results.html?session_id=${sessionId}`;
        }, 2000);
    } else {
        addMessage("Something unexpected happened. Status: " + data.status, 'ai');
    }
}

function addMessage(html, sender) {
    const div = document.createElement('div');
    div.classList.add('message-bubble', sender === 'user' ? 'user-msg' : 'ai-msg');

    // Parse markdown for AI messages if needed, handled by simple HTML for now or `marked`
    if (sender === 'ai' && typeof marked !== 'undefined') {
        // If html contains markdown symbols, parse it.
        // But our inputs here are mostly HTML constructed strings. 
        // If raw text comes in:
        if (!html.trim().startsWith('<')) {
            div.innerHTML = marked.parse(html);
        } else {
            div.innerHTML = html;
        }
    } else {
        div.innerHTML = html; // User raw text or basic HTML
    }

    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Hide welcome hero if it exists
    const hero = document.getElementById('welcome-hero');
    if (hero) hero.style.display = 'none';
}

function showLoading(show) {
    loadingIndicator.classList.toggle('d-none', !show);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

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
