/**
 * Orion Voice Assistant - Complete Frontend System
 * Handles authentication, 3-part layout, themes, and voice interaction
 */

class OrionAnalytics {
    constructor() {
        this.sessionStart = Date.now();
        this.events = [];
        this.userId = null;
        this.sessionId = this.generateSessionId();
        
        // Track session start
        this.trackEvent('session_start', {
            timestamp: this.sessionStart,
            user_agent: navigator.userAgent,
            screen_resolution: `${screen.width}x${screen.height}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    setUser(userId, username) {
        this.userId = userId;
        this.trackEvent('user_identified', {
            user_id: userId,
            username: username
        });
    }
    
    trackEvent(eventName, properties = {}) {
        const event = {
            event_name: eventName,
            timestamp: Date.now(),
            session_id: this.sessionId,
            user_id: this.userId,
            properties: {
                ...properties,
                page_url: window.location.href,
                referrer: document.referrer
            }
        };
        
        this.events.push(event);
        
        // Send to Google Analytics if available
        if (typeof gtag !== 'undefined') {
            gtag('event', eventName, {
                event_category: 'orion_vva',
                event_label: properties.label || eventName,
                value: properties.value || 1,
                custom_parameter_1: properties.command_type || null,
                custom_parameter_2: properties.timer_duration || null
            });
        }
        
        // Send to backend for storage
        this.sendToBackend(event);
        
        console.log('📊 Analytics:', eventName, properties);
    }
    
    // Voice-specific tracking methods
    trackVoiceCommand(command, intent, success, processingTime) {
        this.trackEvent('voice_command', {
            command: command,
            intent: intent,
            success: success,
            processing_time: processingTime,
            command_length: command.length
        });
    }
    
    trackTimerCreated(duration, description) {
        this.trackEvent('timer_created', {
            timer_duration: duration,
            timer_description: description,
            label: `${duration}s timer`
        });
    }
    
    trackTimerCompleted(duration, description) {
        this.trackEvent('timer_completed', {
            timer_duration: duration,
            timer_description: description,
            label: `${duration}s timer completed`
        });
    }
    
    trackThemeChange(oldTheme, newTheme) {
        this.trackEvent('theme_changed', {
            old_theme: oldTheme,
            new_theme: newTheme,
            label: `${oldTheme} to ${newTheme}`
        });
    }
    
    trackUserAuthentication(action, success, method = 'form') {
        this.trackEvent('user_auth', {
            auth_action: action, // 'login' or 'register'
            auth_success: success,
            auth_method: method,
            label: `${action}_${success ? 'success' : 'failed'}`
        });
    }
    
    trackError(errorType, errorMessage, context) {
        this.trackEvent('error_occurred', {
            error_type: errorType,
            error_message: errorMessage,
            error_context: context,
            label: `${errorType}: ${errorMessage}`
        });
    }
    
    trackPageView(pageName) {
        this.trackEvent('page_view', {
            page_name: pageName,
            label: pageName
        });
    }
    
    async sendToBackend(event) {
        try {
            await fetch('/api/analytics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('orion_token') || ''}`
                },
                body: JSON.stringify(event)
            });
        } catch (error) {
            console.warn('Failed to send analytics to backend:', error);
        }
    }
    
    // Get session summary
    getSessionSummary() {
        const sessionDuration = Date.now() - this.sessionStart;
        const eventCounts = {};
        
        this.events.forEach(event => {
            eventCounts[event.event_name] = (eventCounts[event.event_name] || 0) + 1;
        });
        
        return {
            session_id: this.sessionId,
            user_id: this.userId,
            session_duration: sessionDuration,
            total_events: this.events.length,
            event_breakdown: eventCounts,
            started_at: this.sessionStart,
            ended_at: Date.now()
        };
    }
}

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
        
        // Mission/conversation management
        this.missions = [];
        this.currentMissionId = 'default';
        this.missionCounter = 1;
        
        // Sidebar state
        this.sidebarOpen = false;
        
        // Analytics tracking
        this.analytics = new OrionAnalytics();
        
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
        
        // Mission switcher buttons
        const newMissionBtn = document.getElementById('new-mission-btn');
        if (newMissionBtn) {
            newMissionBtn.addEventListener('click', () => this.createNewMission());
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
                
                // Track successful login
                this.analytics.setUser(data.user.id || data.user.username, data.user.username);
                this.analytics.trackUserAuthentication('login', true);
                
                this.showMainApp();
                this.showSuccess(`Welcome back, Commander ${data.user.username}!`);
                
                // Refresh page after short delay for clean state
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.analytics.trackUserAuthentication('login', false);
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
                
                // Track successful registration
                this.analytics.setUser(data.user.id || data.user.username, data.user.username);
                this.analytics.trackUserAuthentication('register', true);
                
                this.showMainApp();
                this.showSuccess(`Welcome to the command, ${data.user.username}!`);
                
                // Refresh page after short delay for clean state
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.analytics.trackUserAuthentication('register', false);
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
        
        // Refresh page for clean logout
        setTimeout(() => {
            window.location.reload();
        }, 500);
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
        
        // Initialize mission switcher
        this.updateMissionsDisplay();
        
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
        const oldTheme = this.currentTheme;
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
        
        // Track theme change
        this.analytics.trackThemeChange(oldTheme, theme);
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
            return this.handleTimerCommand(cmd);
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
        
        // Configure voice for Orion - Optimus Prime inspired leadership voice
        const voices = this.synthesis.getVoices();
        if (voices.length > 0) {
            // Prefer deep, authoritative male voices like Optimus Prime
            const primeVoice = voices.find(voice => {
                const name = voice.name.toLowerCase();
                return (
                    name.includes('daniel') ||     // Deep British voice
                    name.includes('alex') ||       // Deep voice option
                    name.includes('fred') ||       // Another deep option
                    name.includes('male') ||
                    name.includes('david') ||
                    name.includes('mark') ||
                    name.includes('ryan') ||       // Natural deep voice
                    (name.includes('microsoft') && name.includes('mark'))
                );
            });
            
            if (primeVoice) {
                utterance.voice = primeVoice;
                console.log(`Using Orion voice: ${primeVoice.name}`);
            } else {
                // Fallback to first available voice
                utterance.voice = voices[0];
                console.log(`Fallback voice: ${voices[0].name}`);
            }
        }
        
        // Optimus Prime vocal characteristics:
        utterance.rate = 0.85;    // Measured, thoughtful speech
        utterance.pitch = 0.7;    // Deep, commanding tone
        utterance.volume = 1.0;   // Strong, clear projection
        
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
     * Create timer element with analog clock
     */
    createTimerElement(timer) {
        const timerDiv = document.createElement('div');
        timerDiv.className = 'timer-item';
        timerDiv.id = timer.id;
        
        const endTime = new Date(timer.endTime);
        const formattedEndTime = endTime.toLocaleTimeString();
        
        timerDiv.innerHTML = `
            <div class="timer-content">
                <div class="analog-clock">
                    <div class="clock-face">
                        <div class="clock-numbers">
                            <div class="clock-number" style="--i:1"><span>1</span></div>
                            <div class="clock-number" style="--i:2"><span>2</span></div>
                            <div class="clock-number" style="--i:3"><span>3</span></div>
                            <div class="clock-number" style="--i:4"><span>4</span></div>
                            <div class="clock-number" style="--i:5"><span>5</span></div>
                            <div class="clock-number" style="--i:6"><span>6</span></div>
                            <div class="clock-number" style="--i:7"><span>7</span></div>
                            <div class="clock-number" style="--i:8"><span>8</span></div>
                            <div class="clock-number" style="--i:9"><span>9</span></div>
                            <div class="clock-number" style="--i:10"><span>10</span></div>
                            <div class="clock-number" style="--i:11"><span>11</span></div>
                            <div class="clock-number" style="--i:12"><span>12</span></div>
                        </div>
                        <div class="clock-hand"></div>
                        <div class="clock-center"></div>
                    </div>
                </div>
                <div class="timer-info">
                    <div class="timer-description">${timer.description}</div>
                    <div class="digital-time">${this.formatTime(timer.remaining)}</div>
                    <div class="completion-time">Completes at ${formattedEndTime}</div>
                </div>
            </div>
            <div class="timer-controls">
                <button class="timer-btn cancel-btn" onclick="orionApp.cancelTimer('${timer.id}')">
                    <i class="fas fa-times"></i> Cancel
                </button>
            </div>
        `;
        
        return timerDiv;
    }

    /**
     * Handle timer commands from voice input
     */
    handleTimerCommand(command) {
        const cmd = command.toLowerCase();
        
        // Parse timer duration from command
        const timePattern = /(\d+)\s*(second|seconds|minute|minutes|min|mins|hour|hours|hr|hrs)s?/g;
        const matches = [...cmd.matchAll(timePattern)];
        
        if (matches.length === 0) {
            return "I couldn't understand the timer duration, Commander. Please specify a time like 'set timer for 5 minutes' or '30 seconds'.";
        }
        
        let totalSeconds = 0;
        let durationText = '';
        
        matches.forEach(match => {
            const value = parseInt(match[1]);
            const unit = match[2].toLowerCase();
            
            if (unit.includes('second')) {
                totalSeconds += value;
                durationText += `${value} second${value !== 1 ? 's' : ''} `;
            } else if (unit.includes('minute') || unit.includes('min')) {
                totalSeconds += value * 60;
                durationText += `${value} minute${value !== 1 ? 's' : ''} `;
            } else if (unit.includes('hour') || unit.includes('hr')) {
                totalSeconds += value * 3600;
                durationText += `${value} hour${value !== 1 ? 's' : ''} `;
            }
        });
        
        if (totalSeconds === 0) {
            return "Timer duration must be greater than zero, Commander.";
        }
        
        // Create the timer
        const timer = this.createTimer(totalSeconds, durationText.trim());
        this.startTimer(timer);
        
        // Track timer creation
        this.analytics.trackTimerCreated(totalSeconds, durationText.trim());
        
        const endTime = new Date(Date.now() + totalSeconds * 1000);
        return `Timer set for ${durationText.trim()}, Commander. It will complete at ${endTime.toLocaleTimeString()}.`;
    }
    
    /**
     * Create a new timer object
     */
    createTimer(seconds, description) {
        const timer = {
            id: `timer_${Date.now()}`,
            duration: seconds,
            remaining: seconds,
            description: description,
            startTime: Date.now(),
            endTime: Date.now() + (seconds * 1000),
            active: true,
            interval: null
        };
        
        this.timers.push(timer);
        return timer;
    }
    
    /**
     * Start a timer with visual display
     */
    startTimer(timer) {
        // Update the timers display
        this.updateTimersDisplay(this.timers);
        
        // Start the countdown interval
        timer.interval = setInterval(() => {
            timer.remaining--;
            
            if (timer.remaining <= 0) {
                this.completeTimer(timer);
            } else {
                this.updateTimerDisplay(timer);
            }
        }, 1000);
    }
    
    /**
     * Complete a timer and notify user
     */
    completeTimer(timer) {
        // Clear the interval
        if (timer.interval) {
            clearInterval(timer.interval);
        }
        
        // Remove from active timers
        this.timers = this.timers.filter(t => t.id !== timer.id);
        
        // Update display
        this.updateTimersDisplay(this.timers);
        
        // Track timer completion
        this.analytics.trackTimerCompleted(timer.duration, timer.description);
        
        // Notify user
        const message = `Timer complete, Commander! Your ${timer.description} timer has finished.`;
        this.addMessage('Orion', message, 'orion');
        this.speak(message);
        
        // Play notification sound (browser notification)
        this.playNotification();
        
        // Show browser notification if permitted
        this.showBrowserNotification('Timer Complete', `Your ${timer.description} timer has finished!`);
    }
    
    /**
     * Update individual timer display
     */
    updateTimerDisplay(timer) {
        const timerElement = document.getElementById(timer.id);
        if (timerElement) {
            const digitalTime = timerElement.querySelector('.digital-time');
            const analogClock = timerElement.querySelector('.analog-clock');
            
            if (digitalTime) {
                digitalTime.textContent = this.formatTime(timer.remaining);
            }
            
            if (analogClock) {
                this.updateAnalogClock(analogClock, timer);
            }
        }
    }
    
    /**
     * Update analog clock hands based on timer progress
     */
    updateAnalogClock(clockElement, timer) {
        const progress = (timer.duration - timer.remaining) / timer.duration;
        const angle = progress * 360;
        
        const hand = clockElement.querySelector('.clock-hand');
        if (hand) {
            hand.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
        }
    }
    
    /**
     * Format seconds into readable time
     */
    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    /**
     * Play notification sound
     */
    playNotification() {
        // Create a brief notification sound using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A note
            oscillator.frequency.setValueAtTime(1108, audioContext.currentTime + 0.1); // C# note
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (error) {
            console.log('Audio notification not available');
        }
    }
    
    /**
     * Show browser notification
     */
    showBrowserNotification(title, message) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/static/orion-icon.png' // Optional icon
            });
        } else if ('Notification' in window && Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification(title, {
                        body: message,
                        icon: '/static/orion-icon.png'
                    });
                }
            });
        }
    }
    
    /**
     * Cancel a timer
     */
    cancelTimer(timerId) {
        const timer = this.timers.find(t => t.id === timerId);
        if (timer) {
            if (timer.interval) {
                clearInterval(timer.interval);
            }
            this.timers = this.timers.filter(t => t.id !== timerId);
            this.updateTimersDisplay(this.timers);
            
            this.addMessage('Orion', `Timer for ${timer.description} has been cancelled, Commander.`, 'orion');
        }
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
        
        // Track error analytics
        this.analytics.trackError('user_error', message, 'showError');
        
        // Could implement toast notifications here
        alert(message); // Simple fallback for now
    }
    
    // ==================== MISSION SWITCHER METHODS ====================
    
    /**
     * Create a new mission/conversation
     */
    createNewMission() {
        this.missionCounter++;
        const mission = {
            id: `mission_${Date.now()}`,
            title: `Mission ${this.missionCounter}`,
            description: 'New conversation',
            messages: [],
            createdAt: Date.now(),
            lastActivity: Date.now()
        };
        
        this.missions.push(mission);
        this.switchToMission(mission.id);
        this.updateMissionsDisplay();
        
        // Track analytics
        this.analytics.trackEvent('mission_created', {
            mission_id: mission.id,
            mission_count: this.missions.length
        });
    }
    
    /**
     * Switch to a specific mission
     */
    switchToMission(missionId) {
        // Save current conversation to current mission
        if (this.currentMissionId && this.currentMissionId !== missionId) {
            const currentMission = this.missions.find(m => m.id === this.currentMissionId);
            if (currentMission) {
                currentMission.messages = [...this.conversationHistory];
                currentMission.lastActivity = Date.now();
            }
        }
        
        // Switch to new mission
        this.currentMissionId = missionId;
        const newMission = this.missions.find(m => m.id === missionId);
        
        if (newMission) {
            // Load conversation history for this mission
            this.conversationHistory = [...newMission.messages];
            this.displayConversationHistory();
            
            // Update UI
            const currentMissionName = document.getElementById('current-mission-name');
            if (currentMissionName) {
                currentMissionName.textContent = newMission.title;
            }
        } else {
            // Default mission
            this.conversationHistory = [];
            this.displayConversationHistory();
        }
        
        this.updateMissionsDisplay();
        
        // Track analytics
        this.analytics.trackEvent('mission_switched', {
            from_mission: this.currentMissionId,
            to_mission: missionId
        });
    }
    
    /**
     * Delete a mission
     */
    deleteMission(missionId) {
        if (missionId === 'default') return; // Can't delete default mission
        
        this.missions = this.missions.filter(m => m.id !== missionId);
        
        // If we're deleting the current mission, switch to default
        if (this.currentMissionId === missionId) {
            this.switchToMission('default');
        }
        
        this.updateMissionsDisplay();
        
        // Track analytics
        this.analytics.trackEvent('mission_deleted', {
            mission_id: missionId,
            remaining_missions: this.missions.length
        });
    }
    
    /**
     * Update the missions display in the UI
     */
    updateMissionsDisplay() {
        const missionsList = document.getElementById('missions-list');
        if (!missionsList) return;
        
        // Clear existing missions
        missionsList.innerHTML = '';
        
        // Add default mission
        const defaultMission = {
            id: 'default',
            title: 'Primary Mission',
            description: 'General assistance and commands',
            lastActivity: Date.now()
        };
        
        this.renderMissionItem(defaultMission, missionsList);
        
        // Add user-created missions
        this.missions.forEach(mission => {
            this.renderMissionItem(mission, missionsList);
        });
    }
    
    /**
     * Render a single mission item
     */
    renderMissionItem(mission, container) {
        const missionElement = document.createElement('div');
        missionElement.className = `mission-item ${mission.id === this.currentMissionId ? 'active' : ''}`;
        missionElement.dataset.missionId = mission.id;
        
        const icons = {
            'default': 'fas fa-rocket',
            'mission': 'fas fa-comments'
        };
        
        const icon = mission.id === 'default' ? icons.default : icons.mission;
        const preview = mission.description || (mission.messages && mission.messages.length > 0 ? 
            mission.messages[mission.messages.length - 1].text.substring(0, 40) + '...' : 
            'No messages yet');
        
        missionElement.innerHTML = `
            <div class="mission-icon">
                <i class="${icon}"></i>
            </div>
            <div class="mission-info">
                <span class="mission-title">${mission.title}</span>
                <span class="mission-preview">${preview}</span>
            </div>
            <div class="mission-actions">
                ${mission.id !== 'default' ? `
                    <button class="mission-delete-btn" title="Delete mission" onclick="orionApp.deleteMission('${mission.id}')">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                ` : ''}
            </div>
        `;
        
        // Add click handler for switching
        missionElement.addEventListener('click', (e) => {
            if (!e.target.closest('.mission-actions')) {
                this.switchToMission(mission.id);
            }
        });
        
        container.appendChild(missionElement);
    }
    
    // ==================== ENHANCED SYSTEM MONITORING ====================
    
    /**
     * Enhanced system info refresh with real metrics
     */
    async refreshSystemInfo() {
        const startTime = Date.now();
        
        try {
            // Get system metrics from backend
            const response = await fetch('/api/system/stats', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('orion_token')}`
                }
            });
            
            const responseTime = Date.now() - startTime;
            
            if (response.ok) {
                const stats = await response.json();
                this.updateSystemDisplay({
                    ...stats,
                    response_time: responseTime,
                    network_status: 'Connected'
                });
            } else {
                // Fallback to client-side metrics
                this.updateSystemDisplay({
                    audio_status: this.recognition ? 'Ready' : 'Not Available',
                    ai_status: 'Connected',
                    memory_usage: this.getMemoryUsage(),
                    response_time: responseTime,
                    database_status: 'Checking...',
                    network_status: 'Connected'
                });
            }
        } catch (error) {
            console.error('Failed to fetch system stats:', error);
            // Fallback metrics
            this.updateSystemDisplay({
                audio_status: this.recognition ? 'Ready' : 'Not Available',
                ai_status: 'Offline',
                memory_usage: this.getMemoryUsage(),
                response_time: Date.now() - startTime,
                database_status: 'Offline',
                network_status: 'Connected'
            });
        }
    }
    
    /**
     * Get client-side memory usage estimate
     */
    getMemoryUsage() {
        if (performance.memory) {
            const usedMB = Math.round(performance.memory.usedJSHeapSize / 1048576);
            const totalMB = Math.round(performance.memory.totalJSHeapSize / 1048576);
            return `${usedMB}/${totalMB} MB`;
        }
        return 'N/A';
    }
    
    /**
     * Update system display with real metrics
     */
    updateSystemDisplay(stats) {
        const updates = {
            'audio-status': stats.audio_status || 'Ready',
            'ai-status': stats.ai_status || 'Connected',
            'memory-usage': stats.memory_usage || 'N/A',
            'response-time': stats.response_time ? `${stats.response_time}ms` : '--',
            'database-status': stats.database_status || 'Connected',
            'network-status': stats.network_status || 'Connected'
        };
        
        Object.entries(updates).forEach(([elementId, value]) => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value;
                
                // Add status colors
                element.classList.remove('status-good', 'status-warning', 'status-error');
                if (value.includes('Connected') || value.includes('Ready') || value.includes('Online')) {
                    element.classList.add('status-good');
                } else if (value.includes('Offline') || value.includes('Error')) {
                    element.classList.add('status-error');
                } else if (value.includes('Warning') || value.includes('Checking')) {
                    element.classList.add('status-warning');
                }
            }
        });
        
        this.systemInfo = stats;
    }
}

// Initialize the application
let orionApp;
document.addEventListener('DOMContentLoaded', () => {
    orionApp = new OrionVoiceAssistant();
});

// Global error tracking
window.addEventListener('error', (event) => {
    if (orionApp && orionApp.analytics) {
        orionApp.analytics.trackError('javascript_error', event.message, {
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error ? event.error.stack : null
        });
    }
});

// Track unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    if (orionApp && orionApp.analytics) {
        orionApp.analytics.trackError('unhandled_promise_rejection', event.reason, {
            promise: event.promise
        });
    }
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