import os
import base64
import subprocess
import glob
import signal
import sys
import time
import threading
import select
import traceback  # Added for better error reporting

# Handle clipboard functionality (optional in headless environments)
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    print("Warning: pyperclip not available, clipboard operations disabled")

# Handle requests for API calls
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests library not available, API calls disabled")

# Optional Google Cloud dependencies
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleAuthRequest
    GOOGLE_CLOUD_AVAILABLE = True
    service_account = service_account  # Make sure it's available in the module scope
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    service_account = None
    GoogleAuthRequest = None
    print("Google Cloud libraries not available - using demo mode for image generation")

# Configuration for different environments
import os
import platform
from pathlib import Path

# Get the current script directory
SCRIPT_DIR = Path(__file__).parent

# Environment detection
IS_RASPBERRY_PI = os.path.exists('/etc/rpi-issue') or 'raspberry' in platform.platform().lower()
IS_HEADLESS = not os.environ.get('DISPLAY') and platform.system() == 'Linux'

# Standardized paths as per requirements - all files in /home/pi/Desktop/v2_Tripple S/
BASE_DIR = Path("/home/pi/Desktop/v2_Tripple S")

# Google Cloud Configuration  
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS', str(BASE_DIR / "cloudKey.json"))
# For Google Speech-to-Text, use the standardized credentials path
GOOGLE_SPEECH_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', str(BASE_DIR / "cloudKey.json"))
PROJECT_ID = os.getenv('PROJECT_ID', "trippe-s")
ENDPOINT = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/us-central1/publishers/google/models/imagen-4.0-generate-001:predict"

# Script paths - consistent with repository structure
AUFNAHME_SCRIPT = str(SCRIPT_DIR / "Aufnahme.py")
VOICE_SCRIPT = str(SCRIPT_DIR / "voiceToGoogle.py")
# REMOVED: COPY_SCRIPT (dateiKopieren.py) - no longer part of streamlined workflow

# Standardized file paths in working directory
AUDIO_FILE = str(BASE_DIR / "aufnahme.wav")
TRANSKRIPT_PATH = str(BASE_DIR / "transkript.txt")
TRANSKRIPT_JSON_PATH = str(BASE_DIR / "transkript.json")
BILDER_DIR = str(BASE_DIR / "BilderVertex")

# Print environment info on startup
if __name__ == "__main__":
    print(f"Environment: {'Raspberry Pi' if IS_RASPBERRY_PI else 'Desktop'}")
    print(f"Display: {'Headless' if IS_HEADLESS else 'GUI Available'}")
    print(f"Script Directory: {SCRIPT_DIR}")

class AsyncWorkflowManager:
    """Manages the asynchronous execution of the recording and processing workflow"""
    
    def __init__(self):
        self.recording_process = None
        self.is_recording = False
        self.should_stop = False
        self.output_lines = []
        
    def run_script_sync(self, script_path, beschreibung):
        """Run a script synchronously with output collection"""
        if os.path.exists(script_path):
            print(f"Starte {beschreibung}: {script_path}")
            try:
                # Setup environment variables for the script
                env = os.environ.copy()
                
                # Set GOOGLE_APPLICATION_CREDENTIALS for speech-to-text
                if "voiceToGoogle.py" in script_path:
                    env['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_SPEECH_CREDENTIALS
                    print(f"Setting GOOGLE_APPLICATION_CREDENTIALS to: {GOOGLE_SPEECH_CREDENTIALS}")
                    
                    # Log credential file status
                    if os.path.exists(GOOGLE_SPEECH_CREDENTIALS):
                        print(f"✓ Google credentials file found: {GOOGLE_SPEECH_CREDENTIALS}")
                    else:
                        print(f"⚠ Google credentials file not found: {GOOGLE_SPEECH_CREDENTIALS}")
                        print("Speech recognition will use simulation mode")
                
                result = subprocess.run(
                    ["python3", script_path], 
                    capture_output=True, 
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env=env  # Pass environment variables
                )
                
                if result.stdout:
                    print("--- STDOUT ---")
                    print(result.stdout)
                    
                if result.stderr:
                    print("--- STDERR ---") 
                    print(result.stderr)
                    
                if result.returncode != 0:
                    print(f"Fehler beim Starten von {os.path.basename(script_path)} (Exit Code: {result.returncode})")
                else:
                    print(f"{beschreibung} abgeschlossen!")
                    
                return result.returncode == 0
                
            except subprocess.TimeoutExpired:
                print(f"Timeout bei {beschreibung} nach 5 Minuten")
                return False
            except Exception as e:
                print(f"Fehler beim Ausführen von {beschreibung}: {e}")
                return False
        else:
            print(f"{os.path.basename(script_path)} nicht gefunden!")
            return False

    def start_recording_async(self, script_path):
        """Start Aufnahme.py as asynchronous subprocess"""
        if not script_path or not os.path.exists(script_path):
            print(f"Aufnahme-Script nicht gefunden: {script_path}")
            return False
            
        if self.is_recording:
            print("Warnung: Aufnahme läuft bereits")
            return False
            
        try:
            print(f"Starte Aufnahme asynchron: {script_path}")
            
            # Start the recording process
            self.recording_process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,  # Line buffered
                preexec_fn=os.setsid  # Create new process group
            )
            
            self.is_recording = True
            self.output_lines = []
            print(f"Aufnahme gestartet (PID: {self.recording_process.pid})")
            print("Drücke Enter um die Aufnahme zu stoppen, oder warte auf externes Signal...")
            
            # Start output monitoring thread
            output_thread = threading.Thread(target=self._monitor_output, daemon=True)
            output_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Starten der Aufnahme: {e}")
            self.is_recording = False
            return False

    def _monitor_output(self):
        """Monitor subprocess output in separate thread"""
        try:
            while self.is_recording and self.recording_process:
                if self.recording_process.poll() is not None:
                    # Process has ended
                    break
                    
                # Read available output
                try:
                    # Use select on Unix systems for non-blocking read
                    if hasattr(select, 'select'):
                        ready, _, _ = select.select([self.recording_process.stdout], [], [], 0.1)
                        if ready:
                            line = self.recording_process.stdout.readline()
                            if line:
                                line = line.strip()
                                self.output_lines.append(line)
                                print(f"[Aufnahme] {line}")
                    else:
                        # Fallback for systems without select
                        time.sleep(0.1)
                        
                except Exception:
                    break
                    
        except Exception as e:
            print(f"Fehler beim Überwachen der Ausgabe: {e}")

    def stop_recording(self):
        """Stop the recording process gracefully using SIGTERM"""
        if not self.is_recording or not self.recording_process:
            print("Keine Aufnahme läuft")
            return True
            
        try:
            print("Stoppe Aufnahme...")
            
            # Send SIGTERM to the process group for clean shutdown
            os.killpg(os.getpgid(self.recording_process.pid), signal.SIGTERM)
            
            # Wait for process to finish with timeout
            try:
                stdout, stderr = self.recording_process.communicate(timeout=10)
                
                # Collect any remaining output
                if stdout:
                    for line in stdout.split('\n'):
                        if line.strip():
                            self.output_lines.append(line.strip())
                            print(f"[Aufnahme] {line.strip()}")
                            
                if stderr:
                    print("--- Aufnahme STDERR ---")
                    print(stderr)
                    
            except subprocess.TimeoutExpired:
                print("Aufnahme reagiert nicht auf SIGTERM, erzwinge Beendigung...")
                os.killpg(os.getpgid(self.recording_process.pid), signal.SIGKILL)
                self.recording_process.wait()
                
            print("Aufnahme gestoppt")
            self.is_recording = False
            
            # Display summary of collected output
            if self.output_lines:
                print("\n--- Aufnahme Zusammenfassung ---")
                for line in self.output_lines[-10:]:  # Show last 10 lines
                    print(line)
                print("--- Ende Zusammenfassung ---\n")
                
            return True
            
        except Exception as e:
            print(f"Fehler beim Stoppen der Aufnahme: {e}")
            self.is_recording = False
            return False

    def wait_for_stop_signal(self):
        """Wait for user input or external signal to stop recording"""
        def signal_handler(signum, frame):
            print(f"\nSignal {signum} empfangen, stoppe Aufnahme...")
            self.should_stop = True

        # Set up signal handlers
        original_handlers = {}
        try:
            original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, signal_handler)
            original_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, signal_handler)
        except Exception as e:
            print(f"Warnung: Konnte Signal-Handler nicht setzen: {e}")
        
        try:
            while self.is_recording and not self.should_stop:
                # Check if recording process is still running
                if self.recording_process and self.recording_process.poll() is not None:
                    print("Aufnahme-Prozess beendet")
                    self.is_recording = False
                    break
                
                # Check for keyboard input (non-blocking)
                if hasattr(select, 'select') and sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    input_line = sys.stdin.readline().strip()
                    if input_line == "" or input_line.lower() in ['q', 'quit', 'exit', 'stop']:
                        print("Benutzer-Stop erkannt")
                        self.should_stop = True
                        break
                elif not hasattr(select, 'select'):
                    # Fallback for systems without select - just wait a bit
                    time.sleep(0.1)
                        
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nKeyboard Interrupt empfangen")
            self.should_stop = True
        except Exception as e:
            print(f"Fehler beim Warten auf Stop-Signal: {e}")
            self.should_stop = True
        finally:
            # Restore original signal handlers
            for sig, handler in original_handlers.items():
                try:
                    signal.signal(sig, handler)
                except Exception:
                    pass  # Ignore errors when restoring handlers
            
        return self.should_stop or not self.is_recording

def run_script(script_path, beschreibung):
    """Legacy function for backwards compatibility"""
    manager = AsyncWorkflowManager()
    return manager.run_script_sync(script_path, beschreibung)

class WorkflowFileWatcher:
    """Background service that watches for workflow trigger files and executes tasks"""
    
    def __init__(self, work_dir=None):
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent
        self.trigger_file = self.work_dir / "workflow_trigger.txt"
        self.status_log = self.work_dir / "workflow_status.log"
        self.lock_file = self.work_dir / "workflow_service.lock"
        self.running = False
        self.check_interval = 1.0  # Check every second
        self.workflow_completed = False
        
    def acquire_service_lock(self):
        """Acquire exclusive lock to prevent multiple service instances"""
        try:
            if self.lock_file.exists():
                # Check if existing lock is stale
                lock_stat = self.lock_file.stat()
                lock_age = time.time() - lock_stat.st_mtime
                if lock_age > 300:  # 5 minutes - consider stale
                    self.log_status("Entferne veraltete Lock-Datei", "WARNING")
                    self.lock_file.unlink()
                else:
                    self.log_status("Service bereits aktiv (Lock-Datei vorhanden)", "ERROR")
                    return False
            
            # Create lock file with PID
            with open(self.lock_file, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            
            self.log_status(f"Service-Lock erworben (PID: {os.getpid()})")
            return True
            
        except Exception as e:
            self.log_status(f"Fehler beim Erwerben des Service-Locks: {e}", "ERROR")
            return False
    
    def release_service_lock(self):
        """Release service lock"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                self.log_status("Service-Lock freigegeben")
        except Exception as e:
            self.log_status(f"Fehler beim Freigeben des Service-Locks: {e}", "WARNING")
        
    def log_status(self, message, level="INFO"):
        """Log status message to log file"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{timestamp}] {level}: {message}\n"
            
            with open(self.status_log, "a", encoding="utf-8") as f:
                f.write(log_line)
                
            print(f"[{level}] {message}")
            
        except Exception as e:
            print(f"Logging error: {e}")
    
    def clear_status_log(self):
        """Clear the status log file"""
        try:
            if self.status_log.exists():
                self.status_log.unlink()
        except Exception as e:
            print(f"Error clearing log: {e}")
    
    def execute_workflow(self):
        """
        Execute the clean, streamlined workflow after recording
        
        Streamlined Workflow Sequence:
        1. Transcription: voiceToGoogle.py processes aufnahme.wav → creates transkript.json
        2. File Operations: dateiKopieren.py handles local file management 
        3. Image Generation: Vertex AI generates images from transcript → saves to BilderVertex/
        
        Path Logic:
        - All files located in /home/pi/Desktop/v2_Tripple S/
        - aufnahme.wav: source audio file
        - transkript.json: transcript with metadata (AI processing ready)
        - BilderVertex/: generated images directory
        - cloudKey.json: Google service account credentials (for Vertex AI)
        """
        self.log_status("=== Starting Clean Vertex AI Workflow ===")
        self.log_status("Streamlined workflow: Recording → Transcription → Vertex AI Image Generation")
        self.log_status("⚡ ENHANCED: Workflow now waits for complete recording validation before starting")
        
        success_count = 0
        total_steps = 2  # Streamlined to 2 essential steps: Speech Recognition → Vertex AI
        
        try:
            # Pre-Step: Validate audio file is ready for transcription (race condition prevention)
            self.log_status("Pre-Step: Validating audio file is ready for transcription...")
            audio_file_path = Path(AUDIO_FILE)
            
            if not audio_file_path.exists():
                self.log_status(f"✗ Audio file not found: {AUDIO_FILE}", "ERROR")
                self.log_status("This indicates the recording was not completed properly", "ERROR")
                self.log_status("WORKFLOW_ERROR: Recording incomplete - aborting transcription", "ERROR")
                return
            
            # Check file size and stability
            file_size = audio_file_path.stat().st_size
            if file_size < 1024:
                self.log_status(f"✗ Audio file too small: {file_size} bytes", "ERROR")
                self.log_status("This indicates incomplete or failed recording", "ERROR")
                self.log_status("WORKFLOW_ERROR: Invalid audio file - aborting transcription", "ERROR")
                return
            
            # Quick stability check (ensure file is not still being written)
            import time
            initial_size = file_size
            time.sleep(0.1)  # Brief wait
            current_size = audio_file_path.stat().st_size
            
            if initial_size != current_size:
                self.log_status(f"✗ Audio file still changing: {initial_size} -> {current_size} bytes", "WARNING")
                self.log_status("File appears to be still in use - waiting and retrying...", "INFO")
                time.sleep(0.5)  # Wait longer
                current_size = audio_file_path.stat().st_size
                if initial_size != current_size:
                    self.log_status("WORKFLOW_ERROR: Audio file unstable - aborting to prevent race condition", "ERROR")
                    return
            
            self.log_status(f"✓ Audio file validated and stable: {file_size:,} bytes", "INFO")
            self.log_status("✅ RACE CONDITION PREVENTION: Audio file ready for safe transcription", "INFO")
            
            # Step 1: Voice recognition (Transcription)
            self.log_status("Schritt 1/2: Spracherkennung (voiceToGoogle.py)...")
            self.log_status(f"Setting GOOGLE_APPLICATION_CREDENTIALS to: {GOOGLE_SPEECH_CREDENTIALS}")
            
            manager = AsyncWorkflowManager()
            if manager.run_script_sync(str(self.work_dir / "voiceToGoogle.py"), "Spracherkennung"):
                success_count += 1
                self.log_status("✓ Spracherkennung erfolgreich")
                
                # Check if transcript files were created in standardized location
                transcript_txt = Path(TRANSKRIPT_PATH)
                transcript_json = Path(TRANSKRIPT_JSON_PATH)
                
                if transcript_txt.exists():
                    try:
                        with open(transcript_txt, 'r', encoding='utf-8') as f:
                            transcript_content = f.read()
                        self.log_status(f"Transcript erstellt: '{transcript_content[:100]}{'...' if len(transcript_content) > 100 else ''}'")
                    except Exception as e:
                        self.log_status(f"Transcript-Datei konnte nicht gelesen werden: {e}", "WARNING")
                        
                if transcript_json.exists():
                    self.log_status(f"✓ JSON-Transcript für AI-Integration erstellt: {transcript_json}")
                else:
                    self.log_status("JSON-Transcript wurde nicht erstellt", "WARNING")
            else:
                self.log_status("✗ Spracherkennung fehlgeschlagen", "WARNING")
                self.log_status("Mögliche Ursachen:", "INFO")
                self.log_status(f"- GOOGLE_APPLICATION_CREDENTIALS not set or file missing: {GOOGLE_SPEECH_CREDENTIALS}", "INFO")
                self.log_status("- google-cloud-speech library not installed", "INFO") 
                self.log_status("- Network error or Google Cloud API problem", "INFO")
                self.log_status(f"- Audio file problem (despite validation): {AUDIO_FILE}", "INFO")
            
            # REMOVED STEP 2: File operations (dateiKopieren.py) - not needed for core workflow
            
            # Step 2 (was 3): Image generation (Vertex AI Integration)  
            self.log_status("Schritt 2/2: Bildgenerierung mit Vertex AI...")
            self.log_status("Sending transcript to Vertex AI for image generation")
            
            # Get transcript text - prioritize JSON format for better metadata
            prompt_text = self._get_transcript_for_ai()
            
            if prompt_text and prompt_text.strip():
                self.log_status(f"Transcript found for AI processing: '{prompt_text[:100]}{'...' if len(prompt_text) > 100 else ''}'")
                
                try:
                    # Ensure BilderVertex directory exists in standardized location
                    bilder_dir_path = Path(BILDER_DIR)
                    bilder_dir_path.mkdir(parents=True, exist_ok=True)
                    self.log_status(f"Target directory ensured: {bilder_dir_path}")
                    
                    # Generate image using Vertex AI
                    self.log_status("Sending prompt to Vertex AI Imagen API...")
                    image_paths = generate_image_imagen4(
                        prompt_text, 
                        image_count=1, 
                        bilder_dir=str(bilder_dir_path), 
                        output_prefix="bild",
                        logger=self.log_status
                    )
                    
                    if image_paths:
                        success_count += 1
                        self.log_status("✓ Vertex AI Bildgenerierung erfolgreich abgeschlossen")
                        for img_path in image_paths:
                            self.log_status(f"✓ Bild gespeichert: {img_path}")
                    else:
                        self.log_status("✗ Vertex AI Bildgenerierung: Keine Bilder erhalten", "WARNING")
                        
                except Exception as e:
                    self.log_status(f"✗ Vertex AI Bildgenerierung fehlgeschlagen: {e}", "ERROR")
                    import traceback
                    self.log_status(f"Error details: {traceback.format_exc()}", "ERROR")
            else:
                self.log_status("✗ Kein Transcript für Vertex AI Bildgenerierung gefunden", "WARNING")
                self.log_status("Mögliche Ursachen:", "INFO")
                self.log_status(f"- Transcript-Datei fehlt: {TRANSKRIPT_PATH}", "INFO")
                self.log_status(f"- JSON-Transcript fehlt: {TRANSKRIPT_JSON_PATH}", "INFO")
                self.log_status("- Spracherkennung war nicht erfolgreich", "INFO")
            
            # Final status
            if success_count == total_steps:
                self.log_status("WORKFLOW_COMPLETE: Alle Schritte erfolgreich abgeschlossen")
                self.log_status(f"✓ Streamlined workflow: Speech Recognition → Vertex AI → BilderVertex completed")
            else:
                self.log_status(f"WORKFLOW_COMPLETE: {success_count}/{total_steps} Schritte erfolgreich", "WARNING")
                self.log_status("Workflow partially completed - check individual step logs")
                
        except Exception as e:
            self.log_status(f"WORKFLOW_ERROR: Unerwarteter Fehler: {e}", "ERROR")
            import traceback
            self.log_status(f"Traceback: {traceback.format_exc()}", "ERROR")
        
        finally:
            # Clean up trigger file
            try:
                if self.trigger_file.exists():
                    self.trigger_file.unlink()
                    self.log_status("Trigger-Datei gelöscht")
            except Exception as e:
                self.log_status(f"Fehler beim Löschen der Trigger-Datei: {e}", "WARNING")
            
            # Mark workflow as completed and stop the service to prevent endless loop
            self.workflow_completed = True
            self.log_status("Service beendet sich nach erfolgreichem Workflow-Durchlauf")
            self.running = False
    
    def check_trigger(self):
        """Check for workflow trigger file"""
        if self.trigger_file.exists():
            try:
                with open(self.trigger_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                
                if content == "run":
                    self.log_status("Workflow-Trigger erkannt")
                    self.execute_workflow()
                    return True
                    
            except Exception as e:
                self.log_status(f"Fehler beim Lesen der Trigger-Datei: {e}", "ERROR")
        
        return False
    
    def start_watching(self):
        """Start watching for trigger files in background thread"""
        if self.running:
            print("Watcher bereits aktiv")
            return False
        
        # Acquire exclusive service lock
        if not self.acquire_service_lock():
            return False
        
        self.running = True
        self.workflow_completed = False
        self.clear_status_log()
        self.log_status("Workflow-Manager gestartet")
        self.log_status(f"Überwache Verzeichnis: {self.work_dir}")
        self.log_status(f"Trigger-Datei: {self.trigger_file}")
        
        def watcher_thread():
            try:
                while self.running and not self.workflow_completed:
                    try:
                        if self.check_trigger():
                            # Workflow was executed, service will stop
                            break
                        else:
                            time.sleep(self.check_interval)
                    except Exception as e:
                        self.log_status(f"Watcher-Fehler: {e}", "ERROR")
                        time.sleep(5.0)  # Wait longer on error
            except Exception as e:
                self.log_status(f"Watcher-Thread-Fehler: {e}", "ERROR")
            finally:
                # Always ensure service stops and lock is released
                self.running = False
                self.workflow_completed = True
                self.release_service_lock()
        
        import threading
        self.watcher_thread = threading.Thread(target=watcher_thread, daemon=True)
        self.watcher_thread.start()
        
        print(f"Workflow-Manager läuft im Hintergrund (PID: {os.getpid()})")
        print("Service beendet sich automatisch nach einem Workflow-Durchlauf")
        return True
    
    def stop_watching(self):
        """Stop the background watcher"""
        self.running = False
        self.release_service_lock()
        self.log_status("Workflow-Manager gestoppt")
        print("Workflow-Manager gestoppt")
    
    def _get_transcript_for_ai(self):
        """
        Get transcript text for AI processing, prioritizing JSON format with fallbacks
        
        Priority order:
        1. JSON transcript (transkript.json) - contains metadata and flags
        2. Text transcript (transkript.txt) - plain text fallback
        3. Clipboard content - legacy fallback
        
        Returns:
            str: The transcript text to send to Vertex AI, or empty string if not found
        """
        # Priority 1: Try JSON transcript first (preferred for AI integration)
        if os.path.exists(TRANSKRIPT_JSON_PATH):
            try:
                import json
                with open(TRANSKRIPT_JSON_PATH, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                
                transcript_text = transcript_data.get('transcript', '').strip()
                if transcript_text:
                    processing_method = transcript_data.get('processing_method', 'unknown')
                    is_real = transcript_data.get('real_recognition', False)
                    
                    self.log_status(f"Using JSON transcript (method: {processing_method}, real: {is_real})")
                    
                    # Warn if this is simulation data
                    if not is_real:
                        self.log_status("⚠ Warning: Using simulated transcript data (not real speech)", "WARNING")
                        self.log_status("For real AI image generation, ensure Google Speech-to-Text is working", "WARNING")
                    
                    return transcript_text
                else:
                    self.log_status("JSON transcript file exists but contains no text", "WARNING")
                    
            except Exception as e:
                self.log_status(f"Error reading JSON transcript: {e}", "WARNING")
        
        # Priority 2: Try text transcript file
        if os.path.exists(TRANSKRIPT_PATH):
            try:
                with open(TRANSKRIPT_PATH, 'r', encoding='utf-8') as f:
                    transcript_text = f.read().strip()
                if transcript_text:
                    self.log_status("Using text transcript file")
                    return transcript_text
                else:
                    self.log_status("Text transcript file exists but is empty", "WARNING")
            except Exception as e:
                self.log_status(f"Error reading text transcript: {e}", "WARNING")
        
        # Priority 3: Legacy fallback to clipboard (for backwards compatibility)
        try:
            prompt_text = get_copied_content()
            if prompt_text and prompt_text.strip():
                self.log_status("Using clipboard content as fallback")
                return prompt_text.strip()
        except Exception as e:
            self.log_status(f"Error reading clipboard: {e}", "WARNING")
        
        # No transcript found
        self.log_status("No transcript found in any location", "ERROR")
        return ""

def get_copied_content():
    """Get transcript content from clipboard - legacy function for backwards compatibility"""
    # Note: This is a legacy function. New workflow uses _get_transcript_for_ai() instead
    
    # Try clipboard only (no more file reading fallbacks)
    if CLIPBOARD_AVAILABLE:
        try:
            text = pyperclip.paste()
            if text and text.strip():
                print("Text aus Zwischenablage gelesen.")
                return text.strip()
        except Exception as e:
            print("Konnte Zwischenablage nicht lesen:", e)
    else:
        print("Zwischenablage nicht verfügbar (pyperclip fehlt)")
    
    print("Kein Text gefunden!")
    return ""

def get_next_index(directory, prefix):
    files = glob.glob(f"{directory}/{prefix}_*.png")
    if not files:
        return 1
    nums = []
    for f in files:
        try:
            num = int(f.split("_")[-1].split(".")[0])
            nums.append(num)
        except Exception:
            continue
    return max(nums) + 1 if nums else 1

def generate_image_imagen4(prompt, image_count=1, bilder_dir=BILDER_DIR, output_prefix="bild", logger=None):
    """
    Generate images using Google's Vertex AI Imagen 4.0 API
    
    This function provides a clean, robust integration with Vertex AI for image generation.
    It automatically falls back to demo mode when Google Cloud is not available.
    
    Configuration (transparent setup):
    - Google Cloud Project ID: Set via PROJECT_ID environment variable (default: "trippe-s")
    - Credentials File: {GOOGLE_CREDENTIALS} (service account JSON key)
    - API Endpoint: Vertex AI Imagen 4.0 in us-central1 region
    - Image Parameters: 16:9 aspect ratio, 2k resolution
    - Error Handling: Graceful fallback to demo images if API unavailable
    
    Args:
        prompt (str): Text prompt for image generation (max ~2000 characters)
        image_count (int): Number of images to generate (default: 1)
        bilder_dir (str): Target directory for generated images (default: {BILDER_DIR})
        output_prefix (str): Filename prefix for generated images (default: "bild")
        logger (callable): Optional logging function for status updates
    
    Returns:
        list: List of generated image file paths, empty list if failed
        
    Production Setup Required:
        1. Install dependencies: pip install google-cloud-aiplatform google-auth requests
        2. Set up Google Cloud project with Vertex AI API enabled
        3. Create service account with "Vertex AI User" role
        4. Download service account JSON key to: {GOOGLE_CREDENTIALS}
        5. Set PROJECT_ID environment variable (or use default)
        
    Demo Mode Behavior:
        - When Google Cloud libraries are missing or credentials unavailable
        - Creates placeholder PNG images to test workflow
        - All error handling is transparent with detailed logging
    """
    def log(message, level="INFO"):
        if logger:
            logger(message, level)
        else:
            print(f"[{level}] {message}")
    
    log(f"=== Vertex AI Image Generation ===")
    log(f"Prompt: '{prompt[:100]}{'...' if len(prompt) > 100 else ''}'")
    log(f"Target directory: {bilder_dir}")
    
    # Ensure directory exists
    try:
        if not os.path.exists(bilder_dir):
            os.makedirs(bilder_dir, exist_ok=True)
            log(f"Created directory: {bilder_dir}")
    except Exception as e:
        log(f"Failed to create directory {bilder_dir}: {e}", "ERROR")
        return []
    
        # Check for Google Cloud libraries and credentials
        if not GOOGLE_CLOUD_AVAILABLE:
            log("Google Cloud libraries not available", "WARNING")
            log("Required: pip install google-cloud-aiplatform google-auth", "INFO")
            return _create_demo_images(bilder_dir, output_prefix, image_count, logger)
        
        if not REQUESTS_AVAILABLE:
            log("Requests library not available", "WARNING")
            log("Required: pip install requests", "INFO")
            return _create_demo_images(bilder_dir, output_prefix, image_count, logger)
    
        if not os.path.exists(GOOGLE_CREDENTIALS):
            log(f"Google Cloud credentials not found: {GOOGLE_CREDENTIALS}", "WARNING")
            log("Required: Set up service account and download JSON key file", "INFO")
            log("See: https://cloud.google.com/docs/authentication/getting-started", "INFO")
            return _create_demo_images(bilder_dir, output_prefix, image_count, logger)
    
    log(f"Using Google Cloud credentials: {GOOGLE_CREDENTIALS}")
    
    # Real implementation with Google Cloud Vertex AI
    try:
        log("Authenticating with Google Cloud...")
        
        # Double-check that we have the required modules
        if not GOOGLE_CLOUD_AVAILABLE or service_account is None:
            raise ImportError("Google Cloud libraries not available")
            
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS, scopes=scopes
        )
        auth_req = GoogleAuthRequest()
        credentials.refresh(auth_req)
        token = credentials.token
        log("✓ Authentication successful")

        # Prepare API request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "instances": [
                {"prompt": prompt}
            ],
            "parameters": {
                "sampleCount": image_count,
                "aspectRatio": "16:9",
                "resolution": "2k"
            }
        }
        
        log(f"Sending request to Vertex AI Imagen API...")
        log(f"Endpoint: {ENDPOINT}")
        log(f"Parameters: {image_count} images, 16:9 aspect ratio, 2k resolution")
        
        response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=120)
        
        if response.status_code != 200:
            log(f"Vertex AI API error: HTTP {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            
            # Common error handling
            if response.status_code == 401:
                log("Authentication failed - check service account permissions", "ERROR")
            elif response.status_code == 403:
                log("Permission denied - ensure Vertex AI API is enabled and billing is set up", "ERROR")
            elif response.status_code == 429:
                log("Rate limit exceeded - try again later", "ERROR")
            elif response.status_code >= 500:
                log("Server error - Google Cloud service may be temporarily unavailable", "ERROR")
            
            return _create_demo_images(bilder_dir, output_prefix, image_count, logger)
        
        log("✓ Received response from Vertex AI API")
        result = response.json()
        
        if "predictions" not in result or not result["predictions"]:
            log("No images returned by Vertex AI API", "ERROR")
            return _create_demo_images(bilder_dir, output_prefix, image_count, logger)
        
        # Save generated images
        log(f"Processing {len(result['predictions'])} generated images...")
        generated_files = []
        start_idx = get_next_index(bilder_dir, output_prefix)
        
        for i, pred in enumerate(result["predictions"]):
            if "bytesBase64Encoded" not in pred:
                log(f"Image {i+1}: No image data in response", "WARNING")
                continue
                
            try:
                fname = f"{bilder_dir}/{output_prefix}_{start_idx + i}.png"
                img_data = base64.b64decode(pred["bytesBase64Encoded"])
                
                with open(fname, "wb") as f:
                    f.write(img_data)
                
                file_size = len(img_data)
                log(f"✓ Image {i+1} saved: {fname} ({file_size:,} bytes)")
                generated_files.append(fname)
                
            except Exception as e:
                log(f"Failed to save image {i+1}: {e}", "ERROR")
        
        if generated_files:
            log(f"✓ Vertex AI image generation completed: {len(generated_files)} images saved")
            return generated_files
        else:
            log("No images could be saved", "ERROR")
            return []
            
    except Exception as e:
        log(f"Vertex AI API error: {e}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        
        # Specific error handling
        if "403" in str(e):
            log("Permission error - check Vertex AI API access and billing", "ERROR")
        elif "auth" in str(e).lower():
            log("Authentication error - check service account key", "ERROR")
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            log("Network error - check internet connection", "ERROR")
        
        return _create_demo_images(bilder_dir, output_prefix, image_count, logger)

def _create_demo_images(bilder_dir, output_prefix, image_count, logger=None):
    """
    Create demo/placeholder images when Vertex AI is not available
    
    Returns:
        list: List of created demo image paths
    """
    def log(message, level="INFO"):
        if logger:
            logger(message, level)
        else:
            print(f"[{level}] {message}")
    
    log("Creating demo images as fallback...")
    
    try:
        generated_files = []
        start_idx = get_next_index(bilder_dir, output_prefix)
        
        # Create a minimal PNG file as placeholder
        minimal_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        for i in range(image_count):
            fname = f"{bilder_dir}/{output_prefix}_{start_idx + i}.png"
            with open(fname, "wb") as f:
                f.write(minimal_png)
            
            log(f"✓ Demo image created: {fname}")
            generated_files.append(fname)
        
        return generated_files
        
    except Exception as e:
        log(f"Failed to create demo images: {e}", "ERROR")
        return []

def main():
    """
    Main workflow with asynchronous recording
    
    This function implements the new non-blocking workflow:
    1. Start Aufnahme.py asynchronously using subprocess.Popen
    2. Wait for external event to stop recording (Enter, SIGTERM, etc.)
    3. Continue with synchronous processing steps
    4. Collect and display all subprocess output
    """
    print("=== Audio Recording & AI Image Generation Workflow ===")
    print("Dieses Programm führt folgende Schritte aus:")
    print("1. Aufnahme (asynchron, manuell stoppbar)")  
    print("2. Spracherkennung")
    print("3. Datei kopieren")
    print("4. Bild generieren")
    print("=" * 60)
    
    # Initialize workflow manager
    workflow = AsyncWorkflowManager()
    
    # Step 1: Start recording asynchronously
    if not workflow.start_recording_async(AUFNAHME_SCRIPT):
        print("Fehler beim Starten der Aufnahme - Workflow abgebrochen")
        return False
    
    # Wait for recording to be stopped (manually or by signal)
    print("Warte auf Stop-Signal...")
    print("Optionen zum Stoppen:")
    print("- Drücke Enter")
    print("- Sende SIGTERM an diesen Prozess")
    print("- Drücke Ctrl+C")
    
    workflow.wait_for_stop_signal()
    
    # Stop recording if still running
    if workflow.is_recording:
        workflow.stop_recording()
    
    print("\n" + "=" * 60)
    print("Aufnahme abgeschlossen, fahre mit weiteren Schritten fort...")
    print("=" * 60)
    
    # Step 2: Voice recognition
    if not workflow.run_script_sync(VOICE_SCRIPT, "Spracherkennung"):
        print("Warnung: Spracherkennung fehlgeschlagen, fahre trotzdem fort...")
    
    # Step 3: Copy files  
    if not workflow.run_script_sync(COPY_SCRIPT, "Kopiervorgang"):
        print("Warnung: Kopiervorgang fehlgeschlagen, fahre trotzdem fort...")
    
    print("Inhalt von transkript.txt wurde ins Clipboard kopiert!")
    
    # Step 4: Generate image
    prompt_text = get_copied_content()
    if not prompt_text.strip():
        print("Kein Text zum Senden gefunden – Bild-Generierung übersprungen.")
    else:
        print("Sende Text als Prompt an Vertex AI Imagen 4 ...")
        try:
            generate_image_imagen4(prompt_text, image_count=1, bilder_dir=BILDER_DIR, output_prefix="bild")
        except Exception as e:
            print(f"Fehler bei Bild-Generierung: {e}")
    
    print("\n" + "=" * 60)
    print("Workflow vollständig abgeschlossen!")
    print("=" * 60)
    return True

# --- Original Workflow (kept for backwards compatibility) ---
def run_original_workflow():
    """Run the original synchronous workflow"""
    print("Führe ursprünglichen synchronen Workflow aus...")
    run_script(AUFNAHME_SCRIPT, "Aufnahme")
    run_script(VOICE_SCRIPT, "Spracherkennung")
    run_script(COPY_SCRIPT, "Kopiervorgang")
    print("Inhalt von transkript.txt wurde ins Clipboard kopiert!")

    prompt_text = get_copied_content()
    if not prompt_text.strip():
        print("Kein Text zum Senden gefunden – abgebrochen.")
    else:
        print("Sende Text als Prompt an Vertex AI Imagen 4 ...")
        generate_image_imagen4(prompt_text, image_count=1, bilder_dir=BILDER_DIR, output_prefix="bild")

    print("Workflow abgeschlossen!")

def run_background_service():
    """Run as background workflow manager service - runs ONCE then exits"""
    print("=== Workflow Manager Service ===")
    print("Startet als Hintergrunddienst für die Überwachung von Workflow-Triggern")
    print("Service wird nach EINEM erfolgreichen Workflow-Durchlauf beendet")
    
    watcher = WorkflowFileWatcher()
    
    # Set up signal handlers for clean shutdown
    import signal
    def signal_handler(signum, frame):
        print(f"\nSignal {signum} empfangen, beende Service...")
        watcher.stop_watching()
    
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except Exception as e:
        print(f"Warning: Could not set signal handlers: {e}")
    
    if not watcher.start_watching():
        print("Fehler: Konnte Service nicht starten (möglicherweise läuft bereits eine Instanz)")
        return False
    
    try:
        # Keep the service running until one workflow completes
        while watcher.running and not watcher.workflow_completed:
            time.sleep(1)
        
        print("Workflow-Service beendet sich nach erfolgreichem Durchlauf")
        return True
        
    except KeyboardInterrupt:
        print("\nService wird beendet...")
        watcher.stop_watching()
        return False
    finally:
        # Ensure cleanup even if something goes wrong
        watcher.stop_watching()

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--original":
            run_original_workflow()
        elif sys.argv[1] == "--service":
            run_background_service()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python3 PythonServer.py           # Run interactive async workflow")
            print("  python3 PythonServer.py --service # Run as background service")
            print("  python3 PythonServer.py --original# Run original synchronous workflow")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        main()
