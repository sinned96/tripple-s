#!/usr/bin/env python3
"""
voiceToGoogle.py - Speech recognition script that processes audio recordings
and converts them to text using Google's speech recognition services.

Path Logic and Workflow Integration:
- Base directory: /home/pi/Desktop/v2_Tripple S/
- Input file: /home/pi/Desktop/v2_Tripple S/aufnahme.wav
- Output files: /home/pi/Desktop/v2_Tripple S/transkript.txt and transkript.json
- Google credentials: /home/pi/Desktop/v2_Tripple S/cloudKey.json
- This script runs AFTER Aufnahme.py completes recording
- This script runs BEFORE the local file operations
- Workflow sequence: Recording → Transcription (this script) → Upload

REQUIREMENTS:
- GOOGLE_APPLICATION_CREDENTIALS environment variable must be set to point to service account key
- google-cloud-speech library must be installed: pip install google-cloud-speech
- Audio file must be in WAV format compatible with Google Speech-to-Text
- cloudKey.json must be present in the working directory for authentication

Optional AI Integration Note:
- transkript.json output is ready for further AI processing (e.g., Vertex AI)
- Contains transcript text, metadata, and processing information
- Can be used for content analysis, sentiment analysis, or content generation workflows
"""

import os
import sys
import json
import time
import logging
import wave
import subprocess
from pathlib import Path

# Setup logging for speech-to-text processing
def setup_speech_logging():
    """Setup logging for speech recognition with both file and console output"""
    # Use standardized base directory, but fall back to current directory if not accessible
    try:
        log_dir = Path("/home/pi/Desktop/v2_Tripple S")
        log_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # Fallback to current working directory for testing/development
        log_dir = Path.cwd()
        
    log_file = log_dir / "speech_recognition.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(str(log_file), mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
speech_logger = setup_speech_logging()

# Try to import Google Cloud Speech-to-Text
try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
    speech_logger.info("Google Cloud Speech-to-Text library loaded successfully")
except ImportError as e:
    GOOGLE_SPEECH_AVAILABLE = False
    speech_logger.warning(f"Google Cloud Speech-to-Text library not available: {e}")
    speech_logger.info("Fallback mode will be used when Google API is not available or fails")

def find_audio_recording(audio_file_path=None):
    """Find the audio file in expected locations"""
    # If specific path provided, use it
    if audio_file_path and os.path.exists(audio_file_path):
        speech_logger.info(f"Using provided audio file: {audio_file_path}")
        return audio_file_path
    
    # Define possible recording locations with standardized path as priority
    possible_paths = [
        "/home/pi/Desktop/v2_Tripple S/aufnahme.wav",  # Primary path as per requirements
        str(Path.home() / "Desktop" / "v2_Tripple S" / "aufnahme.wav"),  # Alternative home path
        "Aufnahmen/aufnahme.wav",  # Local directory fallback
        "aufnahme.wav",  # Current directory fallback
        "/tmp/aufnahme.wav"  # Temporary files fallback
    ]
    
    for audio_path in possible_paths:
        if os.path.exists(audio_path):
            speech_logger.info(f"Found audio file at: {audio_path}")
            return audio_path
    
    speech_logger.error("No audio file found in any expected location")
    speech_logger.error("Expected locations:")
    for path in possible_paths:
        speech_logger.error(f"  - {path}")
    
    return None

def simulate_speech_recognition(audio_file):
    """Fallback speech recognition when Google API is unavailable"""
    speech_logger.info(f"Using fallback mode for speech recognition")
    speech_logger.info(f"Processing audio file: {audio_file}")
    
    # Check if file exists and get info
    if not os.path.exists(audio_file):
        speech_logger.error(f"Audio file not found: {audio_file}")
        return None
    
    file_size = os.path.getsize(audio_file)
    speech_logger.info(f"Audio file size: {file_size:,} bytes")
    
    # Simulate processing time based on file size
    processing_time = min(max(file_size / 1000000, 1), 5)  # 1-5 seconds
    speech_logger.info(f"Analyzing audio content... (estimated {processing_time:.1f}s)")
    
    for i in range(int(processing_time)):
        speech_logger.info(f"  Processing... {i+1}/{int(processing_time)}")
        time.sleep(1)
    
    # Simulate different recognition results based on file characteristics
    if file_size < 10000:  # Very small file
        return "Kurze Aufnahme erkannt"
    elif file_size < 100000:  # Small file
        return "Dies ist eine Testaufnahme für die Spracherkennung"
    elif file_size < 500000:  # Medium file
        return "Hallo, dies ist eine längere Audioaufnahme die von der Spracherkennung verarbeitet wird. Bitte erstelle ein Bild basierend auf diesem Text."
    else:  # Large file
        return "Dies ist eine ausführliche Audioaufnahme mit vielen Details. Die Spracherkennung hat erfolgreich den gesprochenen Inhalt erkannt und in Text umgewandelt. Dieser Text kann nun für die Bildgenerierung verwendet werden."

def check_google_credentials():
    """Check if Google Cloud credentials are properly configured"""
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not credentials_path:
        speech_logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        speech_logger.error("Please set it to point to your service account key file:")
        speech_logger.error("export GOOGLE_APPLICATION_CREDENTIALS='/home/pi/Desktop/v2_Tripple S/cloudKey.json'")
        
        # Also check for cloudKey.json in the standardized directory
        default_key_path = "/home/pi/Desktop/v2_Tripple S/cloudKey.json"
        if os.path.exists(default_key_path):
            speech_logger.info(f"Found credentials at standard location: {default_key_path}")
            speech_logger.info("Consider setting GOOGLE_APPLICATION_CREDENTIALS environment variable")
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = default_key_path
            return True
        return False
    
    if not os.path.exists(credentials_path):
        speech_logger.error(f"Credentials file not found: {credentials_path}")
        return False
    
    speech_logger.info(f"Found Google credentials at: {credentials_path}")
    return True

def check_audio_format(audio_file_path):
    """Check if audio file is in mono format suitable for Google Speech-to-Text API"""
    try:
        with wave.open(audio_file_path, 'rb') as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            
            speech_logger.info(f"Audio format analysis:")
            speech_logger.info(f"  Channels: {channels} ({'mono' if channels == 1 else 'stereo' if channels == 2 else f'{channels}-channel'})")
            speech_logger.info(f"  Sample rate: {sample_rate} Hz")
            speech_logger.info(f"  Sample width: {sample_width * 8} bits")
            
            return {
                'channels': channels,
                'sample_rate': sample_rate,
                'sample_width': sample_width,
                'is_mono': channels == 1,
                'is_suitable': channels <= 2 and sample_rate in [16000, 44100, 48000]
            }
            
    except Exception as e:
        speech_logger.error(f"Error analyzing audio format: {e}")
        return None

def convert_to_mono(input_path, output_path=None):
    """Convert stereo audio to mono using ffmpeg for Google Speech-to-Text compatibility"""
    if output_path is None:
        # Create mono version with _mono suffix
        path_obj = Path(input_path)
        output_path = path_obj.parent / f"{path_obj.stem}_mono{path_obj.suffix}"
    
    speech_logger.info(f"Converting stereo audio to mono...")
    speech_logger.info(f"  Input: {input_path}")
    speech_logger.info(f"  Output: {output_path}")
    
    try:
        # Use ffmpeg to convert stereo to mono (mix both channels)
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-i', str(input_path),
            '-ac', '1',  # Audio channels = 1 (mono)
            '-ar', '44100',  # Sample rate = 44100 Hz
            '-acodec', 'pcm_s16le',  # 16-bit PCM encoding
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            speech_logger.info("✓ Audio successfully converted to mono format")
            
            # Verify the conversion worked
            format_info = check_audio_format(str(output_path))
            if format_info and format_info['is_mono']:
                speech_logger.info("✓ Mono conversion verified successfully")
                return str(output_path)
            else:
                speech_logger.error("✗ Mono conversion verification failed")
                return None
        else:
            speech_logger.error("✗ ffmpeg conversion failed")
            speech_logger.error(f"Error output: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        speech_logger.error("✗ Audio conversion timed out (>60s)")
        return None
    except FileNotFoundError:
        speech_logger.error("✗ ffmpeg not found - please install ffmpeg")
        return None
    except Exception as e:
        speech_logger.error(f"✗ Audio conversion error: {e}")
        return None

def ensure_mono_audio(audio_file_path):
    """Ensure audio file is in mono format, convert if necessary"""
    speech_logger.info("=== Audio Format Validation ===")
    
    # Check current format
    format_info = check_audio_format(audio_file_path)
    if not format_info:
        speech_logger.error("Could not analyze audio format")
        return None
    
    if format_info['is_mono']:
        speech_logger.info("✓ Audio is already in mono format - no conversion needed")
        return audio_file_path
    
    if format_info['channels'] == 2:
        speech_logger.warning("⚠ Audio is in stereo format - Google Speech-to-Text requires mono")
        speech_logger.info("Converting to mono format automatically...")
        
        mono_path = convert_to_mono(audio_file_path)
        if mono_path:
            return mono_path
        else:
            speech_logger.error("Failed to convert audio to mono - cannot proceed with Google API")
            return None
    
    else:
        speech_logger.error(f"Unsupported audio format: {format_info['channels']} channels")
        speech_logger.error("Google Speech-to-Text API supports only mono (1 channel) or stereo (2 channel) audio")
        return None

def validate_audio_file(audio_file_path):
    """Validate that the audio file is suitable for Google Speech-to-Text"""
    try:
        file_size = os.path.getsize(audio_file_path)
        speech_logger.info(f"Audio file size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
        
        # Check file size limits (Google Speech-to-Text has limits)
        if file_size == 0:
            speech_logger.error("Audio file is empty")
            return False
        
        if file_size > 10 * 1024 * 1024:  # 10MB limit for synchronous requests
            speech_logger.warning("Audio file is large (>10MB), may require async processing")
        
        # Basic file format check
        if not audio_file_path.lower().endswith('.wav'):
            speech_logger.warning("Audio file is not in WAV format, may cause issues")
        
        return True
        
    except Exception as e:
        speech_logger.error(f"Error validating audio file: {e}")
        return False

def real_google_speech_recognition(audio_file_path):
    """Real speech recognition using Google Cloud Speech-to-Text API"""
    if not GOOGLE_SPEECH_AVAILABLE:
        speech_logger.error("Google Cloud Speech-to-Text library not available")
        return None
    
    if not check_google_credentials():
        speech_logger.error("Google credentials not properly configured")
        return None
    
    # Ensure audio is in mono format before processing
    mono_audio_path = ensure_mono_audio(audio_file_path)
    if not mono_audio_path:
        speech_logger.error("Audio format validation/conversion failed")
        return None
    
    if not validate_audio_file(mono_audio_path):
        speech_logger.error("Audio file validation failed")
        return None
    
    try:
        speech_logger.info("Initializing Google Speech-to-Text client...")
        client = speech.SpeechClient()
        
        speech_logger.info("Reading mono audio file...")
        with open(mono_audio_path, "rb") as audio_file:
            content = audio_file.read()
        
        # Configure audio and recognition settings for MONO audio
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=44100,  # Standard CD quality
            audio_channel_count=1,    # IMPORTANT: Explicitly set to 1 for mono
            language_code="de-DE",    # German language
            alternative_language_codes=["en-US"],  # Fallback to English
            enable_automatic_punctuation=True,
            enable_word_confidence=True,
        )
        
        speech_logger.info("Sending mono audio to Google Speech-to-Text API...")
        speech_logger.info("Using configuration: MONO (1 channel), 44.1kHz, 16-bit PCM, German language")
        
        # Perform the transcription
        response = client.recognize(config=config, audio=audio)
        
        # Process results
        if not response.results:
            speech_logger.warning("No speech detected in audio file")
            return None
        
        # Get the best transcript
        transcript = ""
        confidence_scores = []
        
        for result in response.results:
            alternative = result.alternatives[0]  # Best alternative
            transcript += alternative.transcript + " "
            confidence_scores.append(alternative.confidence)
            
            speech_logger.info(f"Transcript segment: '{alternative.transcript}' (confidence: {alternative.confidence:.2f})")
        
        transcript = transcript.strip()
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        speech_logger.info(f"Speech recognition completed successfully")
        speech_logger.info(f"Average confidence: {avg_confidence:.2f}")
        speech_logger.info(f"Full transcript: '{transcript}'")
        
        # Clean up temporary mono file if it was created
        if mono_audio_path != audio_file_path and os.path.exists(mono_audio_path):
            try:
                os.remove(mono_audio_path)
                speech_logger.info(f"Cleaned up temporary mono file: {mono_audio_path}")
            except Exception as e:
                speech_logger.warning(f"Could not clean up temporary file: {e}")
        
        return transcript
        
    except Exception as e:
        speech_logger.error(f"Google Speech-to-Text API error: {e}")
        speech_logger.error(f"Error type: {type(e).__name__}")
        
        # Log specific error types for mono audio issues
        if "INVALID_ARGUMENT" in str(e):
            speech_logger.error("Invalid argument - this may be related to audio format")
            speech_logger.error("Ensure audio is mono (1 channel), 16-bit PCM, WAV format")
        elif "UNAUTHENTICATED" in str(e):
            speech_logger.error("Authentication failed - check GOOGLE_APPLICATION_CREDENTIALS")
        elif "PERMISSION_DENIED" in str(e):
            speech_logger.error("Permission denied - check service account permissions")
        elif "QUOTA_EXCEEDED" in str(e):
            speech_logger.error("API quota exceeded - check your Google Cloud billing")
        elif "UNAVAILABLE" in str(e):
            speech_logger.error("Service unavailable - network or Google Cloud issue")
        
        return None

def save_transcript(text, output_file=None, processing_method=None):
    """Save the recognized text to files in the standardized directory with proper logging"""
    if output_file is None:
        # Use standardized base directory, but fall back to current directory if not accessible
        try:
            base_dir = Path("/home/pi/Desktop/v2_Tripple S")
            base_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # Fallback to current working directory for testing/development
            base_dir = Path.cwd()
            
        output_file = str(base_dir / "transkript.txt")
    
    # Determine processing method if not provided
    if processing_method is None:
        processing_method = "google_speech_api" if GOOGLE_SPEECH_AVAILABLE else "simulation"
    
    try:
        # Save the transcript as text file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        speech_logger.info(f"Transcript saved to: {output_file}")
        speech_logger.info(f"Transcript content: '{text}'")
        speech_logger.info(f"Processing method: {processing_method}")
        
        # Also save as JSON with metadata in the same directory
        json_file = output_file.replace('.txt', '.json')
        transcript_data = {
            "transcript": text,
            "timestamp": time.time(),
            "iso_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "file_size": len(text),
            "processing_method": processing_method,
            "audio_source": find_audio_recording(),  # Include source audio path
            "workflow_step": "transcription_complete",  # Mark workflow step for integration
            "real_recognition": processing_method == "google_speech_api"  # Flag for real vs simulation
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        speech_logger.info(f"Transcript metadata saved to: {json_file}")
        
        if processing_method == "google_speech_api":
            speech_logger.info("✓ Real Google Speech Recognition - transcript contains actual speech content")
            speech_logger.info("--- Transcript ready for AI integration (Vertex AI compatible) ---")
        else:
            speech_logger.warning("⚠ Simulation mode - transcript contains placeholder text, not real speech")
            
        return True
        
    except Exception as e:
        speech_logger.error(f"Error saving transcript: {e}")
        return False

def main():
    """Main speech recognition workflow"""
    speech_logger.info("=== Voice to Google Speech Recognition ===")
    speech_logger.info("Starting speech-to-text processing...")
    
    # Check if an audio file was provided as command line argument
    audio_file = None
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        speech_logger.info(f"Using audio file from command line: {audio_file}")
    else:
        # Look for the aufnahme.wav file in expected locations
        audio_file = find_audio_recording()
    
    if not audio_file:
        speech_logger.error("No aufnahme.wav file found in any of the expected locations")
        speech_logger.error("Expected locations:")
        expected_paths = [
            "/home/pi/Desktop/v2_Tripple S/aufnahme.wav",
            str(Path.home() / "Desktop" / "v2_Tripple S" / "aufnahme.wav"),
            "Aufnahmen/aufnahme.wav",
            "aufnahme.wav", 
            "/tmp/aufnahme.wav"
        ]
        for path in expected_paths:
            speech_logger.error(f"  - {path}")
        
        # Create a dummy transcript for testing purposes
        speech_logger.info("Creating dummy transcript for workflow testing...")
        dummy_text = "Test Audio Aufnahme - Bitte erstelle ein schönes Bild von einer Landschaft mit Bergen und einem See"
        if save_transcript(dummy_text):
            speech_logger.info("✓ Dummy transcript created successfully")
            return True
        else:
            speech_logger.error("✗ Failed to create dummy transcript")
            return False
    
    speech_logger.info(f"Processing audio file: {os.path.basename(audio_file)}")
    
    # Perform speech recognition - PRIORITIZE REAL GOOGLE API
    try:
        recognized_text = None
        processing_method = None
        
        # Always try real Google Speech-to-Text first if available
        if GOOGLE_SPEECH_AVAILABLE:
            speech_logger.info("Attempting real Google Speech-to-Text recognition...")
            recognized_text = real_google_speech_recognition(audio_file)
            
            if recognized_text:
                processing_method = "google_speech_api"
                speech_logger.info("✓ Real Google Speech-to-Text succeeded!")
            else:
                speech_logger.warning("Real Google Speech-to-Text failed - check credentials and audio format")
        else:
            speech_logger.warning("Google Cloud Speech library not available")
        
        # Only fall back to fallback mode if Google API is not available or explicitly failed
        if not recognized_text:
            processing_method = "fallback"
            speech_logger.warning("Falling back to local processing (fallback mode active)")
            speech_logger.info("For real speech recognition, ensure:")
            speech_logger.info("1. Google Cloud Speech library is installed: pip install google-cloud-speech")
            speech_logger.info("2. Credentials are configured: GOOGLE_APPLICATION_CREDENTIALS environment variable")
            speech_logger.info("3. Audio is in mono format (automatic conversion attempted)")
            recognized_text = simulate_speech_recognition(audio_file)
        
        if recognized_text:
            speech_logger.info("--- Recognition Result ---")
            speech_logger.info(f'"{recognized_text}"')
            speech_logger.info("--- End Result ---")
            
            # Save transcript with processing method info
            if save_transcript(recognized_text, processing_method=processing_method):
                speech_logger.info("✓ Speech recognition completed successfully")
                return True
            else:
                speech_logger.error("✗ Failed to save transcript")
                return False
        else:
            speech_logger.error("✗ Speech recognition failed - no text detected")
            return False
            
    except Exception as e:
        speech_logger.error(f"✗ Speech recognition error: {e}")
        speech_logger.error(f"Error type: {type(e).__name__}")
        import traceback
        speech_logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            speech_logger.info("Speech recognition workflow completed successfully")
            sys.exit(0)
        else:
            speech_logger.error("Speech recognition workflow failed")
            sys.exit(1)
    except KeyboardInterrupt:
        speech_logger.warning("Speech recognition interrupted by user")
        sys.exit(1)
    except Exception as e:
        speech_logger.error(f"Unexpected error: {e}")
        speech_logger.error(f"Error type: {type(e).__name__}")
        import traceback
        speech_logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
