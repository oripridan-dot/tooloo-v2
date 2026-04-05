// Always route to the Sovereign Cloud backend.
const CLOUD_URL = "https://buddys-chat-gru3xdvw6a-zf.a.run.app";
const config = {
    sovereignKey: "SOVEREIGN_HUB_2026_V3",
    apiHost: CLOUD_URL,
};

let socket = null;

// Configure marked.js for safe rendering
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,       // \n → <br>
        gfm: true,          // GitHub Flavored Markdown
        headerIds: false,   // No anchor IDs (XSS safe)
        mangle: false
    });
}

function renderMarkdown(text) {
    if (typeof marked === 'undefined') return text;
    try {
        return marked.parse(text);
    } catch (e) {
        return text;
    }
}

const dom = {
    stream: document.getElementById('chat-messages'),
    input: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    modelPicker: document.getElementById('model-picker'),
    weave: document.getElementById('shard-tray'),
    sandbox: {
        panel: document.getElementById('manifestation-sandbox'),
        content: document.getElementById('sandbox-content'),
        close: document.getElementById('close-sandbox')
    },
    mission: {
        log: document.getElementById('mission-log-stream'),
        info: document.getElementById('active-mission-info'),
        goal: document.getElementById('mission-goal-label')
    },
    paths: {
        overlay: document.getElementById('path-selection-overlay'),
        container: document.getElementById('path-cards-container')
    },
    hud: {
        purity: document.getElementById('tel-purity'),
        vitality: document.getElementById('tel-vitality'),
        emergence: document.getElementById('tel-emergence'),
        story: document.getElementById('tel-story'),
        human: document.getElementById('tel-human'),
        node: document.getElementById('hub-node-id'),
        lamp: document.getElementById('hub-health-pulse'),
        purityGauge: document.getElementById('purity-gauge'),
        vitalityGauge: document.getElementById('vitality-gauge'),
        delta: document.getElementById('tel-delta'),
        cost: document.getElementById('tel-cost'),
        calibrationPulse: document.getElementById('calibration-pulse-dot'),
        stage: document.getElementById('tel-stage')
    },
    handover: {
        overlay: document.getElementById('handover-overlay'),
        track: document.getElementById('handover-track'),
        progress: document.getElementById('handover-progress')
    },
    northStar: {
        panel: document.getElementById('north-star-dashboard'),
        macro: document.getElementById('ns-macro-goal'),
        focus: document.getElementById('ns-current-focus'),
        roadmap: document.getElementById('ns-micro-goals'),
        milestones: document.getElementById('ns-milestones'),
        status: document.getElementById('ns-sync-status'),
        stashBtn: document.getElementById('stash-pivot-btn')
    },
    promptbar: {
        container: document.getElementById('sovereign-promptbar'),
        dynamics: document.getElementById('input-dynamics'),
        missionId: document.getElementById('active-mission-id')
    }
};

let currentThinkingBubble = null;
let isProcessing = false;
let typingQueue = [];
let isTyping = false;
let currentStreamingMessage = null;
let streamingText = '';  // accumulates raw text during streaming
let userScrolledUp = false;  // scroll-lock flag

// --- SOTA UX Telemetry (Rule 7/16) ---
class UXTelemetry {
    constructor() {
        this.metrics = { fps: 60, fid: 0, memory: 0, jank: 0, pulseWeightB: 0, overheadMs: 0 };
        this.frameTimes = [];
        this.observer = null;
        this.isActive = true;
    }

    start() {
        if (!this.isActive) return;
        console.log("Sovereign Telemetry: UX Pulse Awakening...");
        this.initFPS();
        this.initFID();
        this.initMemory();
        this.broadcast(); // Initiate recursive adaptive pulse (Rule 7)
    }

    initFPS() {
        const checkFPS = (time) => {
            if (!this.isActive) return;
            this.frameTimes.push(time);
            if (this.frameTimes.length > 60) {
                const diff = this.frameTimes[this.frameTimes.length - 1] - this.frameTimes[0];
                this.metrics.fps = Math.round(60 / (diff / 1000));
                if (this.metrics.fps < 30) this.metrics.jank++;
                this.frameTimes = [];
            }
            requestAnimationFrame(checkFPS);
        };
        requestAnimationFrame(checkFPS);
    }

    initFID() {
        try {
            this.observer = new PerformanceObserver((list) => {
                if (!this.isActive) return;
                for (const entry of list.getEntries()) {
                    if (entry.entryType === 'first-input') {
                        this.metrics.fid = entry.processingStart - entry.startTime;
                    }
                }
            });
            this.observer.observe({ type: 'first-input', buffered: true });
        } catch (e) { console.warn("FID Observer Not Supported"); }
    }

    initMemory() {
        if (performance.memory) {
            setInterval(() => {
                if (!this.isActive) return;
                this.metrics.memory = Math.round(performance.memory.usedJSHeapSize / 1048576);
            }, 5000);
        }
    }

    broadcast() {
        if (!this.isActive) return;
        if (socket && socket.readyState === WebSocket.OPEN) {
            const start = performance.now();
            
            // Rule 7: Payload Compression (Minified Keys)
            const payload = {
                f: this.metrics.fps,
                fi: this.metrics.fid,
                m: this.metrics.memory,
                j: this.metrics.jank,
                t: Date.now(),
                n: dom.hud.node.innerText
            };
            
            // Consolidate 'Heartbeat' Request: Ask for Telemetry/Shards in the same pulse
            const msg = JSON.stringify({
                type: "ux_telemetry",
                payload: payload,
                request_sync: true // Ask Hub for latest health/shards
            });
            
            this.metrics.pulseWeightB = new Blob([msg]).size;
            socket.send(msg);
            this.metrics.overheadMs = performance.now() - start;
            
            // Adaptive Sampling: Slow down if healthy, speed up if janky
            let nextInterval = 10000;
            if (this.metrics.fps < 30) nextInterval = 5000;
            else if (parseFloat(dom.hud.purity.innerText) > 0.98) nextInterval = 30000;

            this.metrics.jank = 0;
            
            // Self-correction for next broadcast
            clearTimeout(this.broadcastTimer);
            this.broadcastTimer = setTimeout(() => this.broadcast(), nextInterval);
        }
    }
}

const ux = new UXTelemetry();

// --- Initialize Telemetry Pulse ---
async function startTelemetryPulse() {
    ux.start(); // Start SOTA Performance Loop
    restoreHistory(); // Tier 2: Session Resumption
}

async function restoreHistory() {
    try {
        console.log("Sovereign Nexus: Restoring Session History...");
        const response = await fetch(`${config.apiHost}/context/history?limit=20`, {
            headers: { 'X-Sovereign-Key': config.sovereignKey }
        });
        const data = await response.json();
        if (data.status === 'success' && data.messages.length > 0) {
            // Clear current stream if any (optional, but good for clean restoration)
            dom.stream.innerHTML = '';
            data.messages.forEach(msg => {
                appendMessage(msg.role === 'user' ? 'user' : 'buddy', msg.content, msg.dynamics);
            });
            dom.stream.scrollTop = dom.stream.scrollHeight;
        }
    } catch (err) {
        console.warn("History Restoration Fault:", err);
    }
}

async function updateMemoryShards() {
    try {
        const response = await fetch(`${config.apiHost}/memory/shards?limit=5`, {
            headers: { 'X-Sovereign-Key': config.sovereignKey }
        });
        const data = await response.json();
        if (data.status === 'success') {
            renderShardTray(data.shards);
        }
    } catch (err) {
        console.error("Shard Retrieval Error", err);
    }
}

function renderShardTray(shards) {
    if (!shards || !dom.weave) return;
    
    // Simple diffing to avoid flickering
    const currentCount = dom.weave.children.length;
    if (currentCount === shards.length) return;

    dom.weave.innerHTML = '';
    shards.forEach(shard => {
        const el = document.createElement('div');
        el.className = 'shard-weave';
        
        const type = shard.metadata?.type || 'ENGRAM';
        const tier = shard.tier || 'MEDIUM';
        const source = shard.metadata?.source || 'Workspace';
        const fileName = source.split('/').pop();

        el.innerHTML = `
            <header class="shard-hdr" style="font-size: 0.6rem; display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span class="shard-tag" style="color: var(--vibe-color); font-weight: 700;">${type}</span>
                <span class="shard-category" style="opacity: 0.5;">${tier.toUpperCase()}</span>
            </header>
            <div class="shard-text" style="font-size: 0.75rem; line-height: 1.4; color: var(--text-secondary); height: 40px; overflow: hidden; text-overflow: ellipsis;">
                ${fileName}: Ingested metadata and SOTA context.
            </div>
            <footer class="shard-footer" style="font-size: 0.550rem; opacity: 0.3; margin-top: 0.5rem; text-align: right;">
                ${new Date().toLocaleTimeString()}
            </footer>
        `;
        dom.weave.appendChild(el);
    });
}

async function updateTelemetry() {
    try {
        const response = await fetch(`${config.apiHost}/health`, {
            headers: { 'X-Sovereign-Key': config.sovereignKey }
        });
        const data = await response.json();
        
        if (data.status === 'SOVEREIGN' || data.status === 'Awakened') {
            dom.hud.node.innerText = data.hub_id || "SOVEREIGN_NODE";
            dom.hud.purity.innerText = (data.purity || 1.0).toFixed(2);
            dom.hud.purityGauge.style.width = `${(data.purity || 1.0) * 100}%`;
            
            if (data.vitality !== undefined) {
                dom.hud.vitality.innerText = data.vitality.toFixed(2);
                dom.hud.vitalityGauge.style.width = `${data.vitality * 100}%`;
            }
            
            if (data.session_cost_usd !== undefined) dom.hud.cost.innerText = `$${data.session_cost_usd.toFixed(2)}`;
            dom.hud.lamp.classList.add('online');
        }
    } catch (err) {
        dom.hud.lamp.classList.remove('online');
    }
}

// --- WebSocket Core ---
let wsReconnectAttempts = 0;
const MAX_RECONNECT_DELAY = 30000;

function initWebSocket() {
    const wsUrl = CLOUD_URL.replace('https://', 'wss://') + '/ws';
    console.log("Sovereign Nexus: Unified WebSocket connecting to", wsUrl);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log("Sovereign Nexus: WebSocket OPEN");
        wsReconnectAttempts = 0; // Reset on successful connection
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleSovereignEvent(data);
        } catch (e) { console.error("Event parse error", e); }
    };

    socket.onerror = (err) => {
        console.error("Sovereign Nexus: WebSocket error", err);
    };

    socket.onclose = (event) => {
        console.warn(`Sovereign Nexus: WebSocket closed (code=${event.code}). Reconnecting...`);
        wsReconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), MAX_RECONNECT_DELAY);
        setTimeout(initWebSocket, delay);
    };
}

function handleSovereignEvent(data) {
    switch (data.type) {
        case "hub_heartbeat":
            // Keep-alive acknowledged
            console.debug("Hub Heartbeat: STABLE");
            break;
        case "buddy_token":
            clearThinking();
            handleBuddyToken(data.token);
            break;
        case "thinking_pulse":
            showThinking(data.thought);
            break;
        case "buddy_chat":
            clearThinking();
            finalizeBuddyMessage(data);
            stopProcessing();
            break;
        case "mission_telemetry":
            updateMissionHUD(data);
            if (data.level === 'CHOICE') {
                renderPathSelection(data.metadata.options.map(opt => ({
                    title: opt,
                    summary: data.metadata.rationale,
                    id: opt.toLowerCase().replace(/\s+/g, '_')
                })));
            }
            break;
        case "pose_update":
            // Metrics updates
            if (dom.hud.vitality) dom.hud.vitality.innerText = (data.vitality_index || 1.0).toFixed(2);
            if (dom.hud.emergence) dom.hud.emergence.innerText = (data.drift || 0.0).toFixed(4);
            break;
        case "calibration_pulse":
            triggerCalibrationPulse(data.pulse);
            break;
        case "stage_update":
            const s = data.payload ? data.payload.stage : data.stage;
            if (s) updateSovereignStage(s);
            break;
        case "handover_ready":
            initiateCinematicHandover(data.payload);
            break;
        case "north_star_update":
            handleNorthStarUpdate(data.payload);
            break;
        case "mission_start":
            if (dom.promptbar.missionId) {
                dom.promptbar.missionId.innerText = `MISSION: ${data.mission_id}`;
                dom.promptbar.missionId.classList.remove('hidden');
            }
            break;
        case "mission_complete":
            if (dom.promptbar.missionId) {
                dom.promptbar.missionId.classList.add('hidden');
            }
            break;
        case "hub_sync":
            const sync = data.payload;
            if (sync.status === 'SOVEREIGN') {
                if (dom.hud.node) dom.hud.node.innerText = sync.hub_id || "SOVEREIGN_NODE";
                if (dom.hud.purity) dom.hud.purity.innerText = (sync.purity || 1.0).toFixed(2);
                if (dom.hud.purityGauge) dom.hud.purityGauge.style.width = `${(sync.purity || 1.0) * 100}%`;
                if (dom.hud.vitality) dom.hud.vitality.innerText = (sync.vitality || 1.0).toFixed(2);
                if (sync.session_cost_usd !== undefined && dom.hud.cost) {
                    dom.hud.cost.innerText = `$${sync.session_cost_usd.toFixed(4)}`;
                }
                dom.hud.lamp.classList.add('online');
                if (sync.shards) renderShardTray(sync.shards);
                if (sync.north_star) handleNorthStarUpdate(sync.north_star);
            }
            break;
    }
}

function handleNorthStarUpdate(payload) {
    if (!payload || !dom.northStar.panel) return;
    
    console.log("North Star: Synchronizing Trajectory...");
    
    // Update Macro & Focus (value for select dropdowns)
    if (document.activeElement !== dom.northStar.macro) {
        dom.northStar.macro.value = payload.macro || payload.macro_goal;
    }
    if (document.activeElement !== dom.northStar.focus) {
        dom.northStar.focus.value = payload.focus || payload.current_focus;
    }
    
    // Update Roadmap
    dom.northStar.roadmap.innerHTML = '';
    (payload.roadmap || payload.micro_goals || []).forEach(goal => {
        const li = document.createElement('li');
        li.innerText = goal;
        dom.northStar.roadmap.appendChild(li);
    });
    
    // Update Milestones
    dom.northStar.milestones.innerHTML = '';
    (payload.milestones || payload.completed_milestones || []).forEach(ms => {
        const li = document.createElement('li');
        li.innerText = ms;
        dom.northStar.milestones.appendChild(li);
    });
    
    // Pulse Sync Status
    dom.northStar.status.innerText = "STABLE";
    dom.northStar.status.classList.remove('syncing');
}

function sendNorthStarManualUpdate() {
    const payload = {
        macro: dom.northStar.macro.value,
        focus: dom.northStar.focus.value
    };
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        dom.northStar.status.innerText = "SYNCING...";
        dom.northStar.status.classList.add('syncing');
        socket.send(JSON.stringify({
            type: "north_star_intent",
            macro: payload.macro,
            focus: payload.focus
        }));
    }
}

function updateSovereignStage(stage) {
    if (dom.hud.stage) {
        dom.hud.stage.innerText = stage.toUpperCase();
        document.body.className = `sovereign-v4 atmosphere-${stage.toLowerCase()}`;
    }
}

async function initiateCinematicHandover(payload) {
    dom.handover.track.classList.remove('hidden');
    let progress = 0;
    const interval = setInterval(() => {
        progress += 2;
        dom.handover.progress.style.width = `${progress}%`;
        if (progress >= 100) {
            clearInterval(interval);
            dom.handover.overlay.classList.remove('hidden');
            setTimeout(() => {
                window.location.href = payload.cloud_url || config.apiHost;
            }, 1000);
        }
    }, 50);
}

function triggerCalibrationPulse(pulse) {
    if (dom.hud.delta) {
        dom.hud.delta.innerText = pulse.delta.toFixed(4);
    }
    if (dom.hud.calibrationPulse) {
        dom.hud.calibrationPulse.classList.remove('active');
        void dom.hud.calibrationPulse.offsetWidth; // Trigger reflow
        dom.hud.calibrationPulse.classList.add('active');
    }
}

function updateMissionHUD(data) {
    if (!dom.mission.info || !dom.mission.goal || !dom.mission.log) return;
    dom.mission.info.classList.remove('hidden');
    dom.mission.goal.innerText = `GOAL: ${data.goal}`;
    
    const entry = data.entry;
    const log = document.createElement('div');
    log.className = `log-entry ${entry.level.toLowerCase()}`;
    
    const time = new Date(entry.timestamp * 1000).toLocaleTimeString();
    log.innerHTML = `<span class="log-time" style="opacity: 0.4">[${time}]</span> ${entry.message}`;
    
    dom.mission.log.appendChild(log);
    dom.mission.log.scrollTop = dom.mission.log.scrollHeight;
    
    if (entry.level === 'END') {
        setTimeout(() => dom.mission.info.classList.add('hidden'), 5000);
    }
}

function handleBuddyToken(token) {
    if (!currentStreamingMessage) {
        currentStreamingMessage = createMessageElement('buddy');
        dom.stream.appendChild(currentStreamingMessage);
        streamingText = '';
    }
    streamingText += token;

    // Real-time raw text display during streaming (no markdown yet — avoid partial parse flicker)
    const content = currentStreamingMessage.querySelector('.content');
    if (content) content.textContent = streamingText;

    scrollIfNotLocked();
}

async function processTypingQueue() {
    // Legacy: kept for compatibility but not used with true streaming.
    // Tokens now go directly to streamingText in handleBuddyToken.
    isTyping = false;
}


function finalizeBuddyMessage(data) {
    if (currentStreamingMessage) {
        // Render the full accumulated text as Markdown
        const content = currentStreamingMessage.querySelector('.content');
        if (content) {
            content.innerHTML = renderMarkdown(data.content || streamingText);
        }

        if (data.dynamics) {
            updateAtmosphere(data.dynamics);
            const meta = currentStreamingMessage.querySelector('.meta');
            if (meta) meta.querySelector('.meta-role').textContent =
                `Buddy · ${new Date().toLocaleTimeString()}`;
        }

        // Inject copy button
        _attachCopyButton(currentStreamingMessage, data.content || streamingText);

        if (data.manifestation) {
            if (data.manifestation.type === 'path_selection') {
                renderPathSelection(data.manifestation.content);
            } else {
                renderSandbox(data.manifestation);
            }
        }

        streamingText = '';
        currentStreamingMessage = null;
    } else {
        appendMessage('buddy', data.content, data.dynamics);
    }
    scrollIfNotLocked();
}

function createMessageElement(sender, text = '') {
    const msg = document.createElement('div');
    msg.className = `message ${sender}-entry`;
    const isUser = sender === 'user';
    msg.innerHTML = `
        <div class="meta">
            <span class="meta-role">${isUser ? 'Architect' : 'Buddy'} · ${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="content">${isUser ? text : (text ? renderMarkdown(text) : '')}</div>
    `;
    return msg;
}

function _attachCopyButton(msgEl, rawText) {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.title = 'Copy';
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>`;
    btn.onclick = () => {
        navigator.clipboard.writeText(rawText).then(() => {
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
            setTimeout(() => {
                btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>`;
            }, 2000);
        });
    };
    msgEl.appendChild(btn);
}
function renderPathSelection(options) {
    dom.paths.container.innerHTML = '';
    dom.paths.overlay.classList.remove('hidden');
    
    options.forEach(opt => {
        const card = document.createElement('div');
        card.className = 'choice-card';
        card.innerHTML = `
            <div class="choice-title">${opt.title}</div>
            <div class="choice-summary">${opt.summary}</div>
        `;
        card.onclick = () => selectPath(opt);
        dom.paths.container.appendChild(card);
    });
}

function selectPath(option) {
    dom.paths.overlay.classList.add('hidden');
    appendMessage('user', `MISSION_MANIFEST: Selecting Path -> ${option.title}`);
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ 
            type: "user_chat", 
            message: `I select the path: ${option.id}. Proceed with ${option.title}.` 
        }));
    }
}

function updateAtmosphere(dynamics) {
    const intent = (dynamics.intent || 'LISTEN').toLowerCase();
    document.body.className = `sovereign-v4 atmosphere-${intent}`;
    if (dom.hud.human) dom.hud.human.innerText = (dynamics.resonance || 1.0).toFixed(2);
}

function renderSandbox(manifestation) {
    if (!manifestation || !manifestation.content || !dom.sandbox.panel) return;
    dom.sandbox.panel.classList.remove('hidden');
    dom.sandbox.content.innerHTML = manifestation.content;
}

// --- Event Listeners ---
function setupEventListeners() {
    if (dom.input) {
        dom.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        // Auto-grow textarea
        dom.input.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        // Visual feedback for focus
        dom.input.addEventListener('focus', () => {
            if (dom.promptbar.container) dom.promptbar.container.classList.add('focused');
        });
        dom.input.addEventListener('blur', () => {
            if (dom.promptbar.container) dom.promptbar.container.classList.remove('focused');
        });
    }

    if (dom.sendBtn) {
        dom.sendBtn.addEventListener('click', () => {
            handleSendMessage();
        });
    }

    if (dom.sandbox.close) {
        dom.sandbox.close.onclick = () => {
            if (dom.sandbox.panel) dom.sandbox.panel.classList.add('hidden');
        };
    }

    // --- North Star Listeners ---
    if (dom.northStar.macro) {
        dom.northStar.macro.onchange = () => sendNorthStarManualUpdate();
    }
    if (dom.northStar.focus) {
        dom.northStar.focus.onchange = () => sendNorthStarManualUpdate();
    }
    if (dom.northStar.stashBtn) {
        dom.northStar.stashBtn.onclick = () => {
            appendMessage('user', "STASH_AND_PIVOT: Archiving current roadmap and clearing the deck for a new vector.");
            // Reset local UI for immediate feedback
            dom.northStar.macro.value = "Initial Mission";
            dom.northStar.focus.value = "System Setup";
            dom.northStar.roadmap.innerHTML = '';
            sendNorthStarManualUpdate();
        };
    }
}
async function handleSendMessage() {
    const text = dom.input.value.trim();
    if (!text || isProcessing) return;

    appendMessage('user', text);
    dom.input.value = '';
    dom.input.style.height = 'auto';
    startProcessing();
    userScrolledUp = false;  // Resume auto-scroll on new send

    const selectedModel = dom.modelPicker ? dom.modelPicker.value : 'gemini-2.5-pro-exp-03-25';

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "user_chat", message: text, model: selectedModel }));
    } else {
        console.warn("WebSocket Unlinked. Falling back to REST Cognitive Pipeline...");
        try {
            const response = await fetch(`${config.apiHost}/chat`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Sovereign-Key': config.sovereignKey 
                },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            if (data.status === 'success') {
                handleSovereignEvent(data);
            } else {
                appendMessage('buddy', "Cognitive Fault: " + (data.response || "Unknown Error"));
                stopProcessing();
            }
        } catch (err) {
            console.error("REST Fallback Error:", err);
            appendMessage('buddy', "Hub Communication Severed. Re-awakening logic...");
            stopProcessing();
            initWebSocket();
        }
    }
}

function startProcessing() {
    isProcessing = true;
    if (dom.sendBtn) dom.sendBtn.classList.add('active');
}

function stopProcessing() {
    isProcessing = false;
    if (dom.sendBtn) dom.sendBtn.classList.remove('active');
}

function showThinking(thought) {
    if (!currentThinkingBubble) {
        currentThinkingBubble = document.createElement('div');
        currentThinkingBubble.className = 'thinking-pulse';
        dom.stream.appendChild(currentThinkingBubble);
    }
    currentThinkingBubble.innerHTML = `
        <span class="thinking-dots"><span></span><span></span><span></span></span>
        <span class="thinking-label">${thought || 'Reasoning...'}</span>
    `;
    scrollIfNotLocked();
}

function scrollIfNotLocked() {
    if (!userScrolledUp) {
        dom.stream.scrollTop = dom.stream.scrollHeight;
    }
}

function clearThinking() {
    if (currentThinkingBubble) {
        currentThinkingBubble.remove();
        currentThinkingBubble = null;
    }
}

function appendMessage(role, text, dynamics = null) {
    const msg = createMessageElement(role, text);

    if (role === 'buddy') {
        _attachCopyButton(msg, text);
    }

    dom.stream.appendChild(msg);
    scrollIfNotLocked();
}

// --- Scroll Lock: pause auto-scroll when user scrolls up ---
function initScrollLock() {
    dom.stream.addEventListener('scroll', () => {
        const atBottom = dom.stream.scrollTop + dom.stream.clientHeight >= dom.stream.scrollHeight - 40;
        userScrolledUp = !atBottom;
    });
}

// --- Initialization ---
initWebSocket();
startTelemetryPulse();
setupEventListeners();
initScrollLock();
