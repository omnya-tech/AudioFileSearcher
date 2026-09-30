import os
from pathlib import Path
from typing import Optional, List

def log_security(code, msg): print(f"[SECURITY - {code}]: {msg}")
def log_warning(msg): print(f"[WARNING]: {msg}")

class FileValidator:
    MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024  
    MAX_AUDIO_FILE_SIZE = 100 * 1024 * 1024 
    MAX_IMAGE_FILE_SIZE = 20 * 1024 * 1024  

    ALLOWED_TEXT_EXTENSIONS = {'.txt', '.md', '.json', '.xml', '.csv', '.log', '.srt'}
    ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.rm'}
    ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico'}
    DANGEROUS_EXTENSIONS = {'.exe', '.dll', '.bat', '.cmd', '.vbs', '.js', '.ps1', '.msi'}

    @staticmethod
    def validate_file_read(file_path: str, expected_extensions: Optional[List[str]] = None, max_size: Optional[int] = None) -> tuple[bool, Optional[str]]:
        try:
            path = Path(file_path)
            if not path.exists(): return False, f"File not found: {file_path}"
            if not path.is_file():
                log_security("INVALID_FILE", f"Path is not a file: {file_path}")
                return False, "Selected path is not a file"

            extension = path.suffix.lower()
            if extension in FileValidator.DANGEROUS_EXTENSIONS:
                log_security("DANGEROUS_FILE", f"Attempted to read dangerous file: {file_path}")
                return False, f"File type not allowed: {extension}"

            if expected_extensions and extension not in expected_extensions:
                return False, "Invalid file extension"

            file_size = path.stat().st_size
            if max_size is None:
                if extension in FileValidator.ALLOWED_AUDIO_EXTENSIONS: max_size = FileValidator.MAX_AUDIO_FILE_SIZE
                elif extension in FileValidator.ALLOWED_IMAGE_EXTENSIONS: max_size = FileValidator.MAX_IMAGE_FILE_SIZE
                else: max_size = FileValidator.MAX_TEXT_FILE_SIZE

            if file_size > max_size:
                return False, "File is too large"

            if not os.access(file_path, os.R_OK):
                return False, "No read permissions for the file"

            return True, None
        except Exception as e:
            return False, f"Validation error: {e}"

    @staticmethod
    def safe_read_text(file_path: str, encoding: str = 'utf-8', max_size: Optional[int] = None) -> Optional[str]:
        is_valid, error = FileValidator.validate_file_read(file_path, expected_extensions=list(FileValidator.ALLOWED_TEXT_EXTENSIONS), max_size=max_size or FileValidator.MAX_TEXT_FILE_SIZE)
        if not is_valid: return None
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception:
            return None