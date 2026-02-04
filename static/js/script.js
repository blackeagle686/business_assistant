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

    const data = await response.json();
    sessionId = data.session_id;

    if (data.status === 'clarification_required') {
        currentStatus = 'clarification';
        addMessage(data.message, 'ai');

        // Render detailed questions
        const questionsList = data.questions.map(q => `<li>${q.question_text}</li>`).join('');
        addMessage(`<strong>Please answer the following:</strong><ul>${questionsList}</ul>`, 'ai');

        // Store questions for next step logic (simplified here)
        window.currentQuestions = data.questions;
    }
}

async function handleClarification(answerText) {
    // Ideally, we'd parse specific answers. For this MVP, we treat the whole block as answers.
    // Creating a simple map assuming the user answered sequentially or in bulk.
    const answersMap = {};
    if (window.currentQuestions) {
        window.currentQuestions.forEach((q, idx) => {
            answersMap[q.question_id] = answerText; // simplistic mapping 
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

    const data = await response.json();

    if (data.status === 'complete') {
        addMessage("Plan generated! Redirecting to dashboard...", 'ai');
        setTimeout(() => {
            window.location.href = `/static/results.html?session_id=${sessionId}`;
        }, 1500);
    }
}

function addMessage(html, sender) {
    const div = document.createElement('div');
    div.classList.add('message-bubble', sender === 'user' ? 'user-msg' : 'ai-msg');
    div.innerHTML = html;
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
