// 6W_STAMP: SOVEREIGN_ARCHITECT
// SANDBOX_LOGIC | Version: 1.0.0
// TETHERED TO: tooloo_v4_hub.organs.sovereign_chat

const editor = document.getElementById('code-editor');
const viewport = document.getElementById('manifestation-viewport');
const manifestList = document.getElementById('manifest-list');

/**
 * Hub Tethering Protocol
 * Connects to the Sovereign Chat organ via WebSocket or BroadcastChannel
 */
function initializeHubTether() {
    console.log("SANDBOX: Initializing Hub Tether...");
    
    // In a real scenario, this connects to BUDDY_SOCKET
    const hubChannel = new BroadcastChannel('tooloo_v4_manifestation');
    
    hubChannel.onmessage = (event) => {
        const { type, data } = event.data;
        
        switch (type) {
            case 'SANDBOX_PUSH':
                updateSandbox(data.filename, data.content);
                break;
            case 'PULSE_STATS':
                updateStats(data);
                break;
            case 'CONVERGENCE_REPORT_PUSH':
                updateSandbox('grand_convergence_report.html', data.html);
                // Send the actual results to the iframe for chart rendering
                setTimeout(() => {
                    viewport.contentWindow.postMessage({ type: 'UPDATE_AUDIT', results: data.results }, '*');
                }, 1000);
                break;
        }
    };
}

/**
 * Updates the Sandbox with new manifestation content
 */
function updateSandbox(filename, content) {
    console.log(`SANDBOX: Manifesting ${filename}...`);
    
    // 1. Update Explorer
    addOrUpdateManifestItem(filename);
    
    // 2. Inject to Editor
    editor.innerText = content;
    
    // 3. Render to Viewport
    const blob = new Blob([content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    viewport.src = url;
}

function addOrUpdateManifestItem(filename) {
    let items = document.querySelectorAll('.manifest-item');
    let exists = false;
    
    items.forEach(item => {
        if (item.innerText === filename) {
            exists = true;
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    if (!exists) {
        const item = document.createElement('div');
        item.className = 'manifest-item active';
        item.innerText = filename;
        manifestList.appendChild(item);
    }
}

function updateStats(data) {
    const statsOverlay = document.querySelector('.stats-overlay');
    statsOverlay.innerHTML = `FPS: ${data.fps || 60} | ROI: +${data.roi || 0.00} | PURITY: ${data.purity || "1.00"}`;
}

// Initial Warmup
initializeHubTether();

// Mock Initial Data (Rule 7)
const initialCode = `
<style>
    body { background: #000; color: #8a2be2; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif; overflow: hidden; margin: 0; }
    .pulse { width: 100px; height: 100px; background: rgba(138, 43, 226, 0.2); border-radius: 50%; border: 1px solid #8a2be2; animation: glow 2s infinite; }
    @keyframes glow { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.5); opacity: 1; } }
</style>
<div class="pulse"></div>
`;
updateSandbox('spectral_warmup.html', initialCode);
