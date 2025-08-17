// speech.js

let audioContext = null;
let mediaStream = null;
let analyser = null;
let dataArray = null;
let animationId = null;
let waveObj = null;

// Call this when you want to start listening & visualizing
async function startMicVisualization(wave) {
    waveObj = wave;
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = audioContext.createMediaStreamSource(mediaStream);

        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        dataArray = new Uint8Array(analyser.fftSize);

        source.connect(analyser);

        animate();
    } catch (err) {
        console.error("Microphone access failed:", err);
        if (waveObj) waveObj.setActive(false);
    }
}

// Call this when listening ends, to stop animation & close mic
function stopMicVisualization() {
    if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    if (waveObj) {
        waveObj.setActive(false);
    }
}

function animate() {
    if (!analyser || !dataArray) return;
    analyser.getByteTimeDomainData(dataArray);

    // Compute peak-to-peak amplitude
    let min = 128, max = 128;
    for (let i = 0; i < dataArray.length; i++) {
        if (dataArray[i] < min) min = dataArray[i];
        if (dataArray[i] > max) max = dataArray[i];
    }
    let amplitude = (max - min) / 128; // Range (0..1)

    if (waveObj) waveObj.setActive(true);
    if (waveObj) waveObj.setLoudness(amplitude);

    animationId = requestAnimationFrame(animate);
}

// Optionally, expose to window for app.js to use
window.startMicVisualization = startMicVisualization;
window.stopMicVisualization = stopMicVisualization;
