# aurora.py
"""
Aurora Voice Assistant - Full updated version
Features:
- Local hardcoded handlers for time/date/math/system/weather/timers/alarms/stopwatch
- spaCy-enhanced NLP (if available)
- Groq fallback (only used when local handlers don't match)
- APScheduler with SQLite jobstore for persistent timers/alarms
- Threading-based Timer fallback if APScheduler fails
- Stopwatch state persisted to disk so stopwatch keeps running across "exit" (while process alive)
- Clear logging, graceful fallbacks, and helpful messages
"""

import os
import re
import time
import json
import math
import random
import logging
import subprocess
import threading
import datetime as dt
from typing import Optional, Dict, List

import requests
from dotenv import load_dotenv

# Speech / TTS / recognition
import speech_recognition as sr
import pyttsx3 as pt

# System info
import psutil

# Optional spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

# Groq SDK
try:
    from groq import Groq
    GROQ_SDK_AVAILABLE = True
except Exception:
    GROQ_SDK_AVAILABLE = False

# APScheduler for persistent scheduling
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    APSCHEDULER_AVAILABLE = True
except Exception:
    APSCHEDULER_AVAILABLE = False

# Desktop notifications (optional)
try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except Exception:
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        NOTIFICATIONS_AVAILABLE = True
    except Exception:
        NOTIFICATIONS_AVAILABLE = False

# Load environment
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("orion_assistant.log"), logging.StreamHandler()]
)

# ---------------------------
# Utility
# ---------------------------
def safe_json_write(path: str, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.getLogger("Orion").error(f"Failed writing JSON to {path}: {e}")

def safe_json_read(path: str, default=None):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logging.getLogger("Orion").error(f"Failed reading JSON {path}: {e}")
    return default


# ---------------------------
# Groq Handler (safe)
# ---------------------------
class GroqAIHandler:
    def __init__(self, api_key: Optional[str]):
        self.logger = logging.getLogger("GroqHandler")
        self.client = None
        self.conversation_context = []

        if not api_key:
            self.logger.warning("GROQ_API_KEY not found in environment.")
            return

        if not GROQ_SDK_AVAILABLE:
            self.logger.warning("Groq SDK not installed (pip install groq). Groq disabled.")
            return

        try:
            self.client = Groq(api_key=api_key)
            # quick connectivity test (list models) - handle gracefully
            try:
                _ = self.client.models.list()
                self.logger.info("Groq API connection OK.")
            except Exception as e:
                self.logger.warning(f"Groq client initialized but connectivity test failed: {e}")
                # keep client, but calls will show errors with helpful message
        except Exception as e:
            self.logger.error(f"Failed to initialize Groq client: {e}")
            self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def get_response(self, query: str, context: str = "") -> str:
        if not self.client:
            return "Groq AI is not available. Please check API key or network."

        # Try a simple retry pattern
        attempts = 2
        last_error = None
        for attempt in range(attempts):
            try:
                system_message = (
                    "You are Orion, a commanding and strategic voice assistant with the authority of a military commander. "
                    "You address users as 'Commander' and provide clear, decisive responses suitable for text-to-speech. "
                    "Be helpful, knowledgeable, and maintain a tone of respectful authority and strategic thinking."
                    f" Current context: {context}"
                )
                messages = [{"role": "system", "content": system_message}]
                for ctx in self.conversation_context[-6:]:
                    messages.append(ctx)
                messages.append({"role": "user", "content": query})

                response = self.client.chat.completions.create(
                    messages=messages,
                    model="llama-3.3-70b-versatile",
                    temperature=0.7,
                    max_tokens=300
                )
                ai_response = response.choices[0].message.content.strip()
                # update context
                self.conversation_context.append({"role": "user", "content": query})
                self.conversation_context.append({"role": "assistant", "content": ai_response})
                if len(self.conversation_context) > 12:
                    self.conversation_context = self.conversation_context[-12:]
                return ai_response
            except Exception as e:
                last_error = e
                self.logger.warning(f"Groq attempt {attempt+1} failed: {e}")
                time.sleep(0.7)
        return "I'm having trouble reaching Groq right now - please try again"


# ---------------------------
# APScheduler + TimerManager
# ---------------------------
class SchedulerWrapper:
    """
    Wraps APScheduler with SQLite jobstore. Starts if available.
    """
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.available = False
        self.scheduler = None
        if not APSCHEDULER_AVAILABLE:
            self.logger.warning("APScheduler not installed; persistent scheduling disabled.")
            return

        try:
            jobstore_url = "sqlite:///orion_scheduler_jobs.sqlite"
            jobstores = {"default": SQLAlchemyJobStore(url=jobstore_url)}
            self.scheduler = BackgroundScheduler(jobstores=jobstores)
            # Start scheduler as daemon threads
            self.scheduler.start()
            self.available = True
            self.logger.info("APScheduler started with SQLite jobstore.")
        except Exception as e:
            self.logger.error(f"Failed to start APScheduler: {e}")
            self.scheduler = None
            self.available = False

    def shutdown(self, wait=True):
        if self.scheduler:
            try:
                self.scheduler.shutdown(wait=wait)
            except Exception as e:
                self.logger.error(f"Error shutting down scheduler: {e}")

    def add_date_job(self, func, run_date: dt.datetime, args=None, kwargs=None, id: Optional[str] = None, name: Optional[str] = None):
        if not self.available or not self.scheduler:
            raise RuntimeError("Scheduler not available")
        return self.scheduler.add_job(func, 'date', run_date=run_date, args=args or [], kwargs=kwargs or {}, id=id, name=name)


class TimerManagerFallback:
    """Your old thread-based timers kept as fallback if APScheduler isn't available."""
    def __init__(self, assistant_logger, notify_func):
        self.logger = assistant_logger
        self.notify = notify_func
        self.timers = {}
        self.counter = 0

    def set_timer(self, duration_seconds: int, name: str = None) -> int:
        self.counter += 1
        tid = self.counter
        if not name:
            name = f"Timer {tid}"
        thread = threading.Thread(target=self._thread_worker, args=(tid, duration_seconds, name), daemon=True)
        self.timers[tid] = {
            "name": name,
            "duration": duration_seconds,
            "start_time": time.time(),
            "thread": thread
        }
        thread.start()
        self.logger.info(f"Fallback timer {tid} set for {duration_seconds} sec")
        return tid

    def _thread_worker(self, tid, duration, name):
        time.sleep(duration)
        if tid in self.timers:
            message = f"Timer '{name}' finished (fallback)."
            try:
                self.notify(message)
            except Exception as e:
                self.logger.error(f"Failed to notify for fallback timer {tid}: {e}")
            del self.timers[tid]

    def cancel_timer(self, tid):
        # no direct thread cancel; mark as removed to ignore when wakes
        if tid in self.timers:
            del self.timers[tid]
            return True
        return False

    def list_timers(self):
        out = []
        for tid, t in self.timers.items():
            elapsed = time.time() - t["start_time"]
            remaining = t["duration"] - elapsed
            out.append({"id": tid, "name": t["name"], "remaining": remaining})
        return out


class TimerManager:
    """
    Primary timer manager that prefers APScheduler persistent jobs.
    Falls back to TimerManagerFallback if scheduling fails.
    """
    def __init__(self, assistant):
        self.assistant = assistant
        self.logger = assistant.logger
        self.scheduler = assistant.scheduler_wrapper  # scheduler wrapper
        self.fallback = TimerManagerFallback(self.logger, self._notify)
        self.timers = {}  # map integer id -> APS job id or fallback id
        self.counter = 0
        self.lock = threading.Lock()

    def _notify(self, message: str):
        # show notification and speak
        try:
            if NOTIFICATIONS_AVAILABLE:
                if 'notification' in globals():
                    notification.notify(title="Orion Timer", message=message, timeout=8)
                elif 'toaster' in globals():
                    toaster.show_toast("Orion Timer", message, duration=6)
            self.assistant.speak(message)
        except Exception as e:
            self.logger.error(f"Notification failure: {e}")
            # speak fallback
            try:
                self.assistant.speak(message)
            except Exception:
                pass

    def set_timer(self, duration_seconds: int, name: Optional[str] = None) -> int:
        with self.lock:
            self.counter += 1
            t_id = self.counter
        if not name:
            name = f"Timer {t_id}"

        # try scheduler
        if self.scheduler and self.scheduler.available:
            try:
                run_at = dt.datetime.now() + dt.timedelta(seconds=duration_seconds)
                job_id = f"timer_{t_id}_{int(time.time())}"
                self.scheduler.add_date_job(self._scheduler_job_wrapper, run_date=run_at, args=[t_id, name], id=job_id, name=name)
                self.timers[t_id] = {"type": "aps", "job_id": job_id, "name": name, "run_at": run_at.isoformat()}
                self.logger.info(f"Scheduled APS timer {t_id} at {run_at.isoformat()}")
                return t_id
            except Exception as e:
                self.logger.error(f"APScheduler set_timer failed: {e}; falling back to threads.")

        # fallback
        fallback_id = self.fallback.set_timer(duration_seconds, name)
        self.timers[t_id] = {"type": "fallback", "fallback_id": fallback_id, "name": name}
        return t_id

    def _scheduler_job_wrapper(self, t_id: int, name: str):
        # Called inside scheduler worker when timer expires
        message = f"Timer '{name}' is complete!"
        self._notify(message)
        # remove from mapping if present
        if t_id in self.timers:
            try:
                del self.timers[t_id]
            except Exception:
                pass

    def set_alarm(self, target_time: dt.time, name: Optional[str] = None) -> int:
        # compute next occurrence
        now = dt.datetime.now()
        target_datetime = dt.datetime.combine(now.date(), target_time)
        if target_datetime <= now:
            target_datetime += dt.timedelta(days=1)
        duration_seconds = int((target_datetime - now).total_seconds())
        if not name:
            name = f"Alarm for {target_time.strftime('%I:%M %p')}"
        return self.set_timer(duration_seconds, name)

    def list_timers(self):
        out = []
        # APS timers: compute remaining by run_at
        for t_id, meta in list(self.timers.items()):
            try:
                if meta.get("type") == "aps":
                    run_at = dt.datetime.fromisoformat(meta["run_at"])
                    remaining = (run_at - dt.datetime.now()).total_seconds()
                    if remaining > 0:
                        out.append({"id": t_id, "name": meta["name"], "remaining": remaining})
                else:
                    # fallback
                    fl = self.fallback.list_timers()
                    for f in fl:
                        out.append(f)
            except Exception:
                continue
        return out

    def cancel_timer(self, t_id: int) -> bool:
        meta = self.timers.get(t_id)
        if not meta:
            return False
        if meta.get("type") == "aps":
            try:
                job_id = meta["job_id"]
                if self.scheduler and self.scheduler.available:
                    self.scheduler.scheduler.remove_job(job_id)
                del self.timers[t_id]
                return True
            except Exception as e:
                self.logger.error(f"Failed to remove APS job {job_id}: {e}")
                return False
        else:
            # fallback cancel
            try:
                if self.fallback.cancel_timer(meta["fallback_id"]):
                    del self.timers[t_id]
                    return True
            except Exception as e:
                self.logger.error(f"Failed to cancel fallback timer: {e}")
            return False


# ---------------------------
# Stopwatch with persistence
# ---------------------------
class StopwatchManager:
    """
    Stopwatch that persists its running start time and elapsed time to disk.
    If the assistant 'exits' (stops listening) but process is alive, stopwatch will continue.
    On restart, it will restore previous state.
    """
    STATE_FILE = "stopwatch_state.json"

    def __init__(self, assistant):
        self.logger = assistant.logger
        self.running = False
        self.start_time = None  # epoch seconds when started
        self.elapsed_time = 0.0
        # try to load state
        self._load_state()

    def _load_state(self):
        data = safe_json_read(self.STATE_FILE, default=None)
        if data:
            try:
                self.running = data.get("running", False)
                self.start_time = data.get("start_time", None)
                self.elapsed_time = data.get("elapsed_time", 0.0)
                # if it was running, we update elapsed_time to now - start_time
                if self.running and self.start_time:
                    self.elapsed_time = time.time() - self.start_time
                    # keep start_time as original so continuing runs
                self.logger.info(f"Stopwatch restored. Running={self.running}, elapsed={self.elapsed_time:.2f}")
            except Exception as e:
                self.logger.error(f"Failed to restore stopwatch state: {e}")

    def _persist_state(self):
        data = {"running": self.running, "start_time": self.start_time, "elapsed_time": self.elapsed_time}
        safe_json_write(self.STATE_FILE, data)

    def start(self):
        if not self.running:
            if self.start_time is None:
                self.start_time = time.time()
            else:
                # resume from previous elapsed
                self.start_time = time.time() - self.elapsed_time
            self.running = True
            self._persist_state()
            return True
        return False

    def stop(self):
        if self.running:
            self.elapsed_time = time.time() - self.start_time
            self.running = False
            self._persist_state()
            return self.elapsed_time
        return self.elapsed_time

    def reset(self):
        self.start_time = None
        self.elapsed_time = 0.0
        self.running = False
        self._persist_state()

    def get_time(self):
        if self.running:
            return time.time() - self.start_time
        return self.elapsed_time

    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        return f"{minutes:02d}:{secs:06.3f}"


# ---------------------------
# Weather Handler (OpenWeather)
# ---------------------------
class WeatherHandler:
    def __init__(self, api_key: Optional[str], logger: logging.Logger):
        self.api_key = api_key
        self.logger = logger

    def get_current_weather(self, city: str) -> Optional[str]:
        if not self.api_key:
            self.logger.warning("OpenWeather API key missing")
            return None
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": self.api_key, "units": "metric"}
            r = requests.get(url, params=params, timeout=8)
            data = r.json()
            if data.get("cod") != 200:
                return None
            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            return f"The weather in {city} is {weather} with temperature {temp}°C and humidity {humidity}%."
        except Exception as e:
            self.logger.error(f"Weather fetch failed: {e}")
            return None


# ---------------------------
# Voice Assistant
# ---------------------------
class VoiceAssistant:
    def __init__(self, name: str = "Orion"):
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.is_listening = True        # listening flag
        self.keep_running = True       # keep process running after "exit" (so timers still run)
        self.conversation_history = []
        
        # Wake word detection
        self.wake_words = ["orion", "hey orion", "talk to me orion", "daddy's home orion"]
        self.wake_word_listening = True
        self.wake_word_detected = False
        self.wake_word_thread = None
        self._setup_tts()
        self._setup_recognizer()

        # spaCy
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                self.logger.info("spaCy loaded.")
            except Exception as e:
                self.logger.warning(f"spaCy available but failed to load model: {e}")
                self.nlp = None

        # Scheduler wrapper
        self.scheduler_wrapper = SchedulerWrapper(self.logger) if APSCHEDULER_AVAILABLE else SchedulerWrapper(self.logger)  # wrapper handles availability

        # managers
        self.timer_manager = TimerManager(self)
        self.stopwatch_manager = StopwatchManager(self)
        self.weather_handler = WeatherHandler(API_KEY, self.logger)

        # Groq handler
        self.groq_handler = GroqAIHandler(GROQ_API_KEY)

        # command patterns & built-in domains
        self.command_patterns = self._setup_command_patterns()
        self.built_in_domains = {
            'time', 'date', 'weather', 'timer', 'alarm', 'stopwatch',
            'app', 'calculate', 'system', 'greeting', 'help', 'exit'
        }

        # app mappings (launching applications)
        self.app_mappings = {
            'chrome': ['chrome.exe', 'google-chrome', 'chrome'],
            'firefox': ['firefox.exe', 'firefox'],
            'edge': ['msedge.exe', 'microsoft-edge', 'edge'],
            'notepad': ['notepad.exe', 'notepad'],
            'calculator': ['calc.exe', 'calculator'],
            'file explorer': ['explorer.exe', 'nautilus', 'explorer']
        }

        # Start wake word detection
        self.start_wake_word_detection()
        
        self.logger.info(f"{self.name} initialized.")

    # -----------------------
    # Core Setup
    # -----------------------
    def _setup_tts(self):
        try:
            self.engine = pt.init()
            voices = self.engine.getProperty('voices')
            
            # Try to find a male voice with leadership qualities
            male_voice = None
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    # Look for deep, authoritative male voice indicators
                    if any(indicator in voice_name for indicator in ['male', 'man', 'david', 'mark', 'george', 'james', 'richard']):
                        male_voice = voice
                        break
                    # Secondary preference - avoid female voices, prefer deeper/older sounding names
                    elif not any(indicator in voice_name for indicator in ['female', 'woman', 'zira', 'hazel', 'susan', 'samantha']) and male_voice is None:
                        male_voice = voice
            
            # Set the voice
            if male_voice:
                self.engine.setProperty('voice', male_voice.id)
                self.logger.info(f"Using voice: {male_voice.name}")
            elif voices and len(voices) > 0:
                # Fallback to first voice (often male on Windows)
                self.engine.setProperty('voice', voices[0].id)
                self.logger.info(f"Using fallback voice: {voices[0].name}")
            else:
                self.logger.warning("Using default voice")
            
            # Configure voice properties for Orion - deep, authoritative leadership voice
            self.engine.setProperty('rate', 135)  # Slower, more deliberate pace for authority
            self.engine.setProperty('volume', 0.95)  # Strong, confident volume
            
            self.logger.info("TTS engine initialized for Orion.")
        except Exception as e:
            self.logger.error(f"TTS init failed: {e}")
            self.engine = None

    def _setup_recognizer(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.logger.info("Speech recognizer configured.")

    # -----------------------
    # Speak / Listen
    # -----------------------
    def speak(self, text: str, log_message: bool = True):
        if not text:
            return
        if log_message:
            self.logger.info(f"Speaking: {text}")
        print(f"Aurora: {text}")
        try:
            if self.engine:
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                self.logger.warning("TTS engine not available; printing only.")
        except Exception as e:
            self.logger.error(f"TTS error: {e}")

    def listen(self, timeout: int = 10, phrase_time_limit: int = 15) -> Optional[str]:
        if not self.is_listening:
            return None
        try:
            with sr.Microphone() as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                self.logger.info("Audio captured, recognizing...")
                command = self.recognizer.recognize_google(audio, language='en-US')
                command = command.strip()
                self.logger.info(f"Recognized: {command}")
                # also echo on terminal
                print(f"You said: {command}")
                return command.lower()
        except sr.WaitTimeoutError:
            return "timeout"
        except sr.UnknownValueError:
            return "unclear"
        except sr.RequestError as e:
            self.logger.error(f"Speech service RequestError: {e}")
            return "service_error"
        except Exception as e:
            self.logger.error(f"Listen error: {e}")
            return "error"
    
    def listen_for_wake_words(self):
        """Continuously listen for wake words in background"""
        self.logger.info("Wake word detection started")
        while self.wake_word_listening and self.keep_running:
            try:
                with sr.Microphone() as source:
                    # Shorter timeout for wake word detection
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=8)
                    
                    try:
                        command = self.recognizer.recognize_google(audio, language='en-US')
                        command_lower = command.lower().strip()
                        
                        # Check for wake words
                        for wake_word in self.wake_words:
                            if wake_word in command_lower:
                                self.logger.info(f"Wake word detected: '{wake_word}' in '{command}'")
                                self.wake_word_detected = True
                                
                                # Extract command after wake word
                                remaining_command = command_lower.replace(wake_word, "").strip()
                                if remaining_command:
                                    # Process the command immediately
                                    self.logger.info(f"Processing wake word command: {remaining_command}")
                                    intent = self.recognize_command(remaining_command)
                                    self.execute_command(intent, remaining_command)
                                else:
                                    # Just wake word, acknowledge
                                    self.speak("Yes, Commander? I'm listening.")
                                break
                                
                    except sr.UnknownValueError:
                        # Ignore unclear audio for wake words
                        continue
                    except sr.RequestError as e:
                        self.logger.warning(f"Wake word recognition service error: {e}")
                        time.sleep(1)  # Wait before retrying
                        
            except sr.WaitTimeoutError:
                # Timeout is expected, continue listening
                continue
            except Exception as e:
                self.logger.error(f"Wake word detection error: {e}")
                time.sleep(1)  # Brief pause before retrying
        
        self.logger.info("Wake word detection stopped")
    
    def start_wake_word_detection(self):
        """Start wake word detection in background thread"""
        if self.wake_word_thread is None or not self.wake_word_thread.is_alive():
            self.wake_word_listening = True
            self.wake_word_thread = threading.Thread(target=self.listen_for_wake_words, daemon=True)
            self.wake_word_thread.start()
            self.logger.info("Wake word detection thread started")
    
    def stop_wake_word_detection(self):
        """Stop wake word detection"""
        self.wake_word_listening = False
        if self.wake_word_thread and self.wake_word_thread.is_alive():
            self.wake_word_thread.join(timeout=2)
        self.logger.info("Wake word detection stopped")

    # -----------------------
    # Intent Recognition
    # -----------------------
    def _setup_command_patterns(self) -> Dict[str, List[str]]:
        return {
            'time': [
                r'\b(what\s+time|current\s+time|time\s+is|tell\s+time|tell\s+me\s+the\s+time)\b',
                r'\b(what\s+is\s+the\s+time|whats\s+the\s+time)\b',
                r'\b(time\s+right\s+now|current\s+time)\b',
                r'\b(what\s+time\s+is\s+it)\b',
                r'\bclock\b'
            ],
            'date': [
                r'\b(what\s+date|current\s+date|today\'s\s+date|what\s+day)\b',
                r'\b(what\s+is\s+the\s+date|whats\s+the\s+date)\b',
                r'\b(what\s+day\s+is\s+it|what\s+day\s+is\s+today)\b',
                r'\b(todays\s+date|date\s+today)\b'
            ],
            'greeting': [r'\b(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)\b'],
            'exit': [r'\b(exit|quit|goodbye|bye|shutdown|turn\s+off)\b', r'\b(aurora\s+stop|aurora\s+exit|aurora\s+quit)\b', r'^stop$'],
            'help': [r'\b(help|what\s+can\s+you\s+do|commands|assistance)\b'],
            'weather': [r'\b(weather|forecast|temperature)\b', r'\b(weather\s+in|temperature\s+in)\b'],
            'timer': [r'\b(set\s+(a\s+)?timer|timer\s+for|countdown|remind\s+me)\b'],
            'alarm': [r'\b(set\s+(an?\s+)?alarm|alarm\s+for|wake\s+me)\b'],
            'stopwatch': [r'\b(stopwatch|start\s+stopwatch|stop\s+stopwatch|reset\s+stopwatch)\b'],
            'app': [r'\b(open|launch|start|run)\s+\w+\b'],
            'search': [r'\b(search\s+for|look\s+up|google|find)\b'],
            'system': [
                r'\b(system\s+info|battery|memory|disk|storage|cpu)\b',
                r'\b(how\s+much\s+(battery|memory|storage))\b',
                r'\b(memory\s+usage|ram\s+usage|disk\s+usage|storage\s+usage)\b',
                r'\b(my\s+(battery|memory|storage|system))\b'
            ],
            'calculate': [
                r'\b(calculate|solve|compute)\b',
                r'\b(add|plus|subtract|minus|multiply|times|divide|divided)\b',
                r'\b(what\s+(is|are)\s+\d)\b'
            ]
        }

    def recognize_command(self, query: str) -> str:
        if not query:
            return "unknown"
        q = query.lower()
        # Try regex patterns first
        for cmd, patterns in self.command_patterns.items():
            for p in patterns:
                if re.search(p, q, re.IGNORECASE):
                    return cmd
        # If spaCy present, run enhanced intent detection
        if self.nlp:
            try:
                doc = self.nlp(q)
                tokens = [t.text.lower() for t in doc]
                lemmas = [t.lemma_.lower() for t in doc]
                
                # Enhanced intent detection using tokens and lemmas
                
                # Time intent
                time_indicators = ['time', 'clock', 'hour', 'minute']
                if any(word in tokens + lemmas for word in time_indicators):
                    if any(phrase in q for phrase in ['what time', 'current time', 'time is', 'time right now']):
                        return "time"
                
                # Date intent
                date_indicators = ['date', 'day', 'today', 'calendar']
                if any(word in tokens + lemmas for word in date_indicators):
                    if any(phrase in q for phrase in ['what date', 'what day', 'today']):
                        return "date"
                
                # Math/calculation intent
                math_indicators = ['calculate', 'compute', 'add', 'subtract', 'multiply', 'divide', 'plus', 'minus', 'times']
                if any(word in tokens + lemmas for word in math_indicators):
                    return "calculate"
                
                # Check for numbers with math operators
                if re.search(r'\d+.*[\+\-\*\/x×÷]', q):
                    return "calculate"
                
                # System info intent
                system_indicators = ['battery', 'memory', 'disk', 'storage', 'system']
                if any(word in tokens + lemmas for word in system_indicators):
                    return "system"
                
                # Weather intent
                weather_indicators = ['weather', 'temperature', 'forecast', 'rain', 'sunny', 'cloudy']
                if any(word in tokens + lemmas for word in weather_indicators):
                    return "weather"
                
                # App launching intent
                app_indicators = ['open', 'launch', 'start', 'run']
                if any(word in tokens for word in app_indicators):
                    return "app"
                    
            except Exception as e:
                self.logger.debug(f"spaCy parse failed: {e}")
        # last resort: unknown
        return "unknown"

    # -----------------------
    # High-level routing
    # -----------------------
    def execute_command(self, command: str, original_query: str, entities: Dict = None):
        entities = entities or {}
        try:
            # route built-ins
            if command in self.built_in_domains:
                # built-ins handling
                if command == 'time':
                    self.tell_time()
                elif command == 'date':
                    self.tell_date()
                elif command == 'greeting':
                    self.handle_greeting()
                elif command == 'help':
                    self.show_help()
                elif command == 'exit':
                    self.handle_exit()
                elif command == 'weather':
                    self.handle_weather(original_query)
                elif command == 'timer':
                    self.handle_timer(original_query)
                elif command == 'alarm':
                    self.handle_alarm(original_query)
                elif command == 'stopwatch':
                    self.handle_stopwatch(original_query)
                elif command == 'app':
                    self.handle_app_launch(original_query)
                elif command == 'calculate':
                    self.handle_calculation(original_query)
                elif command == 'system':
                    self.handle_system_info(original_query)
                else:
                    self.speak("I didn't recognize that built-in command.")
            elif command == 'unknown' or command not in self.built_in_domains:
                # if unknown, check whether it's a small Q we can answer locally (e.g., simple math)
                handled_locally = self._handle_local_fallbacks(original_query)
                if not handled_locally:
                    # Send to Groq
                    self.handle_groq_query(original_query)
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            self.speak("I ran into an error while executing that command.")

    # -----------------------
    # Local fallback checks (math, short Qs)
    # -----------------------
    def _handle_local_fallbacks(self, query: str) -> bool:
        q = query.lower().strip()
        # math
        if self._looks_like_math(q):
            result = self._evaluate_math_expression(q)
            if result is not None:
                self.speak(f"The result is {result}")
            else:
                self.speak("I couldn't evaluate that expression.")
            return True

        # short hardcoded Q/A examples
        # Add your existing hardcoded Q/A here (example)
        hardcoded_map = {
            "who made you": "I was forged through your dedication and enhanced through our collaborative missions.",
            "what is your name": f"I am {self.name}, your commanding voice assistant.",
            "are you a robot": "I am an advanced AI voice assistant, your strategic digital ally."
        }
        for k, v in hardcoded_map.items():
            if k in q:
                self.speak(v)
                return True

        return False

    def _looks_like_math(self, query: str) -> bool:
        q = query.lower()
        
        # Math keywords
        math_keywords = ['calculate', 'compute', 'solve', 'add', 'subtract', 'multiply', 
                        'divide', 'plus', 'minus', 'times', 'equals', 'squared', 'cubed']
        
        # Check for math keywords
        if any(keyword in q for keyword in math_keywords):
            return True
            
        # Check for numbers with operators
        if re.search(r'\d+.*[\+\-\*\/x×÷].*\d+', query):
            return True
            
        # Check for "what is" followed by numbers and operators
        if re.search(r'what\s+(is|are)\s+\d', q):
            return True
            
        return False

    def _evaluate_math_expression(self, query: str) -> Optional[float]:
        try:
            expression = query.lower().strip()
            
            # Remove common question words
            expression = re.sub(r"\b(what('?s| is)?|calculate|solve|compute|find)\s+", "", expression)
            
            # More comprehensive replacements
            replacements = [
                (r'\bplus\b', ' + '),
                (r'\bminus\b', ' - '),
                (r'\btimes\b', ' * '),
                (r'\bmultiplied\s+by\b', ' * '),
                (r'\bdivided\s+by\b', ' / '),
                (r'\bover\b', ' / '),
                (r'\binto\b', ' * '),
                (r'\bof\b', ' * '),
                (r'\bx\b', ' * '),
                (r'×', ' * '),
                (r'÷', ' / '),
                (r'\bsquared\b', ' ** 2'),
                (r'\bcubed\b', ' ** 3'),
                (r'\bsquare\s+root\s+of\b', 'sqrt('),
                (r'\bpercent\s+of\b', ' * 0.01 * '),
            ]
            
            for pat, rep in replacements:
                expression = re.sub(pat, rep, expression)
            
            # Handle square root
            if 'sqrt(' in expression:
                import math
                expression = expression.replace('sqrt(', f'{math.sqrt.__name__}(')
            
            # Clean up the expression - keep only safe math characters
            expression = re.sub(r'[^0-9.+\-*/()\s]', '', expression)
            expression = expression.strip()
            
            # Must contain at least one digit and one operator
            if not re.search(r'[0-9]', expression):
                return None
            if not re.search(r'[\+\-\*\/]', expression):
                # Maybe it's just a number being asked about
                try:
                    return float(expression)
                except:
                    return None
            
            # Safety check - only allow safe characters
            allowed = set("0123456789+-*/(). ")
            if not all(ch in allowed for ch in expression):
                return None
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}, "sqrt": __import__('math').sqrt})
            
            if isinstance(result, (int, float)):
                return round(float(result), 6) if isinstance(result, float) else result
            return None
            
        except Exception as e:
            self.logger.debug(f"Math eval error for '{query}': {e}")
            return None

    # -----------------------
    # Built-in command implementations
    # -----------------------
    def tell_time(self):
        try:
            now = dt.datetime.now()
            time_str = now.strftime("%I:%M %p")
            self.speak(f"The current time is {time_str}")
        except Exception as e:
            self.logger.error(f"tell_time error: {e}")
            self.speak("I couldn't get the current time.")

    def tell_date(self):
        try:
            today = dt.date.today()
            formatted = today.strftime("%A, %B %d, %Y")
            self.speak(f"Today is {formatted}")
        except Exception as e:
            self.logger.error(f"tell_date error: {e}")
            self.speak("I couldn't get today's date.")

    def handle_greeting(self):
        hour = dt.datetime.now().hour
        if hour < 12:
            greeting = "Good morning, Commander"
        elif hour < 17:
            greeting = "Good afternoon, Commander"
        else:
            greeting = "Good evening, Commander"
        self.speak(f"{greeting}! I am Orion, your strategic voice assistant. What are your orders?")

    def show_help(self):
        text = (
            "I stand ready to provide time and scheduling data, weather reconnaissance, "
            "mission timers and alerts, tactical calculations, system operations, and strategic analysis. "
            "For complex queries, I will consult my AI command network. What is your mission?"
        )
        self.speak(text)

    def handle_exit(self):
        # stop listening but keep process/scheduler alive
        self.speak("Acknowledged. I will cease active monitoring. Background operations and mission timers will continue. "
                   "To fully terminate my systems, command 'terminate assistant' or use Ctrl+C.")
        self.is_listening = False
        self.keep_running = True  # keep process alive so jobs run
        # stop wake word detection when exiting
        self.stop_wake_word_detection()
        # do not call scheduler.shutdown()

    def terminate(self):
        """Full stop: stops scheduler and exits process after speaking."""
        self.speak("Initiating full system shutdown. All operations terminating. Orion, signing off.")
        # stop wake word detection
        self.stop_wake_word_detection()
        # shutdown scheduler
        try:
            if self.scheduler_wrapper and self.scheduler_wrapper.available:
                self.scheduler_wrapper.shutdown(wait=False)
        except Exception:
            pass
        # give TTS a moment then exit
        try:
            time.sleep(0.6)
        except Exception:
            pass
        os._exit(0)

    # -----------------------
    # Weather
    # -----------------------
    def handle_weather(self, query: str):
        # try to extract city
        city = self._extract_city_from_query(query)
        if not city:
            # ask follow-up once
            self.speak("Which city do you want the weather for?")
            city_response = self.listen()
            if city_response and city_response not in ("timeout", "unclear", "service_error", "error"):
                city = city_response
            else:
                self.speak("I didn't get the city name.")
                return
        # fetch
        weather_report = self.weather_handler.get_current_weather(city)
        if weather_report:
            self.speak(weather_report)
        else:
            self.speak(f"Couldn't fetch weather for {city} right now.")

    def _extract_city_from_query(self, query: str) -> Optional[str]:
        # basic patterns
        m = re.search(r'weather (?:in|for) ([a-zA-Z\s]{2,40})', query, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m2 = re.search(r'temperature (?:in|for) ([a-zA-Z\s]{2,40})', query, re.IGNORECASE)
        if m2:
            return m2.group(1).strip()
        # spaCy entity attempt
        if self.nlp:
            try:
                doc = self.nlp(query)
                for ent in doc.ents:
                    if ent.label_ in ("GPE", "LOC"):
                        return ent.text
            except Exception:
                pass
        return None

    # -----------------------
    # Timer / Alarm / Stopwatch handlers
    # -----------------------
    def handle_timer(self, query: str):
        duration = self._parse_time_duration(query)
        if duration and duration > 0:
            name = f"Timer for {duration // 60} minutes" if duration >= 60 else f"Timer for {duration} seconds"
            t_id = self.timer_manager.set_timer(duration, name)
            self.speak(f"Timer set for {self._format_seconds(duration)}.")
        else:
            self.speak("I couldn't understand the timer duration. Try 'set timer for 5 minutes'.")

    def handle_alarm(self, query: str):
        alarm_time = self._parse_alarm_time(query)
        if alarm_time:
            aid = self.timer_manager.set_alarm(alarm_time)
            self.speak(f"Alarm set for {alarm_time.strftime('%I:%M %p')}.")
        else:
            self.speak("I couldn't understand that alarm time. Try 'set alarm for 7 AM'.")

    def handle_stopwatch(self, query: str):
        q = query.lower()
        if 'start' in q:
            if self.stopwatch_manager.start():
                self.speak("Stopwatch started.")
            else:
                self.speak("Stopwatch was already running.")
        elif 'stop' in q:
            elapsed = self.stopwatch_manager.stop()
            self.speak(f"Stopwatch stopped at {self.stopwatch_manager.format_time(elapsed)}.")
        elif 'reset' in q:
            self.stopwatch_manager.reset()
            self.speak("Stopwatch reset.")
        else:
            current = self.stopwatch_manager.get_time()
            status = "running" if self.stopwatch_manager.running else "stopped"
            self.speak(f"Stopwatch is {status} at {self.stopwatch_manager.format_time(current)}.")

    def _parse_time_duration(self, query: str) -> int:
        total = 0
        q = query.lower()
        hours = re.search(r'(\d+)\s*(?:hours?|hrs?)', q)
        if hours:
            total += int(hours.group(1)) * 3600
        mins = re.search(r'(\d+)\s*(?:minutes?|mins?)', q)
        if mins:
            total += int(mins.group(1)) * 60
        secs = re.search(r'(\d+)\s*(?:seconds?|secs?)', q)
        if secs:
            total += int(secs.group(1))
        if total == 0:
            # fallback: first number => minutes
            num = re.search(r'(\d+)', q)
            if num:
                total = int(num.group(1)) * 60
        return total

    def _parse_alarm_time(self, query: str) -> Optional[dt.time]:
        q = query.lower()
        # handle "7 am", "07:30 am", "19:00"
        m = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm)?', q)
        if m:
            try:
                hour = int(m.group(1))
                minute = int(m.group(2)) if m.group(2) else 0
                ampm = m.group(3)
                if ampm:
                    ampm = ampm.lower()
                    if ampm == 'pm' and hour != 12:
                        hour += 12
                    elif ampm == 'am' and hour == 12:
                        hour = 0
                return dt.time(hour % 24, minute % 60)
            except Exception:
                return None
        return None

    def _format_seconds(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} seconds"
        else:
            mins = seconds // 60
            return f"{mins} minutes"

    # -----------------------
    # App launching, calculations, system info
    # -----------------------
    def handle_app_launch(self, query: str):
        app = self._extract_app_name(query)
        if app:
            success = self._launch_app(app)
            if success:
                self.speak(f"Opening {app}.")
            else:
                self.speak(f"Couldn't open {app}.")
        else:
            self.speak("Which app would you like to open?")

    def _extract_app_name(self, query: str) -> Optional[str]:
        for app in self.app_mappings.keys():
            if app in query.lower():
                return app
        return None

    def _launch_app(self, app_name: str) -> bool:
        executables = self.app_mappings.get(app_name, [])
        for exe in executables:
            try:
                if os.name == 'nt':
                    subprocess.Popen(exe, shell=True)
                else:
                    subprocess.Popen([exe])
                return True
            except Exception as e:
                continue
        return False

    def handle_calculation(self, query: str):
        res = self._evaluate_math_expression(query)
        if res is not None:
            self.speak(f"The result is {res}")
        else:
            self.speak("I couldn't compute that.")

    def handle_system_info(self, query: str):
        q = query.lower()
        try:
            if 'battery' in q:
                try:
                    bat = psutil.sensors_battery()
                    if bat:
                        plugged = "plugged in" if bat.power_plugged else "not plugged in"
                        self.speak(f"Battery level is {bat.percent} percent and {plugged}.")
                    else:
                        self.speak("Battery information is unavailable. This might be a desktop computer.")
                except Exception as e:
                    self.logger.debug(f"Battery check failed: {e}")
                    self.speak("I couldn't access battery information.")
                    
            elif 'storage' in q or 'disk' in q:
                try:
                    # Use appropriate path based on OS
                    disk_path = 'C:' if os.name == 'nt' else '/'
                    disk = psutil.disk_usage(disk_path)
                    free_gb = disk.free / (1024**3)
                    total_gb = disk.total / (1024**3)
                    used_percent = (disk.used / disk.total) * 100
                    self.speak(f"You have {free_gb:.1f} GB free out of {total_gb:.1f} GB total. Storage is {used_percent:.1f}% full.")
                except Exception as e:
                    self.logger.debug(f"Disk usage check failed: {e}")
                    self.speak("I couldn't access storage information.")
                    
            elif 'memory' in q or 'ram' in q:
                try:
                    mem = psutil.virtual_memory()
                    available_gb = mem.available / (1024**3)
                    total_gb = mem.total / (1024**3)
                    self.speak(f"Memory usage is {mem.percent}%. You have {available_gb:.1f} GB available out of {total_gb:.1f} GB total.")
                except Exception as e:
                    self.logger.debug(f"Memory check failed: {e}")
                    self.speak("I couldn't access memory information.")
                    
            elif 'cpu' in q or 'processor' in q:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    cpu_count = psutil.cpu_count()
                    self.speak(f"CPU usage is {cpu_percent}% across {cpu_count} cores.")
                except Exception as e:
                    self.logger.debug(f"CPU check failed: {e}")
                    self.speak("I couldn't access CPU information.")
                    
            else:
                self.speak("I can report battery, storage, memory, or CPU information. Which would you like?")
        except Exception as e:
            self.logger.error(f"system info error: {e}")
            self.speak("I couldn't get system information.")

    # -----------------------
    # Groq fallback
    # -----------------------
    def handle_groq_query(self, query: str):
        if not self.groq_handler.is_available():
            # In absence of Groq, politely inform user
            self.speak("I can't reach Groq AI right now. Try asking something I can handle locally.")
            return
        try:
            current_time = dt.datetime.now().strftime("%I:%M %p on %B %d, %Y")
            context = f"Current time: {current_time}. You are Orion, a commanding strategic voice assistant."
            self.logger.info(f"Sending to Groq: {query}")
            response = self.groq_handler.get_response(query, context)
            if response:
                self.speak(response)
                self.conversation_history.append({
                    "timestamp": dt.datetime.now().isoformat(),
                    "user_query": query,
                    "groq_response": response
                })
            else:
                self.speak("Groq didn't return a result.")
        except Exception as e:
            self.logger.error(f"Groq query failed: {e}")
            self.speak("I couldn't reach Groq right now.")

    # -----------------------
    # Conversation saving
    # -----------------------
    def save_conversation_history(self):
        try:
            fname = f"conversation_history_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            safe_json_write(fname, self.conversation_history)
            self.logger.info(f"Conversation saved to {fname}")
        except Exception as e:
            self.logger.error(f"Failed to save conversation: {e}")


# ---------------------------
# Main entrypoint
# ---------------------------
def main():
    print("Starting Orion Voice Assistant...")
    assistant = VoiceAssistant()
    assistant.speak("Systems initialized. Orion reporting for duty. I am now listening for your wake words: Orion, Hey Orion, Talk to me Orion, or Daddy's home Orion.")

    # Main loop: keep process alive even after "exit" is spoken.
    # If assistant.is_listening becomes False (exit), we break inner listening loop but keep process alive
    try:
        while assistant.keep_running:
            # If not listening, sleep and let scheduler/timers run; user can later call assistant.terminate via voice 'terminate assistant'
            if not assistant.is_listening:
                # idle wait - keep process alive so scheduler jobs run
                time.sleep(1.0)
                continue

            command_raw = assistant.listen()
            if command_raw in (None,):
                continue
            if command_raw in ("timeout", "unclear"):
                assistant.speak("I didn't catch that.")
                continue
            if command_raw in ("service_error", "error"):
                assistant.speak("There was an error with the speech service.")
                continue

            intent = assistant.recognize_command(command_raw)
            assistant.execute_command(intent, command_raw)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Terminating assistant.")
    except Exception as e:
        assistant.logger.error(f"Main loop exception: {e}")
    finally:
        # Save conversation on exit
        assistant.save_conversation_history()
        # Do not shut down scheduler automatically unless terminating
        print("Orion process exiting main loop. Background operations will continue if full termination is not called.")


if __name__ == "__main__":
    main()
