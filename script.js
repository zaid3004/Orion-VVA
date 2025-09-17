/**
 * Orion Voice Assistant - Complete Frontend System
 * Handles authentication, 3-part layout, themes, and voice interaction
 */

class OrionVoiceAssistant {
    constructor() {
        // Authentication state
        this.isAuthenticated = false;
        this.currentUser = null;
        
        // Voice system state
        this.isListening = false;
        this.isSpeaking = false;
        this.recognition = null;
        this.wakeWordRecognition = null;
        this.synthesis = window.speechSynthesis;
        
        // Wake word detection
        this.wakeWords = ['orion', 'hey orion', 'talk to me orion', "daddy's home orion"];
        this.wakeWordListening = true;
        this.wakeWordEnabled = true;
        
        // Application state
        this.conversationHistory = [];
        this.timers = [];
        this.systemInfo = {};
        this.currentTheme = 'aurora';
        
        // Sidebar state
        this.sidebarOpen = false;
        
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.checkAuthStatus();
        this.setupEventListeners();
        this.loadUserSettings();
        console.log('Orion Voice Assistant initialized');
    }

    /**
     * Check if user is already authenticated
     */
    checkAuthStatus() {
        const savedUser = localStorage.getItem('orion_user');
        const authToken = localStorage.getItem('orion_token');
        
        if (savedUser && authToken) {
            try {
                this.currentUser = JSON.parse(savedUser);
                this.isAuthenticated = true;
                this.showMainApp();
            } catch (error) {
                console.error('Error parsing saved user data:', error);
                this.showAuthScreen();
            }
        } else {
            this.showAuthScreen();
        }
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Authentication form listeners
        this.setupAuthListeners();
        
        // Main app listeners (will be activated when authenticated)
        this.setupMainAppListeners();
    }

    /**
     * Setup authentication event listeners
     */
    setupAuthListeners() {
        // Form switching
        const showRegisterBtn = document.getElementById('show-register');
        const showLoginBtn = document.getElementById('show-login');
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');

        if (showRegisterBtn) {
            showRegisterBtn.addEventListener('click', (e) => {
                e.preventDefault();
                loginForm.classList.remove('active');
                registerForm.classList.add('active');
            });
        }

        if (showLoginBtn) {
            showLoginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                registerForm.classList.remove('active');
                loginForm.classList.add('active');
            });
        }

        // Form submissions
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRegister();
            });
        }
    }

    /**
     * Setup main application event listeners
     */
    setupMainAppListeners() {
        // User profile button
        const userProfileBtn = document.getElementById('user-profile-btn');
        if (userProfileBtn) {
            userProfileBtn.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        // Theme buttons
        const themeButtons = document.querySelectorAll('.theme-btn');
        themeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                this.changeTheme(theme);
            });
        });

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }

        // Voice control buttons
        const voiceBtn = document.getElementById('voice-btn');
        const stopBtn = document.getElementById('stop-btn');
        const stopSpeakingBtn = document.getElementById('stop-speaking-btn');
        
        if (voiceBtn) {
            voiceBtn.addEventListener('click', () => this.startListening());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopListening());
        }
        
        if (stopSpeakingBtn) {
            stopSpeakingBtn.addEventListener('click', () => this.stopSpeaking());
        }

        // Clear chat button
        const clearChatBtn = document.getElementById('clear-chat-btn');
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', () => this.clearConversation());
        }

        // Refresh system info button
        const refreshSystemBtn = document.getElementById('refresh-system-btn');
        if (refreshSystemBtn) {
            refreshSystemBtn.addEventListener('click', () => this.refreshSystemInfo());
        }

        // Settings controls
        const voiceVolumeSlider = document.getElementById('voice-volume');
        const wakeWordsToggle = document.getElementById('wake-words-enabled');
        
        if (voiceVolumeSlider) {
            voiceVolumeSlider.addEventListener('input', () => {
                this.updateVoiceVolume(voiceVolumeSlider.value);
            });
        }
        
        if (wakeWordsToggle) {
            wakeWordsToggle.addEventListener('change', () => {
                this.toggleWakeWords(wakeWordsToggle.checked);
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.target === document.body) {
                e.preventDefault();
                if (!this.isListening) {
                    this.startListening();
                }
            }
            if (e.key === 'Escape') {
                this.stopListening();
                this.closeSidebar();
            }
        });

        // Click outside sidebar to close
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const userProfileBtn = document.getElementById('user-profile-btn');
            
            if (this.sidebarOpen && sidebar && !sidebar.contains(e.target) && !userProfileBtn.contains(e.target)) {
                this.closeSidebar();
            }
        });
    }

    /**
     * Handle user login
     */
    async handleLogin() {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        if (!username || !password) {
            this.showError('Please fill in all fields');
            return;
        }

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Store user data and token
                this.currentUser = data.user;
                this.isAuthenticated = true;
                
                localStorage.setItem('orion_user', JSON.stringify(data.user));
                localStorage.setItem('orion_token', data.token || 'authenticated');
                
                this.showMainApp();
                this.showSuccess(`Welcome back, Commander ${data.user.username}!`);
            } else {
                this.showError(data.message || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Connection error. Please try again.');
        }
    }

    /**
     * Handle user registration
     */
    async handleRegister() {
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const fullName = document.getElementById('register-fullname').value;

        if (!username || !email || !password || !fullName) {
            this.showError('Please fill in all fields');
            return;
        }

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    email: email,
                    password: password,
                    full_name: fullName
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Auto-login after registration
                this.currentUser = data.user;
                this.isAuthenticated = true;
                
                localStorage.setItem('orion_user', JSON.stringify(data.user));
                localStorage.setItem('orion_token', data.token || 'authenticated');
                
                this.showMainApp();
                this.showSuccess(`Welcome to the command, ${data.user.username}!`);
            } else {
                this.showError(data.message || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showError('Connection error. Please try again.');
        }
    }

    /**
     * Handle user logout
     */
    async handleLogout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('orion_token')}`
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        }

        // Clear local storage and reset state
        localStorage.removeItem('orion_user');
        localStorage.removeItem('orion_token');
        this.currentUser = null;
        this.isAuthenticated = false;
        this.sidebarOpen = false;
        
        // Stop any ongoing processes
        this.stopListening();
        this.stopSpeaking();
        this.stopWakeWordDetection();
        
        this.showAuthScreen();
    }

    /**
     * Show authentication screen
     */
    showAuthScreen() {
        const authScreen = document.getElementById('auth-screen');
        const mainApp = document.getElementById('main-app');
        
        if (authScreen) authScreen.classList.remove('hidden');
        if (mainApp) mainApp.classList.add('hidden');
    }

    /**
     * Show main application
     */
    showMainApp() {
        const authScreen = document.getElementById('auth-screen');
        const mainApp = document.getElementById('main-app');
        
        if (authScreen) authScreen.classList.add('hidden');
        if (mainApp) mainApp.classList.remove('hidden');
        
        // Update user info in UI
        this.updateUserInfo();
        
        // Initialize voice system
        this.setupSpeechRecognition();
        this.setupWakeWordDetection();
        this.startWakeWordDetection();
        
        // Load initial data
        this.loadConversationHistory();
        this.refreshSystemInfo();
        this.refreshTimers();
        
        // Send welcome message
        setTimeout(() => {
            this.addMessage('Orion', `Greetings, Commander ${this.currentUser.username}! All systems are online and ready for your orders. How may I assist you today?`, 'orion');
        }, 1000);
    }

    /**
     * Update user information in the UI
     */
    updateUserInfo() {
        if (!this.currentUser) return;
        
        const navUsername = document.getElementById('nav-username');
        const sidebarUsername = document.getElementById('sidebar-username');
        const sidebarEmail = document.getElementById('sidebar-email');
        
        if (navUsername) navUsername.textContent = this.currentUser.username;
        if (sidebarUsername) sidebarUsername.textContent = this.currentUser.full_name || this.currentUser.username;
        if (sidebarEmail) sidebarEmail.textContent = this.currentUser.email;
    }

    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        if (this.sidebarOpen) {
            this.closeSidebar();
        } else {
            this.openSidebar();
        }
    }

    /**
     * Open sidebar
     */
    openSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.add('open');
            this.sidebarOpen = true;
        }
    }

    /**
     * Close sidebar
     */
    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
            this.sidebarOpen = false;
        }
    }

    /**
     * Change theme
     */
    changeTheme(theme) {
        const html = document.documentElement;
        html.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        
        // Update active theme button
        const themeButtons = document.querySelectorAll('.theme-btn');
        themeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
        
        // Save theme preference
        localStorage.setItem('orion_theme', theme);
    }

    /**
     * Load user settings
     */
    loadUserSettings() {
        const savedTheme = localStorage.getItem('orion_theme');
        if (savedTheme) {
            this.changeTheme(savedTheme);
        }
        
        const savedVolume = localStorage.getItem('orion_voice_volume');
        if (savedVolume) {
            const volumeSlider = document.getElementById('voice-volume');
            if (volumeSlider) {
                volumeSlider.value = savedVolume;
            }
        }
        
        const wakeWordsEnabled = localStorage.getItem('orion_wake_words') !== 'false';
        this.wakeWordEnabled = wakeWordsEnabled;
        const wakeWordsToggle = document.getElementById('wake-words-enabled');
        if (wakeWordsToggle) {
            wakeWordsToggle.checked = wakeWordsEnabled;
        }
    }

    /**
     * Update voice volume
     */
    updateVoiceVolume(volume) {
        localStorage.setItem('orion_voice_volume', volume);
        // Apply volume to speech synthesis if needed
    }

    /**
     * Toggle wake words
     */
    toggleWakeWords(enabled) {
        this.wakeWordEnabled = enabled;
        localStorage.setItem('orion_wake_words', enabled.toString());
        
        if (enabled) {
            this.startWakeWordDetection();
        } else {
            this.stopWakeWordDetection();
        }
    }

    /**
     * Setup Web Speech API for regular commands
     */
    setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.showError('Speech recognition not supported in this browser');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.onRecognitionStart();
        };

        this.recognition.onresult = (event) => {
            this.onRecognitionResult(event);
        };

        this.recognition.onerror = (event) => {
            this.onRecognitionError(event);
        };

        this.recognition.onend = () => {
            this.onRecognitionEnd();
        };
    }

    /**
     * Setup wake word detection
     */
    setupWakeWordDetection() {
        if (!this.wakeWordEnabled) {
            console.log('Wake word detection disabled by user settings');
            return;
        }
        
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('Web Speech API not supported in this browser');
            return;
        }

        console.log('Setting up wake word detection with words:', this.wakeWords);
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.wakeWordRecognition = new SpeechRecognition();
        
        this.wakeWordRecognition.continuous = true;
        this.wakeWordRecognition.interimResults = false;
        this.wakeWordRecognition.lang = 'en-US';
        
        this.wakeWordRecognition.onstart = () => {
            console.log('Wake word detection started successfully');
        };

        this.wakeWordRecognition.onresult = (event) => {
            this.onWakeWordResult(event);
        };

        this.wakeWordRecognition.onerror = (event) => {
            console.warn('Wake word detection error:', event.error);
            if (event.error === 'not-allowed') {
                console.error('Microphone access denied for wake word detection');
            }
        };

        this.wakeWordRecognition.onend = () => {
            console.log('Wake word detection ended, restarting...', this.wakeWordListening, this.wakeWordEnabled);
            if (this.wakeWordListening && this.wakeWordEnabled) {
                setTimeout(() => {
                    this.startWakeWordDetection();
                }, 100);
            }
        };
    }

    /**
     * Start wake word detection
     */
    startWakeWordDetection() {
        console.log('Attempting to start wake word detection...', {
            enabled: this.wakeWordEnabled,
            recognition: !!this.wakeWordRecognition,
            listening: this.wakeWordListening
        });
        
        if (!this.wakeWordEnabled) {
            console.log('Wake words disabled, not starting detection');
            return;
        }
        
        if (!this.wakeWordRecognition) {
            console.error('Wake word recognition not initialized');
            return;
        }
        
        try {
            if (!this.wakeWordListening) {
                this.wakeWordListening = true;
                this.wakeWordRecognition.start();
                console.log('✅ Wake word detection activated successfully');
                // Add a user alert to show it's working
                this.updateStatus('Wake word detection active - try saying "Orion"');
            } else {
                console.log('Wake word detection already listening');
            }
        } catch (error) {
            console.error('❌ Failed to start wake word detection:', error.name, error.message);
            if (error.name !== 'InvalidStateError') {
                this.updateStatus('Wake word detection failed - check browser permissions');
            }
        }
    }

    /**
     * Stop wake word detection
     */
    stopWakeWordDetection() {
        if (this.wakeWordRecognition && this.wakeWordListening) {
            this.wakeWordListening = false;
            try {
                this.wakeWordRecognition.stop();
            } catch (error) {
                console.warn('Error stopping wake word detection:', error);
            }
        }
    }

    /**
     * Handle wake word recognition results
     */
    onWakeWordResult(event) {
        const result = event.results[event.results.length - 1];
        if (result.isFinal) {
            const transcript = result[0].transcript.toLowerCase().trim();
            console.log('Wake word input:', transcript);
            
            for (const wakeWord of this.wakeWords) {
                if (transcript.includes(wakeWord)) {
                    console.log('Wake word detected:', wakeWord);
                    
                    const command = transcript.replace(wakeWord, '').trim();
                    
                    if (command) {
                        this.addMessage('You', transcript, 'user');
                        this.processWakeWordCommand(command);
                    } else {
                        this.addMessage('You', transcript, 'user');
                        this.speak('Yes, Commander? I am listening.');
                    }
                    break;
                }
            }
        }
    }

    /**
     * Start manual voice recognition
     */
    startListening() {
        if (!this.recognition) {
            this.showError('Speech recognition not available');
            return;
        }

        if (this.isListening || this.isSpeaking) {
            if (this.isSpeaking) {
                console.log('Orion is speaking, cannot start listening');
            }
            return;
        }

        this.stopWakeWordDetection();

        try {
            this.recognition.start();
        } catch (error) {
            console.error('Failed to start recognition:', error);
            this.showError('Failed to start voice recognition');
            this.startWakeWordDetection();
        }
    }

    /**
     * Stop voice recognition
     */
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }

    /**
     * Stop Orion from speaking
     */
    stopSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
            this.isSpeaking = false;
            this.updateStatus('Ready to listen');
            console.log('Orion stopped speaking by user request');
        }
    }

    /**
     * Handle recognition start
     */
    onRecognitionStart() {
        this.isListening = true;
        this.updateStatus('Listening...');
        
        const avatarRing = document.getElementById('avatar-ring');
        const voiceBtn = document.getElementById('voice-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (avatarRing) avatarRing.classList.add('active');
        if (voiceBtn) voiceBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'flex';
        
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
            this.isSpeaking = false;
        }
    }

    /**
     * Handle recognition results
     */
    onRecognitionResult(event) {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                transcript += event.results[i][0].transcript;
            }
        }

        if (transcript.trim()) {
            this.processVoiceCommand(transcript.trim());
        }
    }

    /**
     * Handle recognition errors
     */
    onRecognitionError(event) {
        console.error('Speech recognition error:', event.error);
        let errorMessage = 'Recognition error';
        
        switch (event.error) {
            case 'no-speech':
                errorMessage = 'No speech detected';
                break;
            case 'audio-capture':
                errorMessage = 'Microphone not available';
                break;
            case 'not-allowed':
                errorMessage = 'Microphone permission denied';
                break;
            case 'network':
                errorMessage = 'Network error';
                break;
        }
        
        this.showError(errorMessage);
        this.updateStatus(errorMessage);
    }

    /**
     * Handle recognition end
     */
    onRecognitionEnd() {
        this.isListening = false;
        
        const avatarRing = document.getElementById('avatar-ring');
        const voiceBtn = document.getElementById('voice-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (avatarRing) avatarRing.classList.remove('active');
        if (voiceBtn) voiceBtn.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
        
        this.updateStatus('Ready to listen');
        
        // Resume wake word detection
        setTimeout(() => {
            this.startWakeWordDetection();
        }, 500);
    }

    /**
     * Process voice command from manual activation
     */
    async processVoiceCommand(command) {
        console.log('Processing manual command:', command);
        this.addMessage('You', command, 'user');
        this.updateStatus('Processing...');

        try {
            const response = await this.sendToBackend(command);
            
            if (response && response.message) {
                this.addMessage('Orion', response.message, 'orion');
                this.speak(response.message);
            } else {
                const localResponse = this.processLocalCommand(command);
                this.addMessage('Orion', localResponse, 'orion');
                this.speak(localResponse);
            }
        } catch (error) {
            console.error('Error processing command:', error);
            const fallbackResponse = this.processLocalCommand(command);
            this.addMessage('Orion', fallbackResponse, 'orion');
            this.speak(fallbackResponse);
        }

        this.updateStatus('Ready to listen');
    }

    /**
     * Process command detected via wake word
     */
    async processWakeWordCommand(command) {
        console.log('Processing wake word command:', command);
        this.updateStatus('Processing wake word command...');

        try {
            const response = await this.sendToBackend(command);
            
            if (response && response.message) {
                this.addMessage('Orion', response.message, 'orion');
                this.speak(response.message);
            } else {
                const localResponse = this.processLocalCommand(command);
                this.addMessage('Orion', localResponse, 'orion');
                this.speak(localResponse);
            }
        } catch (error) {
            console.error('Error processing wake word command:', error);
            const fallbackResponse = this.processLocalCommand(command);
            this.addMessage('Orion', fallbackResponse, 'orion');
            this.speak(fallbackResponse);
        }

        this.updateStatus('Listening for wake words...');
    }

    /**
     * Send command to backend
     */
    async sendToBackend(command) {
        try {
            const response = await fetch('/api/process-command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('orion_token')}`
                },
                body: JSON.stringify({ command: command })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    return data;
                }
            }
        } catch (error) {
            console.error('Backend communication error:', error);
        }
        return null;
    }

    /**
     * Process commands locally (fallback)
     */
    processLocalCommand(command) {
        const cmd = command.toLowerCase();

        // Check for timer commands first before time queries
        if (cmd.includes('timer') || (cmd.includes('set') && (cmd.includes('timer') || cmd.includes('alarm')))) {
            return 'Timer and alarm functionality requires the full Orion system. Please use the desktop version for advanced scheduling operations, Commander.';
        }
        
        if (cmd.includes('time') && !cmd.includes('timer')) {
            const now = new Date();
            return `The current time is ${now.toLocaleTimeString()}, Commander.`;
        }
        
        if (cmd.includes('date')) {
            const now = new Date();
            return `Today is ${now.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            })}, Commander.`;
        }
        
        if (cmd.includes('hello') || cmd.includes('hi')) {
            const hour = new Date().getHours();
            let greeting = 'Greetings';
            if (hour < 12) greeting = 'Good morning';
            else if (hour < 17) greeting = 'Good afternoon';
            else greeting = 'Good evening';
            
            return `${greeting}, Commander! Orion reporting and ready for your orders.`;
        }
        
        if (cmd.includes('help')) {
            return 'I stand ready to assist with strategic operations, time queries, calculations, system monitoring, and comprehensive analysis. What is your mission, Commander?';
        }
        
        return 'Command received and understood, Commander. However, this requires the full Orion system capabilities. The desktop version offers more advanced tactical options.';
    }

    /**
     * Add message to conversation
     */
    addMessage(sender, message, type) {
        const messagesContainer = document.getElementById('conversation-messages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type === 'user' ? 'user-message' : 'orion-message'}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Store in conversation history
        this.conversationHistory.push({
            sender,
            message,
            type,
            timestamp: new Date().toISOString()
        });
    }

    /**
     * Clear conversation
     */
    clearConversation() {
        const messagesContainer = document.getElementById('conversation-messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
        }
        this.conversationHistory = [];
    }

    /**
     * Speak text using Speech Synthesis
     */
    speak(text) {
        if (!text) return;

        console.log('Orion speaking:', text);
        
        if (this.synthesis.speaking) {
            this.synthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure voice for Orion - prefer male, deep voice
        const voices = this.synthesis.getVoices();
        if (voices.length > 0) {
            const maleVoice = voices.find(voice => 
                voice.name.toLowerCase().includes('male') || 
                voice.name.toLowerCase().includes('david') ||
                voice.name.toLowerCase().includes('mark')
            );
            
            if (maleVoice) {
                utterance.voice = maleVoice;
            } else {
                // Fallback to first available voice
                utterance.voice = voices[0];
            }
        }
        
        utterance.rate = 0.9; // Slightly slower for authority
        utterance.pitch = 0.8; // Lower pitch for commanding presence
        utterance.volume = 0.9;
        
        utterance.onstart = () => {
            this.isSpeaking = true;
            this.updateStatus('Orion is speaking...');
        };
        
        utterance.onend = () => {
            this.isSpeaking = false;
            this.updateStatus('Ready to listen');
        };
        
        this.synthesis.speak(utterance);
    }

    /**
     * Update status indicator
     */
    updateStatus(status) {
        const statusText = document.getElementById('status-text');
        if (statusText) {
            statusText.textContent = status;
        }
    }

    /**
     * Load conversation history
     */
    async loadConversationHistory() {
        try {
            const response = await fetch('/api/chat/history', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('orion_token')}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.messages) {
                    // Load recent messages
                    data.messages.forEach(msg => {
                        this.addMessage(msg.sender, msg.content, msg.sender === 'user' ? 'user' : 'orion');
                    });
                }
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
        }
    }

    /**
     * Refresh system information
     */
    async refreshSystemInfo() {
        try {
            const response = await fetch('/api/system-info', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('orion_token')}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateSystemDisplay(data);
            }
        } catch (error) {
            console.error('Error refreshing system info:', error);
        }
    }

    /**
     * Update system information display
     */
    updateSystemDisplay(systemData) {
        const updates = {
            'audio-status': systemData.audio_status || 'Ready',
            'ai-status': systemData.ai_status || 'Online',
            'memory-usage': systemData.memory_usage || '--',
            'cpu-usage': systemData.cpu_usage || '--',
            'battery-status': systemData.battery_status || '--',
            'network-status': systemData.network_status || 'Connected'
        };

        Object.entries(updates).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    /**
     * Refresh timers display
     */
    async refreshTimers() {
        try {
            const response = await fetch('/api/timers', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('orion_token')}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateTimersDisplay(data.timers || []);
            }
        } catch (error) {
            console.error('Error refreshing timers:', error);
        }
    }

    /**
     * Update timers display
     */
    updateTimersDisplay(timers) {
        const timersEmpty = document.getElementById('timers-empty');
        const timersList = document.getElementById('timers-list');
        
        if (timers.length === 0) {
            if (timersEmpty) timersEmpty.style.display = 'block';
            if (timersList) timersList.innerHTML = '';
        } else {
            if (timersEmpty) timersEmpty.style.display = 'none';
            if (timersList) {
                timersList.innerHTML = '';
                timers.forEach(timer => {
                    const timerElement = this.createTimerElement(timer);
                    timersList.appendChild(timerElement);
                });
            }
        }
    }

    /**
     * Create timer element
     */
    createTimerElement(timer) {
        const timerDiv = document.createElement('div');
        timerDiv.className = 'timer-item';
        timerDiv.innerHTML = `
            <div class="timer-header">
                <span class="timer-name">${timer.name}</span>
                <span class="timer-time">${timer.remaining}</span>
            </div>
            <div class="timer-controls">
                <button class="timer-btn" onclick="pauseTimer('${timer.id}')">Pause</button>
                <button class="timer-btn" onclick="cancelTimer('${timer.id}')">Cancel</button>
            </div>
        `;
        return timerDiv;
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log('Success:', message);
        // Could implement toast notifications here
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('Error:', message);
        // Could implement toast notifications here
        alert(message); // Simple fallback for now
    }
}

// Initialize the application
let orionApp;
document.addEventListener('DOMContentLoaded', () => {
    orionApp = new OrionVoiceAssistant();
});

// Global functions for timer controls
function pauseTimer(timerId) {
    // Implementation for pausing timer
    console.log('Pausing timer:', timerId);
}

function cancelTimer(timerId) {
    // Implementation for canceling timer
    console.log('Canceling timer:', timerId);
}