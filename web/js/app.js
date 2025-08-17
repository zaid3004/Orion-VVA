// app.js

let wave = null;

window.onload = function () {
    const micBtn = document.getElementById("mic-btn");
    const userText = document.getElementById("user-text");
    const assistantText = document.getElementById("assistant-text");
    const statusDiv = document.getElementById("status");
    const canvas = document.getElementById("audio-wave");

    wave = new AudioWave(canvas);
    wave.renderIdle();

    // Button toggles listening
    micBtn.addEventListener("click", function () {
        if (!micBtn.classList.contains("listening")) {
            micBtn.classList.add("listening");
            wave.setActive(true);
            eel.start_listening();
        }
    });

    // Status/message update functions exposed to Python
    eel.expose(display_user_text);
    eel.expose(display_assistant_text);
    eel.expose(set_status);
    eel.expose(set_wave_status);

    function display_user_text(text) {
        userText.textContent = text || "";
    }

    function display_assistant_text(text) {
        assistantText.textContent = text || "";
        // Stop animation/mic if any "error" returned
        document.getElementById("mic-btn").classList.remove("listening");
        wave.setActive(false);
    }

    function set_status(text) {
        statusDiv.textContent = text || "";
    }

    function set_wave_status(state) {
        if (state === 'listening') {
            wave.setActive(true);
        } else {
            wave.setActive(false);
        }
        if (state !== 'listening') {
            document.getElementById("mic-btn").classList.remove("listening");
        }
    }
};
