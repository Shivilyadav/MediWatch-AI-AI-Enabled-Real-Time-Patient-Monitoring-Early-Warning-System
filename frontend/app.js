/**
 * Aavishkar Patient Monitor - Frontend Controller
 * Handles 60fps canvas oscilloscope rendering, WebSocket telemetry streaming,
 * multi-bed management, and interactive clinical event simulation.
 */

let patientsData = [];
let currentBedId = "BED-101";
let isMultiBedView = false;
let socket = null;
let alarmAudioMuted = false;

// Waveform Canvas Buffer Queues
const waveBuffers = {
    "BED-101": { ecg: [], ppg: [] },
    "BED-102": { ecg: [], ppg: [] },
    "BED-103": { ecg: [], ppg: [] },
    "BED-104": { ecg: [], ppg: [] }
};

// Canvas Sweep Pointers
let sweepX = 0;
const SWEEP_SPEED = 2.5;

// Audio Synth Alarm Context
let audioCtx = null;

document.addEventListener("DOMContentLoaded", () => {
    initClock();
    initEventListeners();
    fetchPatientsList();
    connectWebSocket();
    startCanvasRenderLoop();
});

// Master Clock
function initClock() {
    const timeEl = document.getElementById("system-time");
    setInterval(() => {
        const now = new Date();
        timeEl.textContent = now.toTimeString().split(' ')[0];
    }, 1000);
}

// Initial REST Patient Fetch
async function fetchPatientsList() {
    try {
        const res = await fetch("/api/patients");
        if (res.ok) {
            patientsData = await res.json();
            renderPatientTabs();
            updateSingleBedUI();
            if (isMultiBedView) renderMultiBedGrid();
        }
    } catch (err) {
        console.warn("API fetch error, waiting for WebSocket data:", err);
    }
}

// WebSocket Telemetry Client
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        document.getElementById("ws-status-dot").className = "status-dot online";
        document.getElementById("ws-status-text").textContent = "LIVE TELEMETRY";
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // 1. Process 60Hz high-frequency waveform samples
        if (data.waveforms) {
            for (const bedId in data.waveforms) {
                if (waveBuffers[bedId]) {
                    waveBuffers[bedId].ecg.push(data.waveforms[bedId].ecg);
                    waveBuffers[bedId].ppg.push(data.waveforms[bedId].ppg);
                    
                    // Cap buffer size
                    if (waveBuffers[bedId].ecg.length > 300) waveBuffers[bedId].ecg.shift();
                    if (waveBuffers[bedId].ppg.length > 300) waveBuffers[bedId].ppg.shift();
                }
            }
        }

        // 2. Process 1Hz vital parameter updates & ML evaluations
        if (data.vitals) {
            for (const bedId in data.vitals) {
                const patient = patientsData.find(p => p.id === bedId);
                if (patient) {
                    patient.vitals = data.vitals[bedId].vitals;
                    patient.analysis = data.vitals[bedId].analysis;
                }
            }
            updatePatientTabBadges();
            updateSingleBedUI();
            if (isMultiBedView) renderMultiBedGrid();
            checkAndTriggerAlarmSound();
        }
    };

    socket.onclose = () => {
        document.getElementById("ws-status-dot").className = "status-dot";
        document.getElementById("ws-status-text").textContent = "DISCONNECTED - RETRYING";
        setTimeout(connectWebSocket, 2000);
    };

    socket.onerror = () => {
        socket.close();
    };
}

// Render Patient Tabs
function renderPatientTabs() {
    const container = document.getElementById("patient-tabs");
    container.innerHTML = "";

    patientsData.forEach(p => {
        const btn = document.createElement("button");
        btn.className = `tab-btn ${p.id === currentBedId ? 'active' : ''}`;
        btn.dataset.bed = p.id;
        
        const riskTier = (p.analysis?.risk_level || "LOW").toLowerCase();
        
        btn.innerHTML = `
            <span>${p.id}: ${p.name}</span>
            <span class="tab-badge ${riskTier}">${p.analysis?.risk_level || 'LOW'}</span>
        `;

        btn.onclick = () => {
            currentBedId = p.id;
            renderPatientTabs();
            updateSingleBedUI();
        };

        container.appendChild(btn);
    });
}

function updatePatientTabBadges() {
    patientsData.forEach(p => {
        const btn = document.querySelector(`.tab-btn[data-bed="${p.id}"]`);
        if (btn) {
            const badge = btn.querySelector('.tab-badge');
            if (badge && p.analysis) {
                const riskTier = p.analysis.risk_level.toLowerCase();
                badge.className = `tab-badge ${riskTier}`;
                badge.textContent = p.analysis.risk_level;
            }
        }
    });
}

// Update Single Bed Active UI
function updateSingleBedUI() {
    const patient = patientsData.find(p => p.id === currentBedId);
    if (!patient || !patient.vitals) return;

    // Header info
    document.getElementById("p-name").textContent = patient.name;
    document.getElementById("p-bed").textContent = patient.id;
    document.getElementById("p-age-gender").textContent = `${patient.age} Y/O ${patient.gender.toUpperCase()}`;
    document.getElementById("p-admission").textContent = patient.admission_type;
    document.getElementById("p-doctor").textContent = patient.doctor;

    // Vitals
    const v = patient.vitals;
    const a = patient.analysis;

    document.getElementById("val-hr").textContent = v.heart_rate;
    document.getElementById("val-spo2").textContent = v.spo2;

    document.getElementById("card-hr").textContent = v.heart_rate;
    document.getElementById("card-spo2").innerHTML = `${v.spo2}<small>%</small>`;
    document.getElementById("card-bp").textContent = `${v.sys_bp}/${v.dia_bp}`;
    document.getElementById("card-map").textContent = v.map;
    document.getElementById("card-rr").innerHTML = `${v.resp_rate}<small>rpm</small>`;
    document.getElementById("card-temp").innerHTML = `${v.temp}<small>°C</small>`;

    // Risk Card
    if (a) {
        document.getElementById("risk-score-val").textContent = a.risk_score;
        const statusEl = document.getElementById("risk-level-status");
        statusEl.textContent = `${a.risk_level} RISK`;
        
        // Dynamic Risk Colors
        let color = "var(--risk-low)";
        if (a.risk_level === "MEDIUM") color = "var(--risk-med)";
        if (a.risk_level === "HIGH") color = "var(--risk-high)";
        if (a.risk_level === "CRITICAL") color = "var(--risk-critical)";
        
        statusEl.style.color = color;
        document.getElementById("risk-score-val").style.color = color;

        const flagsText = a.detected_flags.length > 0 
            ? a.detected_flags.join(", ") 
            : "Normal Sinus Telemetry";
        document.getElementById("risk-flags").textContent = flagsText;
    }
}

// 60 FPS Oscilloscope Canvas Sweeper
function startCanvasRenderLoop() {
    const canvasECG = document.getElementById("canvas-ecg");
    const canvasPPG = document.getElementById("canvas-ppg");
    
    if (!canvasECG || !canvasPPG) return;

    const ctxECG = canvasECG.getContext("2d");
    const ctxPPG = canvasPPG.getContext("2d");

    let prevEcgY = canvasECG.height / 2;
    let prevPpgY = canvasPPG.height / 2;

    function render() {
        const buffer = waveBuffers[currentBedId];
        const width = canvasECG.width;
        const heightECG = canvasECG.height;
        const heightPPG = canvasPPG.height;

        if (buffer && buffer.ecg.length > 0) {
            const ecgVal = buffer.ecg[buffer.ecg.length - 1];
            const ppgVal = buffer.ppg[buffer.ppg.length - 1];

            // Scale to canvas coordinates
            const ecgY = (heightECG / 2) - (ecgVal * (heightECG * 0.35));
            const ppgY = heightPPG - (ppgVal * heightPPG * 0.8) - 10;

            const nextX = (sweepX + SWEEP_SPEED) % width;

            // Clear eraser bar ahead of sweep beam
            ctxECG.clearRect(nextX, 0, 16, heightECG);
            ctxPPG.clearRect(nextX, 0, 16, heightPPG);

            // Draw ECG segment
            ctxECG.strokeStyle = "#00ff66";
            ctxECG.lineWidth = 2.2;
            ctxECG.shadowBlur = 6;
            ctxECG.shadowColor = "#00ff66";
            ctxECG.beginPath();
            ctxECG.moveTo(sweepX, prevEcgY);
            ctxECG.lineTo(nextX, ecgY);
            ctxECG.stroke();

            // Draw PPG segment
            ctxPPG.strokeStyle = "#00e5ff";
            ctxPPG.lineWidth = 2.0;
            ctxPPG.shadowBlur = 6;
            ctxPPG.shadowColor = "#00e5ff";
            ctxPPG.beginPath();
            ctxPPG.moveTo(sweepX, prevPpgY);
            ctxPPG.lineTo(nextX, ppgY);
            ctxPPG.stroke();

            prevEcgY = ecgY;
            prevPpgY = ppgY;
            sweepX = nextX;
        }

        requestAnimationFrame(render);
    }

    requestAnimationFrame(render);
}

// Multi-Bed View Renderer
function renderMultiBedGrid() {
    const grid = document.getElementById("multi-bed-view");
    grid.innerHTML = "";

    patientsData.forEach(p => {
        const v = p.vitals || {};
        const a = p.analysis || {};
        const riskTier = (a.risk_level || "LOW").toLowerCase();

        const card = document.createElement("div");
        card.className = "bed-station-card";
        card.onclick = () => {
            currentBedId = p.id;
            isMultiBedView = false;
            document.getElementById("single-bed-view").classList.remove("hidden");
            document.getElementById("multi-bed-view").classList.add("hidden");
            document.getElementById("view-mode-label").textContent = "MULTI BED STATION";
            renderPatientTabs();
            updateSingleBedUI();
        };

        card.innerHTML = `
            <div class="station-header">
                <div class="station-bed">${p.id}: ${p.name}</div>
                <span class="tab-badge ${riskTier}">${a.risk_level || 'LOW'}</span>
            </div>
            <div class="station-vitals-row">
                <div>
                    <small style="color:var(--ecg-green)">HR</small>
                    <div class="st-metric-val" style="color:var(--ecg-green)">${v.heart_rate || '--'}</div>
                </div>
                <div>
                    <small style="color:var(--ppg-cyan)">SpO2</small>
                    <div class="st-metric-val" style="color:var(--ppg-cyan)">${v.spo2 || '--'}%</div>
                </div>
                <div>
                    <small style="color:var(--bp-red)">BP</small>
                    <div class="st-metric-val" style="color:var(--bp-red)">${v.sys_bp || '--'}/${v.dia_bp || '--'}</div>
                </div>
                <div>
                    <small style="color:var(--temp-purple)">TEMP</small>
                    <div class="st-metric-val" style="color:var(--temp-purple)">${v.temp || '--'}°</div>
                </div>
            </div>
        `;

        grid.appendChild(card);
    });
}

// Acoustic Alarm Feedback
function checkAndTriggerAlarmSound() {
    if (alarmAudioMuted) return;

    const criticalPatient = patientsData.find(p => p.analysis?.risk_level === "CRITICAL");
    if (criticalPatient) {
        playBeepSound();
    }
}

function playBeepSound() {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === "suspended") audioCtx.resume();

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.value = 880; // A5 note high alert
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);

        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) {
        // Ignore browser autoplay restrictions until user interaction
    }
}

// UI Event Listeners
function initEventListeners() {
    // View Switcher
    document.getElementById("btn-toggle-view").onclick = () => {
        isMultiBedView = !isMultiBedView;
        const singleView = document.getElementById("single-bed-view");
        const multiView = document.getElementById("multi-bed-view");
        const label = document.getElementById("view-mode-label");

        if (isMultiBedView) {
            singleView.classList.add("hidden");
            multiView.classList.remove("hidden");
            label.textContent = "SINGLE BED VIEW";
            renderMultiBedGrid();
        } else {
            singleView.classList.remove("hidden");
            multiView.classList.add("hidden");
            label.textContent = "MULTI BED STATION";
            updateSingleBedUI();
        }
    };

    // Silence Alarms Button
    document.getElementById("btn-silence").onclick = () => {
        alarmAudioMuted = !alarmAudioMuted;
        const btn = document.getElementById("btn-silence");
        if (alarmAudioMuted) {
            btn.style.opacity = "0.5";
            btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg> MUTED`;
        } else {
            btn.style.opacity = "1";
            btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg> SILENCE ALARMS`;
        }
    };

    // Simulator Modal Controls
    const simModal = document.getElementById("sim-modal");
    document.getElementById("btn-open-sim").onclick = () => simModal.classList.remove("hidden");
    document.getElementById("btn-close-sim").onclick = () => simModal.classList.add("hidden");

    // Simulator Buttons
    document.querySelectorAll(".sim-option-btn").forEach(btn => {
        btn.onclick = async () => {
            const bedId = document.getElementById("sim-bed-select").value;
            const condition = btn.dataset.condition;

            try {
                const res = await fetch("/api/simulate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ bed_id: bedId, condition: condition })
                });

                if (res.ok) {
                    const result = await res.json();
                    simModal.classList.add("hidden");
                    fetchPatientsList();
                    fetchAlerts();
                }
            } catch (err) {
                console.error("Simulation error:", err);
            }
        };
    });
}

// Fetch Alerts Log
async function fetchAlerts() {
    try {
        const res = await fetch("/api/alerts");
        if (res.ok) {
            const alerts = await res.json();
            const feed = document.getElementById("alert-feed");
            document.getElementById("alert-count-badge").textContent = `${alerts.length} ALERTS`;

            if (alerts.length === 0) {
                feed.innerHTML = `<div class="empty-feed">No active clinical alarms recorded. System monitoring nominal.</div>`;
                return;
            }

            feed.innerHTML = alerts.map(a => `
                <div class="alert-item ${a.risk_level.toLowerCase()}">
                    <div>
                        <strong>[${a.timestamp}] ${a.bed_id} (${a.patient_name}):</strong>
                        <span>${a.flags.join(", ")} - HR: ${a.vitals.heart_rate} SpO2: ${a.vitals.spo2}%</span>
                    </div>
                    ${!a.acknowledged ? `<button class="ack-btn" onclick="acknowledgeAlert('${a.alert_id}')">ACKNOWLEDGE</button>` : `<span style="font-size:0.7rem;opacity:0.7">ACKNOWLEDGED</span>`}
                </div>
            `).join("");
        }
    } catch (e) {
        console.warn("Could not fetch alerts log:", e);
    }
}

async function acknowledgeAlert(alertId) {
    try {
        await fetch("/api/alerts/acknowledge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ alert_id: alertId })
        });
        fetchAlerts();
    } catch (e) {
        console.error(e);
    }
}
