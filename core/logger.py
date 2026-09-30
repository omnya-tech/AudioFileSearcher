import os
from datetime import datetime
from core.paths import LOGS_DIR

class Logger:
    def __init__(self):
        self.log_dir = LOGS_DIR
        self.log_file = os.path.join(self.log_dir, "app.log")
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _write(self, level, msg, code=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{level}]" if not code else f"[{level} - {code}]"
        log_entry = f"{timestamp} {prefix}: {msg}\n"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(log_entry.strip())
        except:
            pass

_logger_instance = Logger()

def log_error(msg):
    _logger_instance._write("ERROR", msg)

def log_warning(msg):
    _logger_instance._write("WARNING", msg)

def log_info(msg):
    _logger_instance._write("INFO", msg)

def log_security(code, msg):
    _logger_instance._write("SECURITY", msg, code)