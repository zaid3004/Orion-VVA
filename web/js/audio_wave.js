// audio_wave.js

class AudioWave {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.width = canvas.width;
        this.height = canvas.height;
        this.animId = null;

        // Animation state
        this.active = false;
        this.amplitude = 10;
        this.noise = 0;
        this.phase = 0;
    }

    setActive(isActive) {
        this.active = isActive;
        if (isActive) {
            this.start();
        } else {
            this.stop();
            this.renderIdle();
        }
    }

    // Optionally: set amplitude from microphone loudness (0..1)
    setLoudness(loudness) {
        this.amplitude = 4 + 18 * Math.max(0, Math.min(1, loudness));
    }

    start() {
        if (this.animId) return;
        this.animate();
    }

    stop() {
        if (this.animId) {
            cancelAnimationFrame(this.animId);
            this.animId = null;
        }
    }

    animate() {
        this.animId = requestAnimationFrame(() => this.animate());
        this.render();
        this.phase += 0.13;
    }

    render() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.width, this.height);
        ctx.save();
        ctx.strokeStyle = '#4fc3f7';
        ctx.lineWidth = 3;
        ctx.beginPath();

        for (let x = 0; x < this.width; x++) {
            // Sine with modulated amplitude
            let relX = x / this.width * 2 * Math.PI;
            let y = this.height / 2 +
                Math.sin(relX * 2 + this.phase) *
                (this.amplitude + Math.sin(this.phase + relX) * this.amplitude * 0.25);
            ctx.lineTo(x, y);
        }
        ctx.stroke();
        ctx.restore();
    }

    renderIdle() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.width, this.height);
        ctx.save();
        ctx.strokeStyle = "#8ec7fc";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, this.height / 2);
        ctx.lineTo(this.width, this.height / 2);
        ctx.stroke();
        ctx.restore();
    }
}

// Attach to window so that app.js can use it
window.AudioWave = AudioWave;
