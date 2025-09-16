#!/usr/bin/env python3
"""
programmSendFile.py - Server upload functionality for audio files

This script transfers aufnahme.wav from the local directory to the target server.
It supports multiple upload methods (SCP, SFTP, rsync) and includes comprehensive
error handling and logging.

Path Logic and Workflow Integration:
- Source file: /home/pi/Desktop/v2_Tripple S/aufnahme.wav
- Target server path: /home/server/XYZ/aufnahme.wav
- This script runs AFTER voiceToGoogle.py completes transcription
- Workflow sequence: Recording → Transcription → Upload (this script)

Required for server upload:
- SSH key authentication configured for target server
- Network connectivity to target server
- Proper permissions on target server directory

Optional AI Integration Note:
- transkript.json can be exported for further AI processing (e.g., Vertex AI)
- The transcript data is available in JSON format with metadata
- Integration point for additional AI workflows or content analysis
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
import json

# Setup logging for upload operations
def setup_upload_logging():
    """Setup logging for upload operations with both file and console output"""
    log_dir = Path("/home/pi/Desktop/v2_Tripple S")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "upload.log"
    
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
upload_logger = setup_upload_logging()

# Standardized paths as per requirements
BASE_DIR = Path("/home/pi/Desktop/v2_Tripple S")
AUDIO_FILE = BASE_DIR / "aufnahme.wav"
TRANSCRIPT_FILE = BASE_DIR / "transkript.json"
CLOUD_KEY_FILE = BASE_DIR / "cloudKey.json"

# Server configuration
SERVER_HOST = os.getenv('UPLOAD_SERVER_HOST', 'your-server.example.com')
SERVER_USER = os.getenv('UPLOAD_SERVER_USER', 'pi')
SERVER_PATH = '/home/server/XYZ/aufnahme.wav'
SSH_KEY_PATH = os.getenv('SSH_KEY_PATH', '~/.ssh/id_rsa')

class AudioUploader:
    """Handles uploading of audio files to the target server"""
    
    def __init__(self):
        self.upload_methods = ['scp', 'rsync', 'sftp']
        self.last_upload_time = None
        
    def validate_source_file(self, file_path):
        """Validate that the source audio file exists and is valid"""
        try:
            if not file_path.exists():
                upload_logger.error(f"Source file not found: {file_path}")
                return False
                
            file_size = file_path.stat().st_size
            if file_size == 0:
                upload_logger.error(f"Source file is empty: {file_path}")
                return False
                
            upload_logger.info(f"Source file validated: {file_path}")
            upload_logger.info(f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
            return True
            
        except Exception as e:
            upload_logger.error(f"Error validating source file: {e}")
            return False
    
    def test_server_connectivity(self):
        """Test SSH connectivity to the target server"""
        try:
            upload_logger.info(f"Testing connectivity to {SERVER_USER}@{SERVER_HOST}")
            
            # Test SSH connection
            test_cmd = [
                'ssh',
                '-i', os.path.expanduser(SSH_KEY_PATH),
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'BatchMode=yes',  # Non-interactive
                f'{SERVER_USER}@{SERVER_HOST}',
                'echo "Connection test successful"'
            ]
            
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                upload_logger.info("✓ Server connectivity test successful")
                return True
            else:
                upload_logger.error(f"Server connectivity test failed (exit code: {result.returncode})")
                if result.stderr:
                    upload_logger.error(f"SSH error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            upload_logger.error("Server connectivity test timed out")
            return False
        except Exception as e:
            upload_logger.error(f"Error testing server connectivity: {e}")
            return False
    
    def upload_via_scp(self, source_file):
        """Upload file using SCP"""
        try:
            upload_logger.info("Attempting upload via SCP...")
            
            # Ensure target directory exists on server
            mkdir_cmd = [
                'ssh',
                '-i', os.path.expanduser(SSH_KEY_PATH),
                '-o', 'StrictHostKeyChecking=no',
                f'{SERVER_USER}@{SERVER_HOST}',
                f'mkdir -p "{os.path.dirname(SERVER_PATH)}"'
            ]
            
            mkdir_result = subprocess.run(mkdir_cmd, capture_output=True, text=True, timeout=30)
            if mkdir_result.returncode != 0:
                upload_logger.warning(f"Could not ensure target directory exists: {mkdir_result.stderr}")
            
            # Upload the file
            scp_cmd = [
                'scp',
                '-i', os.path.expanduser(SSH_KEY_PATH),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=30',
                str(source_file),
                f'{SERVER_USER}@{SERVER_HOST}:{SERVER_PATH}'
            ]
            
            upload_logger.info(f"Running SCP command: {' '.join(scp_cmd[:-2])} <source> <target>")
            
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for large files
            )
            
            if result.returncode == 0:
                upload_logger.info("✓ SCP upload completed successfully")
                return True
            else:
                upload_logger.error(f"SCP upload failed (exit code: {result.returncode})")
                if result.stderr:
                    upload_logger.error(f"SCP error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            upload_logger.error("SCP upload timed out")
            return False
        except Exception as e:
            upload_logger.error(f"Error during SCP upload: {e}")
            return False
    
    def upload_via_rsync(self, source_file):
        """Upload file using rsync with progress and resume capability"""
        try:
            upload_logger.info("Attempting upload via rsync...")
            
            rsync_cmd = [
                'rsync',
                '-avz',  # Archive mode, verbose, compress
                '--progress',
                '--partial',  # Keep partial files for resume
                '-e', f'ssh -i {os.path.expanduser(SSH_KEY_PATH)} -o StrictHostKeyChecking=no',
                str(source_file),
                f'{SERVER_USER}@{SERVER_HOST}:{SERVER_PATH}'
            ]
            
            upload_logger.info(f"Running rsync command: {' '.join(rsync_cmd[:-2])} <source> <target>")
            
            result = subprocess.run(
                rsync_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                upload_logger.info("✓ Rsync upload completed successfully")
                if result.stdout:
                    # Log rsync output for transfer statistics
                    upload_logger.info(f"Transfer details: {result.stdout.split()[-1] if result.stdout.split() else 'N/A'}")
                return True
            else:
                upload_logger.error(f"Rsync upload failed (exit code: {result.returncode})")
                if result.stderr:
                    upload_logger.error(f"Rsync error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            upload_logger.error("Rsync upload timed out")
            return False
        except Exception as e:
            upload_logger.error(f"Error during rsync upload: {e}")
            return False
    
    def verify_upload(self, source_file):
        """Verify that the upload was successful by comparing file sizes"""
        try:
            upload_logger.info("Verifying upload...")
            
            # Get local file size
            local_size = source_file.stat().st_size
            
            # Get remote file size
            remote_size_cmd = [
                'ssh',
                '-i', os.path.expanduser(SSH_KEY_PATH),
                '-o', 'StrictHostKeyChecking=no',
                f'{SERVER_USER}@{SERVER_HOST}',
                f'stat -c %s "{SERVER_PATH}" 2>/dev/null || echo "0"'
            ]
            
            result = subprocess.run(remote_size_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    remote_size = int(result.stdout.strip())
                    upload_logger.info(f"Local file size: {local_size:,} bytes")
                    upload_logger.info(f"Remote file size: {remote_size:,} bytes")
                    
                    if local_size == remote_size and remote_size > 0:
                        upload_logger.info("✓ Upload verification successful - file sizes match")
                        return True
                    else:
                        upload_logger.error(f"Upload verification failed - size mismatch (local: {local_size}, remote: {remote_size})")
                        return False
                        
                except ValueError:
                    upload_logger.error(f"Could not parse remote file size: '{result.stdout.strip()}'")
                    return False
            else:
                upload_logger.error("Could not verify remote file size")
                return False
                
        except Exception as e:
            upload_logger.error(f"Error verifying upload: {e}")
            return False
    
    def upload_file(self, source_file=None):
        """Main upload method that tries different upload methods"""
        if source_file is None:
            source_file = AUDIO_FILE
            
        upload_logger.info("=== Audio File Upload Process ===")
        upload_logger.info(f"Source: {source_file}")
        upload_logger.info(f"Target: {SERVER_USER}@{SERVER_HOST}:{SERVER_PATH}")
        
        # Validate source file
        if not self.validate_source_file(source_file):
            return False
        
        # Test server connectivity
        if not self.test_server_connectivity():
            upload_logger.error("Server connectivity test failed - aborting upload")
            return False
        
        # Try upload methods in order of preference
        for method in self.upload_methods:
            upload_logger.info(f"Trying upload method: {method}")
            
            success = False
            if method == 'scp':
                success = self.upload_via_scp(source_file)
            elif method == 'rsync':
                success = self.upload_via_rsync(source_file)
            elif method == 'sftp':
                # SFTP implementation could be added here if needed
                upload_logger.info("SFTP method not implemented, skipping...")
                continue
            
            if success:
                # Verify the upload
                if self.verify_upload(source_file):
                    self.last_upload_time = time.time()
                    upload_logger.info(f"✓ Upload completed successfully using {method}")
                    
                    # Log transcript info if available for AI processing integration
                    self._log_transcript_info()
                    return True
                else:
                    upload_logger.warning(f"Upload via {method} completed but verification failed")
            else:
                upload_logger.warning(f"Upload via {method} failed, trying next method...")
        
        upload_logger.error("✗ All upload methods failed")
        return False
    
    def _log_transcript_info(self):
        """Log transcript information for potential AI integration"""
        try:
            if TRANSCRIPT_FILE.exists():
                with open(TRANSCRIPT_FILE, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                
                upload_logger.info("--- Transcript Information (AI Integration Ready) ---")
                upload_logger.info(f"Transcript: {transcript_data.get('transcript', 'N/A')}")
                upload_logger.info(f"Processing method: {transcript_data.get('processing_method', 'unknown')}")
                upload_logger.info(f"Timestamp: {transcript_data.get('iso_timestamp', 'N/A')}")
                upload_logger.info("Note: Transcript data is available for Vertex AI or other AI processing")
                upload_logger.info("--- End Transcript Information ---")
            else:
                upload_logger.info("No transcript file found - transcription may have failed")
                
        except Exception as e:
            upload_logger.warning(f"Could not read transcript information: {e}")

def main():
    """Main entry point for the upload script"""
    upload_logger.info("=== programmSendFile.py - Audio File Upload ===")
    upload_logger.info("Starting server upload process...")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        source_file_path = Path(sys.argv[1])
        upload_logger.info(f"Using source file from command line: {source_file_path}")
    else:
        source_file_path = AUDIO_FILE
        upload_logger.info(f"Using default source file: {source_file_path}")
    
    # Create uploader and perform upload
    uploader = AudioUploader()
    
    try:
        success = uploader.upload_file(source_file_path)
        
        if success:
            upload_logger.info("✓ Audio file upload workflow completed successfully")
            upload_logger.info("Server now has the latest recording available")
            return True
        else:
            upload_logger.error("✗ Audio file upload workflow failed")
            return False
            
    except KeyboardInterrupt:
        upload_logger.warning("Upload interrupted by user")
        return False
    except Exception as e:
        upload_logger.error(f"Unexpected error during upload: {e}")
        import traceback
        upload_logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            upload_logger.info("Upload process completed successfully")
            sys.exit(0)
        else:
            upload_logger.error("Upload process failed")
            sys.exit(1)
    except Exception as e:
        upload_logger.error(f"Fatal error: {e}")
        sys.exit(1)
