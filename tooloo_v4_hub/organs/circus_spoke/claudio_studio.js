/* 6W_STAMP 
   WHO: TooLoo V4 (Sovereign Architect)
   WHAT: CLAUDIO_STUDIO.JS | Version: 1.0.0
   WHERE: tooloo_v4_hub/organs/circus_spoke/claudio_studio.js
   WHY: Rule 7 (UX Supremacy) - Real-Time Engram Visualization
   HOW: Canvas + SVG Manipulation + Engram Interpolation
   TIER: T3:architectural-purity
   PURITY: 1.00
*/

class ClaudioStudio {
    constructor() {
        this.peers = new Map();
        this.localIntent = { f0: 440, velocity: 0.8, timbre: new Array(16).fill(0.5) };
        this.isSimulating = true;
        this.socket = null;
        
        this.initDOM();
        this.initNetwork();
        this.startPulse();
    }

    initNetwork() {
        this.socket = new WebSocket('ws://localhost:8844');
        this.socket.onopen = () => {
            console.log('⚡ CCS TETHERED TO SOVEREIGN PULSE');
            this.isSimulating = false; // Real data takes over
            document.getElementById('purity-status').style.color = '#00ff00';
            document.getElementById('purity-status').innerText = 'PURITY: 1.00 (LIVE)';
        };
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'engram_update') {
                this.localIntent = {
                    f0: data.f0,
                    velocity: 1.0, // Force vis for engram pop
                    timbre: data.timbre
                };
            }
        };
        this.socket.onclose = () => {
            console.warn('⚠️ CCS TETHER DISSOLVED. REVERTING TO SIM.');
            this.isSimulating = true;
        };
    }


    initDOM() {
        this.bloomPath1 = document.getElementById('engram-path-1');
        this.bloomPath2 = document.getElementById('engram-path-2');
        this.intentLevelText = document.getElementById('intent-level');
        this.peerList = document.getElementById('peer-list');
        
        // Setup initial simulation peers
        this.addPeer('Maria Rossi', 'VOCAL_STACK | LATENCY: 12ms');
        this.addPeer('David Kim', 'MASTERING_PULSE | LATENCY: 24ms');
    }

    addPeer(name, status) {
        const id = Math.random().toString(36).substr(2, 9);
        const item = document.createElement('div');
        item.className = 'peer-item';
        item.innerHTML = `
            <div class="peer-avatar">${name[0]}</div>
            <div class="peer-info">
                <div class="peer-name">${name}</div>
                <div class="peer-status">${status}</div>
            </div>
            <canvas id="peer-viz-${id}" class="peer-viz-mini" width="60" height="30"></canvas>
        `;
        this.peerList.appendChild(item);
        
        const canvas = document.getElementById(`peer-viz-${id}`);
        this.peers.set(id, { name, status, canvas, ctx: canvas.getContext('2d'), phase: Math.random() * Math.PI * 2 });
    }

    updateSpectralBloom(intent) {
        // High-fidelity SVG Path deformation based on 16D timbre
        const points = 64;
        const radius = 40;
        const center = 50;
        let d1 = "";
        let d2 = "";

        for (let i = 0; i <= points; i++) {
            const angle = (i / points) * Math.PI * 2;
            const timbreIndex = Math.floor((i / points) * 16) % 16;
            const offset = (intent.timbre[timbreIndex] * 8) * Math.sin(angle * 8 + Date.now() * 0.005);
            
            const r1 = radius + offset;
            const r2 = (radius - 5) + (offset * 0.5);
            
            const x1 = center + r1 * Math.cos(angle);
            const y1 = center + r1 * Math.sin(angle);
            const x2 = center + r2 * Math.cos(angle);
            const y2 = center + r2 * Math.sin(angle);

            if (i === 0) {
                d1 += `M ${x1} ${y1}`;
                d2 += `M ${x2} ${y2}`;
            } else {
                d1 += ` L ${x1} ${y1}`;
                d2 += ` L ${x2} ${y2}`;
            }
        }

        this.bloomPath1.setAttribute('d', d1 + " Z");
        this.bloomPath2.setAttribute('d', d2 + " Z");
        
        this.intentLevelText.innerText = `${Math.round(intent.velocity * 100)}%`;
    }

    drawPeerViz(peer) {
        const { ctx, canvas } = peer;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.beginPath();
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 1;
        
        peer.phase += 0.05;
        for(let x = 0; x < canvas.width; x++) {
            const y = (canvas.height / 2) + Math.sin(x * 0.2 + peer.phase) * 5;
            if(x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    startPulse() {
        const loop = () => {
            if (this.isSimulating) {
                // Stochastic Timbre Drift for "Spectral Bloom" verification
                this.localIntent.timbre = this.localIntent.timbre.map(t => 
                    Math.max(0.1, Math.min(0.9, t + (Math.random() - 0.5) * 0.05))
                );
                this.localIntent.velocity = 0.7 + Math.sin(Date.now() * 0.002) * 0.2;
            }

            this.updateSpectralBloom(this.localIntent);
            
            this.peers.forEach(peer => this.drawPeerViz(peer));

            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }
}

// Actual Emergence of the Sovereign Studio
window.addEventListener('DOMContentLoaded', () => {
    window.studio = new ClaudioStudio();
});
