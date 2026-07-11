let map, userMarker, telemetryChart;
let ws;
let nodesData = [];
let selectedNodeId = null;
let nodeMarkers = {};
let alertIds = new Set();
let isUnderAttack = false;
let currentLoss = 0;
let currentCitizens = 0;
let lossInterval = null;
let audioCtx = null;
let chartData = { labels: [], datasets: [
    { label: 'Voltage (V)', borderColor: '#00e5ff', data: [], tension: 0.6, pointRadius: 0, borderWidth: 2 },
    { label: 'Current (A)', borderColor: '#00e676', data: [], tension: 0.6, pointRadius: 0, borderWidth: 2 },
    { label: 'Packets/s (k)', borderColor: '#ffab00', data: [], tension: 0.6, pointRadius: 0, borderWidth: 2 }
]};
let mapOverlays = {}; // Store blast radius & shields
// DOM Elements
const el = {
    clock: document.getElementById('clock'),
    connDot: document.getElementById('connection-dot'),
    connText: document.getElementById('connection-text'),
    statNodes: document.getElementById('stat-total-nodes'),
    statHealthy: document.getElementById('stat-healthy-nodes'),
    statThreats: document.getElementById('stat-threats'),
    statLoss: document.getElementById('stat-loss'),
    statCitizens: document.getElementById('stat-citizens'),
    statLedger: document.getElementById('stat-ledger'),
    nodeGrid: document.getElementById('node-grid'),
    chartName: document.getElementById('chart-node-name'),
    chaosName: document.getElementById('chaos-target-name'),
    alertFeed: document.getElementById('alert-feed'),
    chatContainer: document.getElementById('chat-container'),
    chatInput: document.getElementById('chat-input'),
    btnSendChat: document.getElementById('btn-send-chat'),
    btnViewLedger: document.getElementById('btn-view-ledger'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    modal: document.getElementById('ledger-modal'),
    ledgerBody: document.getElementById('ledger-tbody'),
    ledgerBadge: document.getElementById('ledger-integrity-badge'),
    btnResolve: document.getElementById('btn-resolve'),
    btnSos: document.getElementById('btn-sos-quarantine'),
    toastContainer: document.getElementById('toast-container'),
    hudStability: document.getElementById('hud-stability'),
    hudLedger: document.getElementById('hud-ledger'),
    hudDefenses: document.getElementById('hud-defenses')
};
// Utils
const formatTime = (d) => d.toTimeString().split(' ')[0];
const truncateHash = (h) => h ? `${h.substring(0,8)}...${h.substring(h.length-8)}` : '-';
const getNodeIcon = (type) => ({'power_grid':'⚡', 'water_treatment':'🚰', 'traffic_control':'🚦', 'agri_iot':'🌾'})[type] || '📍';
const getStatusColor = (status) => ({'normal':'var(--success)', 'warning':'var(--warning)', 'critical':'var(--danger)'})[status] || '#fff';
// Voice and Siren
function playSirenAndSpeak(msg) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    // Siren
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'square';
    osc.frequency.setValueAtTime(400, audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(800, audioCtx.currentTime + 0.5);
    osc.frequency.linearRampToValueAtTime(400, audioCtx.currentTime + 1.0);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    osc.start();
    osc.stop(audioCtx.currentTime + 1.5);
    
    // Speak
    if ('speechSynthesis' in window) {
        const u = new SpeechSynthesisUtterance(msg);
        u.volume = 1; u.rate = 1; u.pitch = 1;
        window.speechSynthesis.speak(u);
    }
}
// Financial Loss Loop
function startLossSimulation() {
    if(lossInterval) return;
    lossInterval = setInterval(() => {
        currentLoss += Math.floor(Math.random() * 5000) + 1000;
        currentCitizens += Math.floor(Math.random() * 50) + 10;
        el.statLoss.textContent = '₹' + currentLoss.toLocaleString('en-IN');
        el.statCitizens.textContent = currentCitizens.toLocaleString('en-IN');
    }, 1000);
}
function stopLossSimulation() {
    if(lossInterval) clearInterval(lossInterval);
    lossInterval = null;
}
// Clock
setInterval(() => el.clock.textContent = formatTime(new Date()), 1000);
// Init
document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    initChart();
    setupEventListeners();
    await fetchInitialData();
    connectWebSocket();
    startGPS();
});
// Map
function initMap() {
    map = L.map('map').setView([22.5, 79], 5); // Center India
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        className: 'map-tiles'
    }).addTo(map);
    // Dark mode CSS trick for OSM: filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); in style.css or JS
    document.querySelector('.leaflet-layer').style.filter = 'invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%)';
}
function updateMapMarkers() {
    nodesData.forEach(n => {
        let color = getStatusColor(n.status);
        let pulseClass = n.status === 'critical' ? 'map-radar-pulse' : '';
        let html = `<div class="${pulseClass}" style="background:${color}; width:15px; height:15px; border-radius:50%; border:2px solid #fff; box-shadow:0 0 10px ${color}"></div>`;
        
        if (!nodeMarkers[n.id]) {
            let icon = L.divIcon({className: 'custom-icon', html: html, iconSize: [15,15]});
            let marker = L.marker([n.lat, n.lng], {icon: icon}).addTo(map);
            marker.bindPopup(`<b>${getNodeIcon(n.type)} ${n.name}</b><br>Type: ${n.type}<br>Status: ${n.status}`);
            marker.on('click', () => selectNode(n.id));
            nodeMarkers[n.id] = marker;
            mapOverlays[n.id] = { blast: null, shield: null };
        } else {
            nodeMarkers[n.id].setIcon(L.divIcon({className: 'custom-icon', html: html, iconSize: [15,15]}));
            if(n.status === 'critical') nodeMarkers[n.id].setZIndexOffset(1000);
            else nodeMarkers[n.id].setZIndexOffset(0);
        }
        
        // Blast Radius overlay
        if (n.status === 'critical' && !mapOverlays[n.id].blast && !mapOverlays[n.id].isolated) {
            mapOverlays[n.id].blast = L.circle([n.lat, n.lng], {
                color: 'red', fillColor: '#f03', fillOpacity: 0.2, radius: 250000 // 250km radius
            }).addTo(map);
            showToast(`Cascading failure predicted from ${n.name}!`, 'error');
        } else if (n.status !== 'critical' && mapOverlays[n.id].blast) {
            map.removeLayer(mapOverlays[n.id].blast);
            mapOverlays[n.id].blast = null;
        }
    });
}
// Chart
function initChart() {
    const ctx = document.getElementById('telemetryChart').getContext('2d');
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";
    telemetryChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { display: false }, // Hide axes for oscilloscope look
                x: { display: false }
            },
            plugins: { legend: { position: 'top' } },
            animation: false,
            elements: { line: { borderCapStyle: 'round' } }
        }
    });
}
async function fetchTelemetryHistory(nodeId) {
    try {
        const res = await fetch('/api/telemetry');
        const hist = await res.json();
        const data = hist[nodeId] || [];
        
        chartData.labels = data.map((_, i) => i);
        chartData.datasets[0].data = data.map(d => d.voltage || 0);
        chartData.datasets[1].data = data.map(d => d.current || 0);
        chartData.datasets[2].data = data.map(d => (d.packets_per_sec || 0)/1000); // Scale to k
        telemetryChart.update();
    } catch(e) { console.error("History fetch error:", e); }
}
function updateChartLive(nodes) {
    if(!selectedNodeId) return;
    const n = nodes.find(x => x.id === selectedNodeId);
    if(n && n.metrics) {
        chartData.labels.push(chartData.labels.length);
        if(chartData.labels.length > 60) chartData.labels.shift();
        
        // Oscilloscope glitch effect
        if(n.status === 'critical') {
            chartData.datasets.forEach(ds => { ds.tension = 0; ds.borderColor = '#ff1744'; ds.borderWidth = 1; });
        } else {
            chartData.datasets[0].borderColor = '#00e5ff';
            chartData.datasets[1].borderColor = '#00e676';
            chartData.datasets[2].borderColor = '#ffab00';
            chartData.datasets.forEach(ds => { ds.tension = 0.6; ds.borderWidth = 2; });
        }
        
        // Smooth out the data slightly if normal
        let v = n.metrics.voltage || 0;
        let c = n.metrics.current || 0;
        let p = (n.metrics.packets_per_sec || 0)/1000;
        if(n.status !== 'critical') {
            // Fake sine smoothing for oscilloscope look
            let t = Date.now() / 1000;
            v += Math.sin(t*2) * 5;
            c += Math.cos(t*2) * 2;
            p += Math.sin(t*3);
        }
        
        chartData.datasets[0].data.push(v);
        chartData.datasets[1].data.push(c);
        chartData.datasets[2].data.push(p);
        
        if(chartData.datasets[0].data.length > 60) {
            chartData.datasets.forEach(ds => ds.data.shift());
        }
        telemetryChart.update();
    }
}
// Data fetching
async function fetchInitialData() {
    try {
        const res = await fetch('/api/nodes');
        nodesData = await res.json();
        renderNodeGrid();
        updateMapMarkers();
        if(nodesData.length > 0) selectNode(nodesData[0].id);
        
        const aRes = await fetch('/api/alerts');
        const alerts = await aRes.json();
        alerts.forEach(renderAlert);
        
        await updateStats();
    } catch(e) { console.error("Init fetch error:", e); }
}
async function updateStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        el.statNodes.textContent = stats.total_nodes;
        el.statHealthy.textContent = stats.healthy_nodes;
        el.statThreats.textContent = stats.critical_nodes + stats.warning_nodes;
        el.statLedger.textContent = stats.ledger_integrity_status ? 'Valid' : 'Compromised';
        el.statLedger.className = stats.ledger_integrity_status ? 'stat-value text-success' : 'stat-value text-danger';
    } catch(e) {}
}
// UI Rendering
function renderNodeGrid() {
    el.nodeGrid.innerHTML = '';
    nodesData.forEach(n => {
        const card = document.createElement('div');
        card.className = `node-card ${n.status} ${n.id === selectedNodeId ? 'selected' : ''}`;
        card.onclick = () => selectNode(n.id);
        card.innerHTML = `
            <div class="node-header">
                <span>${getNodeIcon(n.type)} ${n.name}</span>
                <span class="node-city">${n.city}</span>
            </div>
            <div class="node-metrics">
                <span>V: ${n.metrics.voltage ? n.metrics.voltage.toFixed(1) : '-'}</span>
                <span>I: ${n.metrics.current ? n.metrics.current.toFixed(1) : '-'}</span>
                <span>P/s: ${n.metrics.packets_per_sec ? Math.round(n.metrics.packets_per_sec) : '-'}</span>
                <span>Load: ${n.metrics.cpu_load ? n.metrics.cpu_load.toFixed(1)+'%' : '-'}</span>
            </div>
        `;
        el.nodeGrid.appendChild(card);
    });
}
function selectNode(id) {
    selectedNodeId = id;
    const n = nodesData.find(x => x.id === id);
    if(!n) return;
    
    el.chartName.textContent = n.name;
    el.chaosName.textContent = n.name;
    
    // Visual selection update
    document.querySelectorAll('.node-card').forEach(c => c.classList.remove('selected'));
    const cards = Array.from(el.nodeGrid.children);
    const idx = nodesData.findIndex(x => x.id === id);
    if(cards[idx]) cards[idx].classList.add('selected');
    
    fetchTelemetryHistory(id);
}
function renderAlert(a) {
    if(alertIds.has(a.id)) return;
    alertIds.add(a.id);
    
    const empty = el.alertFeed.querySelector('.empty-state');
    if(empty) empty.remove();
    
    
    const div = document.createElement('div');
    div.className = `alert-item ${a.severity}`;
    div.innerHTML = `
        <div>
            <div class="alert-time">${formatTime(new Date(a.timestamp))}</div>
            <div class="alert-title">${a.threat_type}</div>
            <div class="alert-node">Target: ${a.node_name}</div>
        </div>
        <button class="btn-sop" onclick="askCopilot('Give me SOP for ${a.threat_type} on ${a.node_name}')">Get SOP</button>
    `;
    el.alertFeed.prepend(div);
    
    if (a.severity === 'critical') {
        playSirenAndSpeak(`Warning! ${a.threat_type} detected on ${a.node_name}`);
    }
}
// WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/live`);
    
    ws.onopen = () => {
        el.connDot.className = 'status-dot connected';
        el.connText.textContent = 'Connected (Live)';
    };
    
    ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        if(data.type === 'update') {
            nodesData = data.nodes;
            renderNodeGrid();
            updateMapMarkers();
            updateChartLive(data.nodes);
            
            // Check critical state
            const hasCritical = data.nodes.some(n => n.status === 'critical');
            if (hasCritical && !isUnderAttack) {
                isUnderAttack = true;
                document.body.classList.add('glitch-mode');
                startLossSimulation();
                el.hudStability.textContent = '40.2%';
                el.hudStability.className = 'hud-value hud-red';
            } else if (!hasCritical && isUnderAttack) {
                isUnderAttack = false;
                document.body.classList.remove('glitch-mode');
                stopLossSimulation();
                el.hudStability.textContent = '99.9%';
                el.hudStability.className = 'hud-value hud-green';
            }
            
            // HUD Update
            if(data.stats.ledger_integrity_status) {
                el.hudLedger.textContent = 'SECURE (SHA-256)';
                el.hudLedger.className = 'hud-value hud-green';
            } else {
                el.hudLedger.textContent = 'COMPROMISED';
                el.hudLedger.className = 'hud-value hud-red';
            }
            
            // Stats
            el.statNodes.textContent = data.stats.total_nodes;
            el.statHealthy.textContent = data.stats.healthy_nodes;
            el.statThreats.textContent = data.stats.critical_nodes + data.stats.warning_nodes;
            el.statLedger.textContent = data.stats.ledger_integrity_status ? 'Valid' : 'Compromised';
            el.statLedger.className = data.stats.ledger_integrity_status ? 'stat-value text-success' : 'stat-value text-danger';
            
            // Alerts
            if(data.alerts) {
                data.alerts.forEach(renderAlert);
            }
        }
    };
    
    ws.onclose = () => {
        el.connDot.className = 'status-dot';
        el.connText.textContent = 'Disconnected';
        setTimeout(connectWebSocket, 3000);
    };
}
// Interactions
function setupEventListeners() {
    // Chaos toggles
    document.querySelectorAll('.chaos-toggle').forEach(toggle => {
        toggle.onchange = async (e) => {
            if(!selectedNodeId) {
                e.target.checked = false;
                return showToast('No node selected', 'error');
            }
            if (e.target.checked) {
                // Uncheck others
                document.querySelectorAll('.chaos-toggle').forEach(t => { if(t !== e.target) t.checked = false; });
                const attack = e.target.getAttribute('data-attack');
                if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); // Init audio on user gesture
                try {
                    const res = await fetch('/api/inject-chaos', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify({node_id: selectedNodeId, attack_type: attack})
                    });
                    if(res.ok) showToast(`Injected ${attack} on target`, 'warning');
                } catch(e) { showToast('Injection failed', 'error'); }
            }
        };
    });
    
    // SOS Kill-Switch
    el.btnSos.onclick = () => {
        if(!selectedNodeId) return showToast('No node selected for isolation', 'error');
        const n = nodesData.find(x => x.id === selectedNodeId);
        if(n) {
            // Remove blast radius if any
            if(mapOverlays[n.id].blast) {
                map.removeLayer(mapOverlays[n.id].blast);
                mapOverlays[n.id].blast = null;
            }
            // Add cyber shield
            if(!mapOverlays[n.id].shield) {
                mapOverlays[n.id].shield = L.circle([n.lat, n.lng], {
                    color: '#00e5ff', fillColor: '#00e5ff', fillOpacity: 0.4, radius: 150000, dashArray: '5, 10'
                }).addTo(map);
                mapOverlays[n.id].isolated = true;
            }
            showToast(`${n.name} NETWORK ISOLATED (Cyber Shield Active)`, 'info');
            el.hudDefenses.textContent = `NODE ${selectedNodeId} ISOLATED`;
            el.hudDefenses.className = 'hud-value hud-green';
            playSirenAndSpeak("Cyber shield activated. Network traffic blocked.");
        }
    };
    
    // Resolve button
    el.btnResolve.onclick = async () => {
        if(!selectedNodeId) return;
        document.querySelectorAll('.chaos-toggle').forEach(t => t.checked = false);
        
        // Remove shield
        if(mapOverlays[selectedNodeId] && mapOverlays[selectedNodeId].shield) {
            map.removeLayer(mapOverlays[selectedNodeId].shield);
            mapOverlays[selectedNodeId].shield = null;
            mapOverlays[selectedNodeId].isolated = false;
            el.hudDefenses.textContent = 'STANDBY';
            el.hudDefenses.className = 'hud-value';
        }
        try {
            const res = await fetch('/api/resolve', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({node_id: selectedNodeId})
            });
            if(res.ok) showToast('Incident resolved', 'success');
        } catch(e) {}
    };
    
    // Chat
    const handleChat = async () => {
        const text = el.chatInput.value.trim();
        if(!text) return;
        
        // User message
        appendChatMsg(text, 'user-message', '👤');
        el.chatInput.value = '';
        
        try {
            const res = await fetch('/api/copilot', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({query: text})
            });
            const data = await res.json();
            
            if(data && data.length > 0) {
                const sop = data[0];
                let content = `<b>SOP: ${sop.title}</b>\n\n`;
                sop.steps.forEach((step, i) => content += `${i+1}. ${step}\n`);
                appendChatMsg(content, 'ai-message', '🤖');
            } else {
                appendChatMsg("I couldn't find a specific SOP for that. Please try rephrasing.", 'ai-message', '🤖');
            }
        } catch(e) {
            appendChatMsg("Error connecting to local AI engine.", 'ai-message', '🤖');
        }
    };
    
    el.btnSendChat.onclick = handleChat;
    el.chatInput.onkeypress = (e) => { if(e.key === 'Enter') handleChat(); };
    
    // Ledger Modal
    el.btnViewLedger.onclick = async () => {
        el.modal.classList.add('active');
        try {
            const res = await fetch('/api/ledger');
            const data = await res.json();
            
            el.ledgerBadge.textContent = data.integrity.is_valid ? 'Integrity: Valid ✓' : 'Integrity: COMPROMISED ✗';
            el.ledgerBadge.className = data.integrity.is_valid ? 'integrity-badge integrity-valid' : 'integrity-badge integrity-invalid';
            
            el.ledgerBody.innerHTML = '';
            data.entries.reverse().forEach(e => {
                let badge = e.severity === 'critical' || e.event_type.includes('chaos') 
                    ? '<span class="receipt-blocked">Hack Attempt: BLOCKED BY KAVACH</span>' 
                    : '<span class="receipt-valid">SYSTEM LOG VERIFIED</span>';
                el.ledgerBody.innerHTML += `
                    <div class="receipt-item">
                        <strong>BLOCK ID:</strong> #${e.index}<br>
                        <strong>TIME:</strong> ${formatTime(new Date(e.timestamp))}<br>
                        <strong>EVENT:</strong> ${e.event_type.toUpperCase()}<br>
                        <strong>TARGET:</strong> ${e.node_id || 'SYSTEM'}<br>
                        <strong>HASH:</strong> ${e.current_hash}<br>
                        ${badge}
                    </div>
                `;
            });
        } catch(e) { console.error(e); }
    };
    
    el.btnCloseModal.onclick = () => el.modal.classList.remove('active');
}
window.askCopilot = (query) => {
    el.chatInput.value = query;
    el.btnSendChat.click();
};
function appendChatMsg(text, type, avatar) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-bubble">${text}</div>`;
    el.chatContainer.appendChild(div);
    el.chatContainer.scrollTop = el.chatContainer.scrollHeight;
}
function showToast(msg, type='info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    el.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
// GPS Tracking
function startGPS() {
    if ("geolocation" in navigator) {
        navigator.geolocation.watchPosition(
            (pos) => {
                const {latitude, longitude, accuracy} = pos.coords;
                if(!userMarker) {
                    const icon = L.divIcon({className: 'custom-icon', html: '<div style="background:#00e5ff; width:15px; height:15px; border-radius:50%; border:2px solid #fff; box-shadow:0 0 10px #00e5ff;"></div>', iconSize: [15,15]});
                    userMarker = L.marker([latitude, longitude], {icon}).addTo(map);
                    userMarker.bindPopup("<b>Your Live Location</b>");
                } else {
                    userMarker.setLatLng([latitude, longitude]);
                }
            },
            (err) => console.log("GPS Denied/Error", err),
            { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }
        );
    }
}
