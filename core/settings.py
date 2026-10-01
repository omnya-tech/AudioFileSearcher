import os
import json

from core.paths import APP_DIR, CONFIG_FILE, ensure_dir

# يكتبه مثبت Inno Setup في مجلد البرنامج (انظر installer/AudioFileSearcher.iss)
INSTALLER_LANGUAGE_FILE = "installer_language"

class SettingsManager:
    def __init__(self, config_file=None):
        # المسار ثابت بجانب البرنامج مهما كان مجلد التشغيل الحالي
        self.config_file = config_file or CONFIG_FILE
        self.settings = self._get_defaults()
        self.load()

    def _get_defaults(self):
        return {
            "user_mode": "beginner",
            "model_size": "deepdml/faster-whisper-large-v3-turbo-ct2",
            "device": "cpu",
            "keep_in_memory": True,
            "use_local_model": False,
            "local_model_path": "",
            "output_directory": "",
            "default_export_format": "srt",
            "auto_save": True,
            "open_folder_after_save": False,
            "export_formats": ["srt", "txt", "vtt", "json", "docx"],
            "enable_correction": True,
            "correction_level": "medium",
            "use_hotwords": True,
            "learn_mode": "ask",
            "custom_dictionary": {},
            "language": "ar",
            "theme": "light",
            "font_size": 10,
            "compute_type": "int8",
            "beam_size": 5,
            "temperature": 0.0,
            "transcription_language": "ar",
            "auto_detect_language": False,
            "vad_filter": True,
            "word_timestamps": True,
            "no_speech_threshold": 0.6,
            "threads": 0,
            "initial_prompt": ""
        }

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8-sig') as f:  # يقبل الملف لو حُفظ بمحرر يضيف BOM
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.settings.update(data)
            except Exception as e:
                print(f"[ERROR]: Settings file is corrupted, using defaults: {e}")

    def save(self):
        # الكتابة في ملف مؤقت ثم استبداله، حتى لا يتلف ملف الإعدادات لو انقطع الحفظ في المنتصف
        tmp_file = self.config_file + ".tmp"
        try:
            ensure_dir(os.path.dirname(self.config_file))
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            os.replace(tmp_file, self.config_file)
        except Exception as e:
            print(f"[ERROR]: Failed to save settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def update(self, values):
        """تعديل عدة إعدادات معاً مع حفظ الملف مرة واحدة فقط"""
        self.settings.update(values)
        self.save()

    def apply_installer_language(self):
        """
        المثبت يكتب اللغة التي اختارها المستخدم في ملف بجانب البرنامج، فيظهر البرنامج بلغة المثبت.
        تُطبَّق مرة واحدة بعد كل تثبيت (بصمة الملف محفوظة)، فلا تُلغي تغيير المستخدم للغة لاحقاً من الإعدادات.
        """
        path = os.path.join(APP_DIR, INSTALLER_LANGUAGE_FILE)
        try:
            with open(path, encoding="utf-8-sig") as f:
                lang = f.read().strip().lower()
            stamp = f"{lang}:{os.path.getmtime(path)}"
        except OSError:
            return
        if lang in ("ar", "en") and self.get("installer_language_stamp") != stamp:
            self.update({"language": lang, "installer_language_stamp": stamp})

    def reset_to_defaults(self):
        self.settings = self._get_defaults()
        self.save()