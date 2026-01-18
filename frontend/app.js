/**
 * AI Shorts Generator - Frontend Application
 * Handles video upload, shorts identification, and generation
 */

const API_BASE = 'http://127.0.0.1:8001/api/v1';

// State
let currentVideoId = null;
let identifiedShorts = [];

// DOM Elements
const elements = {
    // Upload
    uploadZone: document.getElementById('uploadZone'),
    fileInput: document.getElementById('fileInput'),
    uploadProgress: document.getElementById('uploadProgress'),
    fileName: document.getElementById('fileName'),
    progressPercent: document.getElementById('progressPercent'),
    progressFill: document.getElementById('progressFill'),
    videoInfo: document.getElementById('videoInfo'),
    videoPreview: document.getElementById('videoPreview'),
    videoName: document.getElementById('videoName'),
    videoSize: document.getElementById('videoSize'),
    removeVideoBtn: document.getElementById('removeVideoBtn'),

    // Identify
    identifySection: document.getElementById('identifySection'),
    maxShorts: document.getElementById('maxShorts'),
    identifyBtn: document.getElementById('identifyBtn'),
    processingStatus: document.getElementById('processingStatus'),
    statusTitle: document.getElementById('statusTitle'),
    statusSubtitle: document.getElementById('statusSubtitle'),
    minDuration: document.getElementById('minDuration'),
    maxDuration: document.getElementById('maxDuration'),
    minDurationValue: document.getElementById('minDurationValue'),
    maxDurationValue: document.getElementById('maxDurationValue'),

    // Results
    resultsSection: document.getElementById('resultsSection'),
    shortsCount: document.getElementById('shortsCount'),
    videoSummary: document.getElementById('videoSummary'),
    summaryText: document.getElementById('summaryText'),
    shortsList: document.getElementById('shortsList'),
    generateAllBtn: document.getElementById('generateAllBtn'),

    // Generated
    generatedSection: document.getElementById('generatedSection'),
    generatedList: document.getElementById('generatedList'),
    startOverBtn: document.getElementById('startOverBtn'),
};

// ========================================
// Slider Handlers
// ========================================

if (elements.minDuration) {
    elements.minDuration.addEventListener('input', (e) => {
        elements.minDurationValue.textContent = e.target.value;
    });
}

if (elements.maxDuration) {
    elements.maxDuration.addEventListener('input', (e) => {
        elements.maxDurationValue.textContent = e.target.value;
    });
}

// ========================================
// Upload Handlers
// ========================================

elements.uploadZone.addEventListener('click', () => {
    elements.fileInput.click();
});

elements.uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.uploadZone.classList.add('dragover');
});

elements.uploadZone.addEventListener('dragleave', () => {
    elements.uploadZone.classList.remove('dragover');
});

elements.uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
        handleFileUpload(file);
    }
});

elements.fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFileUpload(file);
    }
});

elements.removeVideoBtn.addEventListener('click', resetUpload);

async function handleFileUpload(file) {
    // Show progress
    elements.uploadZone.classList.add('hidden');
    elements.uploadProgress.classList.remove('hidden');
    elements.fileName.textContent = file.name;

    console.log('📤 Starting upload:', file.name, formatFileSize(file.size));

    const formData = new FormData();
    formData.append('file', file);

    try {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                elements.progressPercent.textContent = `${percent}%`;
                elements.progressFill.style.width = `${percent}%`;
                console.log(`Upload progress: ${percent}%`);
            }
        });

        xhr.addEventListener('load', () => {
            console.log('📥 Upload response:', xhr.status, xhr.responseText.slice(0, 200));
            if (xhr.status === 200 || xhr.status === 201) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    currentVideoId = response.video_id;
                    console.log('✅ Upload success:', response.video_id);
                    showVideoInfo(file, response);
                } catch (parseError) {
                    console.error('❌ Parse error:', parseError);
                    alert('Upload failed: Invalid response from server.');
                    resetUpload();
                }
            } else {
                console.error('❌ Upload failed with status:', xhr.status);
                alert(`Upload failed (${xhr.status}). Please try again.`);
                resetUpload();
            }
        });

        xhr.addEventListener('error', (e) => {
            console.error('❌ Network error:', e);
            alert('Upload failed. Please check your connection.');
            resetUpload();
        });

        xhr.addEventListener('timeout', () => {
            console.error('❌ Upload timed out');
            alert('Upload timed out. Please try again with a smaller file.');
            resetUpload();
        });

        // Set long timeout (10 minutes for large files)
        xhr.timeout = 600000;

        xhr.open('POST', `${API_BASE}/videos/upload`);
        xhr.send(formData);

    } catch (error) {
        console.error('❌ Upload error:', error);
        alert('Upload failed. Please try again.');
        resetUpload();
    }
}

function showVideoInfo(file, response) {
    elements.uploadProgress.classList.add('hidden');
    elements.videoInfo.classList.remove('hidden');
    elements.identifySection.classList.remove('hidden');

    elements.videoName.textContent = file.name;
    elements.videoSize.textContent = `Size: ${formatFileSize(file.size)}`;

    // Preview
    const url = URL.createObjectURL(file);
    elements.videoPreview.src = url;
    elements.videoPreview.load();
}

function resetUpload() {
    currentVideoId = null;
    identifiedShorts = [];

    elements.uploadZone.classList.remove('hidden');
    elements.uploadProgress.classList.add('hidden');
    elements.videoInfo.classList.add('hidden');
    elements.identifySection.classList.add('hidden');
    elements.resultsSection.classList.add('hidden');
    elements.generatedSection.classList.add('hidden');

    elements.progressFill.style.width = '0%';
    elements.progressPercent.textContent = '0%';
    elements.fileInput.value = '';
}

// ========================================
// Identify Handlers
// ========================================

elements.identifyBtn.addEventListener('click', identifyShorts);

async function identifyShorts() {
    if (!currentVideoId) return;

    const maxShorts = elements.maxShorts.value;
    const minDuration = elements.minDuration.value;
    const maxDuration = elements.maxDuration.value;

    // Show processing
    elements.identifyBtn.disabled = true;
    elements.processingStatus.classList.remove('hidden');
    elements.statusTitle.textContent = 'Transcribing audio with Whisper...';
    elements.statusSubtitle.textContent = 'Step 1 of 3';

    try {
        // Simulate step updates
        setTimeout(() => {
            elements.statusTitle.textContent = 'Analyzing for viral moments with Gemini...';
            elements.statusSubtitle.textContent = 'Step 2 of 3';
        }, 5000);

        setTimeout(() => {
            elements.statusTitle.textContent = 'Aligning precise timestamps...';
            elements.statusSubtitle.textContent = 'Step 3 of 3';
        }, 10000);

        // Build query params
        const params = new URLSearchParams();
        if (maxShorts && maxShorts !== '0') params.append('max_shorts', maxShorts);
        if (minDuration) params.append('min_duration', minDuration);
        if (maxDuration) params.append('max_duration', maxDuration);

        const response = await fetch(
            `${API_BASE}/shorts/identify/${currentVideoId}?${params.toString()}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error('Identification failed');
        }

        const data = await response.json();
        identifiedShorts = data.analysis.shorts;

        elements.processingStatus.classList.add('hidden');
        elements.identifyBtn.disabled = false;

        showResults(data.analysis);

    } catch (error) {
        console.error('Identify error:', error);
        alert('Failed to identify shorts. Please try again.');
        elements.processingStatus.classList.add('hidden');
        elements.identifyBtn.disabled = false;
    }
}

function showResults(analysis) {
    elements.resultsSection.classList.remove('hidden');
    elements.shortsCount.textContent = `${analysis.total_shorts_found} shorts found`;

    // Summary
    if (analysis.video_summary) {
        elements.videoSummary.classList.remove('hidden');
        elements.summaryText.textContent = analysis.video_summary;
    }

    // Shorts list
    elements.shortsList.innerHTML = analysis.shorts.map((short, index) => `
        <div class="short-card" data-index="${index}">
            <div class="short-rank">${index + 1}</div>
            <div class="short-content">
                <div class="short-title">${escapeHtml(short.title)}</div>
                <div class="short-meta">
                    <span>⏱️ ${short.start_time} - ${short.end_time}</span>
                    <span>📏 ${short.duration_seconds}s</span>
                </div>
                <div class="short-hook">"${escapeHtml(short.hook)}"</div>
            </div>
            <div class="short-score">
                <div class="score-value">${Math.round(short.virality_score)}</div>
                <div class="score-label">Viral Score</div>
            </div>
        </div>
    `).join('');

    // Scroll to results
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// ========================================
// Generate Handlers
// ========================================

elements.generateAllBtn.addEventListener('click', generateAllShorts);

async function generateAllShorts() {
    if (!currentVideoId || identifiedShorts.length === 0) return;

    elements.generateAllBtn.disabled = true;
    elements.generateAllBtn.innerHTML = '<span class="spinner"></span> Generating...';

    try {
        const response = await fetch(
            `${API_BASE}/shorts/generate/${currentVideoId}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error('Generation failed');
        }

        const data = await response.json();
        showGeneratedShorts(data.shorts);

    } catch (error) {
        console.error('Generate error:', error);
        alert('Failed to generate shorts. Please try again.');
        elements.generateAllBtn.disabled = false;
        elements.generateAllBtn.innerHTML = '<span class="btn-icon">🎬</span><span>Generate All Shorts</span>';
    }
}

function showGeneratedShorts(shorts) {
    elements.resultsSection.classList.add('hidden');
    elements.generatedSection.classList.remove('hidden');

    // Use origin only (not API_BASE) since download_url already includes /api/v1
    const baseUrl = window.location.origin;

    elements.generatedList.innerHTML = shorts.map((short) => `
        <div class="generated-card">
            <div class="generated-video">
                <video src="${baseUrl}${short.download_url}" controls preload="metadata"></video>
            </div>
            <div class="generated-info">
                <div class="generated-title">${escapeHtml(short.title)}</div>
                <div class="generated-duration">Duration: ${short.duration_seconds}s</div>
                <div class="generated-actions">
                    <a href="${baseUrl}${short.download_url}" download="${short.short_id}.mp4" class="btn btn-primary">
                        ⬇️ Download
                    </a>
                </div>
            </div>
        </div>
    `).join('');

    elements.generatedSection.scrollIntoView({ behavior: 'smooth' });
}

// ========================================
// Start Over
// ========================================

elements.startOverBtn.addEventListener('click', () => {
    resetUpload();
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ========================================
// Utilities
// ========================================

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
console.log('🎬 AI Shorts Generator loaded');
