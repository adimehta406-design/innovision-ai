/**
 * TruthLens – Frontend Application Logic
 * Handles file upload, API communication, and dynamic results rendering.
 */

// State
let selectedFile = null;

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const uploadPreview = document.getElementById('upload-preview');
const previewImg = document.getElementById('preview-img');
const fileName = document.getElementById('file-name');
const analyzeBtn = document.getElementById('analyze-btn');
const heroSection = document.getElementById('hero');
const uploadSection = document.getElementById('upload-section');
const loadingSection = document.getElementById('loading-section');
const resultsSection = document.getElementById('results-section');
const featuresSection = document.getElementById('features');

// === CONFIGURATION ===
// If running locally, use current origin. If on Surge, use Render backend.
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? window.location.origin
    : 'https://innovisionai.onrender.com'; // Production Backend URL

// ============ DRAG & DROP ============
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
        handleFileSelect(files[0]);
    }
});

uploadZone.addEventListener('click', (e) => {
    if (e.target.closest('.browse-btn') || e.target.closest('.analyze-btn')) return;
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

// ============ FILE HANDLING ============
function handleFileSelect(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file (JPEG, PNG, WebP, etc.)');
        return;
    }
    if (file.size > 20 * 1024 * 1024) {
        alert('Image is too large (max 20MB)');
        return;
    }

    selectedFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        uploadPreview.style.display = 'block';
        fileName.textContent = `${file.name} (${formatFileSize(file.size)})`;
    };
    reader.readAsDataURL(file);

    // Show analyze button
    analyzeBtn.style.display = 'block';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ============ ANALYSIS ============
async function startAnalysis() {
    if (!selectedFile) return;

    // Switch to loading state
    heroSection.style.display = 'none';
    uploadSection.style.display = 'none';
    featuresSection.style.display = 'none';
    resultsSection.style.display = 'none';
    loadingSection.style.display = 'block';

    // Animate loading steps
    const steps = ['step-exif', 'step-ela', 'step-tamper', 'step-ocr', 'step-ai', 'step-verdict'];
    const statusMessages = [
        'Extracting EXIF metadata...',
        'Running Error Level Analysis...',
        'Detecting image tampering...',
        'Performing OCR text extraction...',
        'Analyzing for AI generation...',
        'Generating AI verdict...'
    ];

    let stepIndex = 0;
    const stepInterval = setInterval(() => {
        if (stepIndex < steps.length) {
            // Mark previous as done
            if (stepIndex > 0) {
                document.getElementById(steps[stepIndex - 1]).classList.remove('active');
                document.getElementById(steps[stepIndex - 1]).classList.add('done');
                const prevIcon = document.getElementById(steps[stepIndex - 1]).querySelector('.loading-step-icon');
                prevIcon.textContent = '✓';
            }
            // Mark current as active
            document.getElementById(steps[stepIndex]).classList.add('active');
            document.getElementById('loading-status').textContent = statusMessages[stepIndex];
            stepIndex++;
        }
    }, 800);

    // Send to API
    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            body: formData
        });

        clearInterval(stepInterval);

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Analysis failed (HTTP ${response.status})`);
        }

        const data = await response.json();

        // Mark all steps as done
        steps.forEach(s => {
            const el = document.getElementById(s);
            el.classList.remove('active');
            el.classList.add('done');
            el.querySelector('.loading-step-icon').textContent = '✓';
        });

        // Short delay for UX
        await new Promise(r => setTimeout(r, 600));

        // Show results
        renderResults(data);

    } catch (err) {
        clearInterval(stepInterval);
        console.error('Analysis error:', err);
        loadingSection.style.display = 'none';
        heroSection.style.display = 'block';
        uploadSection.style.display = 'block';
        featuresSection.style.display = 'block';
        alert(`Analysis failed: ${err.message}`);
    }
}

// ============ RENDER RESULTS ============
function renderResults(data) {
    loadingSection.style.display = 'none';
    resultsSection.style.display = 'block';
    resultsSection.innerHTML = '';

    const risk = data.risk;
    const verdict = data.verdict;
    const riskLevel = risk.risk_level.toLowerCase();

    // Color map
    const levelColors = {
        low: '#22c55e',
        medium: '#fbbf24',
        high: '#fb923c',
        critical: '#ef4444'
    };
    const scoreColor = levelColors[riskLevel] || '#4f8cff';

    // === Results Header ===
    const header = el('div', 'results-header');
    header.innerHTML = `
        <h2>Analysis Complete</h2>
        <div class="results-meta">
            <span>📁 ${data.filename}</span>
            <span>⏱️ ${data.analysis_time}s</span>
            <span>🆔 ${data.analysis_id}</span>
            <span>📐 ${formatFileSize(data.file_size)}</span>
        </div>
    `;
    resultsSection.appendChild(header);

    // === Risk Score Card ===
    const riskCard = el('div', 'risk-card');
    riskCard.innerHTML = `
        <div class="risk-gauge-container">
            <canvas id="risk-gauge" width="360" height="360"></canvas>
            <div class="risk-score-display">
                <div class="risk-score-number" style="color:${scoreColor}">${Math.round(risk.overall_score)}</div>
                <div class="risk-score-label">Risk Score</div>
            </div>
        </div>
        <div class="risk-info">
            <div class="risk-level-badge ${riskLevel}">
                ${risk.risk_emoji} ${risk.risk_level}
            </div>
            <div class="risk-description">${risk.risk_description}</div>
            <div class="risk-breakdown" id="risk-breakdown"></div>
        </div>
    `;
    resultsSection.appendChild(riskCard);

    // Draw gauge
    setTimeout(() => drawRiskGauge(risk.overall_score, scoreColor), 100);

    // Risk breakdown bars
    const breakdownContainer = document.getElementById('risk-breakdown');
    if (risk.breakdown) {
        risk.breakdown.forEach(item => {
            const barLevel = item.level.toLowerCase();
            const barColor = levelColors[barLevel] || '#4f8cff';
            const barItem = el('div', 'risk-bar-item');
            barItem.innerHTML = `
                <div class="risk-bar-label">${item.analyzer} (${item.raw_score})</div>
                <div class="risk-bar">
                    <div class="risk-bar-fill ${barLevel}" id="bar-${item.analyzer.replace(/\s/g, '')}" style="width:0%"></div>
                </div>
            `;
            breakdownContainer.appendChild(barItem);
        });

        // Animate bars
        setTimeout(() => {
            risk.breakdown.forEach(item => {
                const barEl = document.getElementById(`bar-${item.analyzer.replace(/\s/g, '')}`);
                if (barEl) barEl.style.width = `${item.raw_score}%`;
            });
        }, 300);
    }

    // === AI Verdict Card ===
    const verdictCard = el('div', 'verdict-card');
    const verdictBgColors = {
        'LIKELY AUTHENTIC': 'rgba(34,197,94,0.12)',
        'POSSIBLY MANIPULATED': 'rgba(251,191,36,0.12)',
        'LIKELY MANIPULATED': 'rgba(251,146,60,0.12)',
        'HIGHLY SUSPICIOUS': 'rgba(239,68,68,0.12)'
    };
    const verdictTextColors = {
        'LIKELY AUTHENTIC': '#22c55e',
        'POSSIBLY MANIPULATED': '#fbbf24',
        'LIKELY MANIPULATED': '#fb923c',
        'HIGHLY SUSPICIOUS': '#ef4444'
    };
    const vBg = verdictBgColors[verdict.verdict] || 'rgba(79,140,255,0.12)';
    const vColor = verdictTextColors[verdict.verdict] || '#4f8cff';

    verdictCard.innerHTML = `
        <div class="verdict-header">
            <span class="verdict-icon">⚖️</span>
            <span class="verdict-title">AI Verdict</span>
            <span class="verdict-label" style="background:${vBg};color:${vColor}">${verdict.verdict}</span>
        </div>
        <div class="verdict-text">${escapeHtml(verdict.ai_analysis)}</div>
    `;
    resultsSection.appendChild(verdictCard);

    // === Analysis Cards Grid ===
    const grid = el('div', 'analysis-grid');

    // EXIF card
    grid.appendChild(createAnalysisCard('📋', 'EXIF Metadata', data.exif));
    // ELA card
    grid.appendChild(createAnalysisCard('🔥', 'Error Level Analysis', data.ela));
    // Tampering card
    grid.appendChild(createAnalysisCard('🔎', 'Tampering Detection', data.tampering));
    // OCR card
    grid.appendChild(createAnalysisCard('📝', 'OCR Text Analysis', data.ocr));
    // AI Detection card
    grid.appendChild(createAnalysisCard('🤖', 'AI Generation Detection', data.ai_detection));

    resultsSection.appendChild(grid);

    // === Evidence Images ===
    const evidenceSection = el('div', 'evidence-section');
    evidenceSection.innerHTML = `<h3 class="evidence-title">🖼️ Visual Evidence</h3>`;
    const evidenceGrid = el('div', 'evidence-grid');

    // Original image
    if (data.original_image) {
        evidenceGrid.appendChild(createEvidenceCard('📷 Original Image', data.original_image));
    }
    // ELA heatmap
    if (data.ela_image) {
        evidenceGrid.appendChild(createEvidenceCard('🔥 ELA Heatmap', data.ela_image));
    }
    // Annotated (tampering)
    if (data.tamper_annotated_image) {
        evidenceGrid.appendChild(createEvidenceCard('🔎 Tamper Annotations', data.tamper_annotated_image));
    }
    // Noise map
    if (data.noise_map_image) {
        evidenceGrid.appendChild(createEvidenceCard('📊 Noise Map', data.noise_map_image));
    }

    evidenceSection.appendChild(evidenceGrid);
    resultsSection.appendChild(evidenceSection);

    // === EXIF Metadata Table ===
    if (data.exif && data.exif.metadata && Object.keys(data.exif.metadata).length > 0) {
        const metaSection = el('div', 'evidence-section');
        metaSection.innerHTML = `<h3 class="evidence-title">📋 EXIF Metadata Details</h3>`;
        const metaCard = el('div', 'analysis-card');
        metaCard.style.maxHeight = '400px';
        metaCard.style.overflowY = 'auto';

        let tableHtml = '<div class="metadata-table">';
        for (const [key, value] of Object.entries(data.exif.metadata)) {
            tableHtml += `
                <div class="metadata-row">
                    <div class="metadata-key">${escapeHtml(key)}</div>
                    <div class="metadata-value">${escapeHtml(String(value).substring(0, 200))}</div>
                </div>
            `;
        }
        tableHtml += '</div>';
        metaCard.innerHTML = tableHtml;
        metaSection.appendChild(metaCard);
        resultsSection.appendChild(metaSection);
    }

    // === All Flags Summary ===
    if (risk.all_flags && risk.all_flags.length > 0) {
        const flagsSection = el('div', 'evidence-section');
        flagsSection.innerHTML = `<h3 class="evidence-title">🚩 All Detection Flags (${risk.all_flags.length})</h3>`;
        const flagsCard = el('div', 'analysis-card');
        const flagsDiv = el('div', 'analysis-flags');
        risk.all_flags.forEach(flag => {
            const flagEl = el('div', 'analysis-flag ' + getFlagClass(flag));
            flagEl.textContent = flag;
            flagsDiv.appendChild(flagEl);
        });
        flagsCard.appendChild(flagsDiv);
        flagsSection.appendChild(flagsCard);
        resultsSection.appendChild(flagsSection);
    }

    // === New Analysis Button ===
    const newBtn = document.createElement('button');
    newBtn.className = 'new-analysis-btn';
    newBtn.textContent = '🔄 Analyze Another Image';
    newBtn.onclick = resetUI;
    resultsSection.appendChild(newBtn);
}

// ============ HELPER FUNCTIONS ============

function el(tag, className) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    return e;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getFlagClass(flag) {
    if (flag.includes('🔴')) return 'danger';
    if (flag.includes('🟡')) return 'warning';
    if (flag.includes('✅')) return 'success';
    return 'info';
}

function createAnalysisCard(icon, title, data) {
    const card = el('div', 'analysis-card');
    const score = data?.risk_score ?? 0;
    const summary = data?.summary ?? 'N/A';
    const flags = data?.flags ?? [];

    const levelColors = { 0: '#22c55e', 25: '#22c55e', 50: '#fbbf24', 75: '#fb923c', 100: '#ef4444' };
    let scoreColorVal = '#22c55e';
    if (score > 75) scoreColorVal = '#ef4444';
    else if (score > 50) scoreColorVal = '#fb923c';
    else if (score > 25) scoreColorVal = '#fbbf24';

    let flagsHtml = '';
    flags.slice(0, 4).forEach(f => {
        flagsHtml += `<div class="analysis-flag ${getFlagClass(f)}">${escapeHtml(f)}</div>`;
    });

    card.innerHTML = `
        <div class="analysis-card-header">
            <div class="analysis-card-title">
                <span class="icon">${icon}</span>
                <span>${title}</span>
            </div>
            <div class="analysis-card-score" style="color:${scoreColorVal}">${score}</div>
        </div>
        <div class="analysis-card-summary">${escapeHtml(summary)}</div>
        <div class="analysis-flags">${flagsHtml}</div>
    `;
    return card;
}

function createEvidenceCard(label, imageSrc) {
    const card = el('div', 'evidence-card');
    card.innerHTML = `
        <div class="evidence-card-label">${label}</div>
        <img src="${imageSrc}" alt="${label}" loading="lazy">
    `;
    return card;
}

// ============ RISK GAUGE (CANVAS) ============
function drawRiskGauge(score, color) {
    const canvas = document.getElementById('risk-gauge');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const centerX = 180;
    const centerY = 180;
    const radius = 150;

    // Clear
    ctx.clearRect(0, 0, 360, 360);

    // Background arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
    ctx.lineWidth = 16;
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Score arc (animated)
    const maxAngle = 1.5 * Math.PI;
    const targetAngle = (score / 100) * maxAngle;
    let currentAngle = 0;

    function animate() {
        if (currentAngle < targetAngle) {
            currentAngle = Math.min(currentAngle + 0.04, targetAngle);

            ctx.clearRect(0, 0, 360, 360);

            // Background
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
            ctx.lineWidth = 16;
            ctx.strokeStyle = 'rgba(255,255,255,0.06)';
            ctx.lineCap = 'round';
            ctx.stroke();

            // Score
            const gradient = ctx.createLinearGradient(0, 0, 360, 360);
            gradient.addColorStop(0, color);
            gradient.addColorStop(1, adjustColor(color, -30));

            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.75 * Math.PI + currentAngle);
            ctx.lineWidth = 16;
            ctx.strokeStyle = gradient;
            ctx.lineCap = 'round';
            ctx.stroke();

            // Glow effect
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.75 * Math.PI + currentAngle);
            ctx.lineWidth = 24;
            ctx.strokeStyle = color + '22';
            ctx.lineCap = 'round';
            ctx.stroke();

            requestAnimationFrame(animate);
        }
    }
    animate();
}

function adjustColor(hex, amount) {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = Math.min(255, Math.max(0, (num >> 16) + amount));
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amount));
    const b = Math.min(255, Math.max(0, (num & 0x0000FF) + amount));
    return '#' + (0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1);
}

// ============ RESET UI ============
function resetUI() {
    // Reset state
    selectedFile = null;
    fileInput.value = '';
    uploadPreview.style.display = 'none';
    analyzeBtn.style.display = 'none';
    previewImg.src = '';
    fileName.textContent = '';

    // Reset loading steps
    ['step-exif', 'step-ela', 'step-tamper', 'step-ocr', 'step-ai', 'step-verdict'].forEach(s => {
        const el = document.getElementById(s);
        el.classList.remove('active', 'done');
        // Restore original icons
        const icons = { 'step-exif': '📋', 'step-ela': '🔥', 'step-tamper': '🔎', 'step-ocr': '📝', 'step-ai': '🤖', 'step-verdict': '⚖️' };
        el.querySelector('.loading-step-icon').textContent = icons[s];
    });

    // Switch views
    resultsSection.style.display = 'none';
    loadingSection.style.display = 'none';
    heroSection.style.display = 'block';
    uploadSection.style.display = 'block';
    featuresSection.style.display = 'block';

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============ UNIVERSAL TRUTH SYSTEM LOGIC ============

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.input-section').forEach(sec => sec.classList.remove('active'));

    document.getElementById(`tab-${tab}`).classList.add('active');
    document.getElementById(`${tab}-section`).classList.add('active');
}

function updateCharCount(textarea) {
    document.getElementById('char-count').innerText = `${textarea.value.length}/5000`;
}

async function startTextVerification() {
    const text = document.getElementById('claim-text').value;
    if (!text || text.length < 5) {
        alert("Please enter some text to verify.");
        return;
    }

    const loadingSection = document.getElementById('loading-section');
    const resultsSection = document.getElementById('results-section');
    const uploadSection = document.getElementById('upload-section');
    const heroSection = document.getElementById('hero');
    const featuresSection = document.getElementById('features');

    heroSection.style.display = 'none';
    uploadSection.style.display = 'none';
    featuresSection.style.display = 'none';
    loadingSection.style.display = 'flex'; // Changed to flex for better centering if needed, or block
    loadingSection.style.display = 'block';
    resultsSection.innerHTML = '';

    // Update loading steps for Text
    document.querySelector('.loading-title').innerText = "Verifying Claim...";
    document.getElementById('loading-status').innerText = "Cross-referencing trusted sources...";

    // Hide visual steps, show generic spinner
    document.querySelector('.loading-steps').style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/api/verify/text`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });

        if (!response.ok) throw new Error("Verification failed");

        const data = await response.json();
        renderTextResults(data);

        loadingSection.style.display = 'none';
        resultsSection.style.display = 'block';

        // Restore loading steps for next time
        document.querySelector('.loading-steps').style.display = 'grid';
        document.querySelector('.loading-title').innerText = "Analyzing Image...";

    } catch (e) {
        alert("Error: " + e.message);
        location.reload();
    }
}

function renderTextResults(data) {
    const resultsSection = document.getElementById('results-section');

    // Truth Score Color
    let scoreColor = 'var(--text-secondary)';
    let verdictClass = 'verdict-UNVERIFIED';

    if (data.truth_score > 80) { scoreColor = 'var(--success)'; verdictClass = 'verdict-TRUE'; }
    else if (data.truth_score < 40) { scoreColor = 'var(--danger)'; verdictClass = 'verdict-FALSE'; }
    else { scoreColor = 'var(--warning)'; verdictClass = 'verdict-MISLEADING'; }

    // Risk Gauge Data (Reuse existing gauge implementation if possible, or simple number)
    // We'll use a simple card layout for text

    const html = `
        <div class="results-header">
            <h2>Claim Verification Complete</h2>
            <div class="results-meta">
                <span>📝 Text Analysis</span>
                <span>⏱️ < 10s</span>
                <span>🆔 ${Math.random().toString(36).substr(2, 9)}</span>
            </div>
        </div>

        <div class="verdict-card" style="border-top: 4px solid ${scoreColor}">
            <div class="verdict-header">
                <span class="verdict-icon">⚖️</span>
                <span class="verdict-title">Truth Assessment</span>
                <span class="text-verdict-badge ${verdictClass}">${data.verdict}</span>
            </div>
            
            <div style="margin-bottom: 2rem; text-align: center;">
                <div style="font-size: 4rem; font-weight: 800; color: ${scoreColor}; line-height: 1;">${data.truth_score}%</div>
                <div style="font-size: 0.9rem; opacity: 0.7; letter-spacing: 2px;">TRUTH SCORE</div>
            </div>

            <div class="verdict-text">
                <strong>Analysis:</strong> ${data.explanation}
            </div>
            
             <div class="sources-list">
                <h3 style="margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;">📚 Evidence Sources</h3>
                ${data.sources.length > 0 ? data.sources.map(s => `
                    <div class="source-card ${s.category.toLowerCase().replace(' ', '-').replace('/', '-')}">
                        <div class="source-meta">
                            <span class="source-domain">${s.domain}</span>
                            <span>${s.category}</span>
                        </div>
                        <a href="${s.href || '#'}" target="_blank" class="source-title">${s.title}</a>
                        <div class="source-snippet">${s.body || 'No preview available.'}</div>
                    </div>
                `).join('') : '<div style="opacity:0.6; padding:1rem;">No public sources found.</div>'}
            </div>
            
            <button class="new-analysis-btn" onclick="location.reload()">🔄 Verify Another Claim</button>
        </div>
    `;

    resultsSection.innerHTML = html;
}
