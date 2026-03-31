const config = {
    apiHost: window.location.origin,
    sovereignKey: "SOVEREIGN_HUB_2026_V3"
};

const chatViewport = document.getElementById('conversation-viewport');
const textArea = document.getElementById('nexus-input');
const sendBtn = document.getElementById('send-trigger');
const sidebar = document.getElementById('cognitive-sidebar');
const shardContainer = document.getElementById('shard-container');
const closeSidebar = document.getElementById('close-sidebar');
const indicators = document.getElementById('active-indicators');

let isProcessing = false;

// Event Listeners
textArea.addEventListener('input', handleInput);
textArea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});
sendBtn.addEventListener('click', handleSend);
closeSidebar.addEventListener('click', () => {
    sidebar.classList.add('hidden');
});

function handleInput() {
    textArea.style.height = 'auto';
    textArea.style.height = Math.min(textArea.scrollHeight, 250) + 'px';
    sendBtn.disabled = textArea.value.trim() === '' || isProcessing;
}

async function handleSend() {
    const text = textArea.value.trim();
    if (!text || isProcessing) return;

    textArea.value = '';
    handleInput();
    appendMessage('user', text);
    
    await communicateWithBuddy(text);
}

function appendMessage(role, text) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    
    const content = document.createElement('div');
    content.className = 'msg-content';
    
    // Minimal Markdown + Shard extraction
    let cleanText = text;
    if (text.includes("--- PROACTIVE_SHARD ---")) {
        const parts = text.split("--- PROACTIVE_SHARD ---");
        cleanText = parts[0].trim();
        const shardData = parts[1].trim();
        createCognitiveShard(shardData);
    }

    content.innerText = cleanText;
    msg.appendChild(content);
    chatViewport.appendChild(msg);
    chatViewport.scrollTop = chatViewport.scrollHeight;
}

async function communicateWithBuddy(goal) {
    isProcessing = true;
    sendBtn.disabled = true;
    
    // Add temporary thinking indicator
    const thinking = document.createElement('div');
    thinking.className = 'message buddy thinking';
    thinking.innerHTML = '<div class="msg-content">Buddy is reflecting...</div>';
    chatViewport.appendChild(thinking);

    try {
        const response = await fetch(`${config.apiHost}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Sovereign-Key': config.sovereignKey
            },
            body: JSON.stringify({
                goal: goal,
                context: { environment: "cloud", client: "nexus_v2" },
                mode: "MACRO"
            })
        });
        
        const data = await response.json();
        chatViewport.removeChild(thinking);

        if (data.status === 'success') {
            const result = data.results[0];
            appendMessage('buddy', result.reasoning || "Mission logic synthesized.");
            
            // JIT Indicators
            updateJITIndicators(result.tethered_organs || ['system_o', 'vertex_o']);
        } else {
            appendMessage('buddy', `Error: ${data.detail}`);
        }
    } catch (err) {
        chatViewport.removeChild(thinking);
        appendMessage('buddy', `Connection Fault: ${err.message}`);
    } finally {
        isProcessing = false;
        handleInput();
    }
}

function createCognitiveShard(data) {
    sidebar.classList.remove('hidden');
    
    const shard = document.createElement('div');
    shard.className = 'enrichment-shard';
    
    // Basic detection for shard type
    let type = "SOTA_PULSE";
    if (data.toLowerCase().includes("improvement")) type = "SUGGESTION";
    if (data.toLowerCase().includes("audit")) type = "PURITY_AUDIT";

    shard.innerHTML = `
        <header>
            <span class="shard-type">${type}</span>
            <span class="shard-time">${new Date().toLocaleTimeString()}</span>
        </header>
        <div class="shard-body">${data}</div>
    `;
    
    shardContainer.prepend(shard);
}

function updateJITIndicators(organs) {
    indicators.innerHTML = '';
    organs.forEach(org => {
        const p = document.createElement('span');
        p.className = 'pill';
        p.innerText = org.toUpperCase();
        indicators.appendChild(p);
    });
}

// Initial Sync
updateJITIndicators(['system_o', 'vertex_o']);
