"""
مسارات البرنامج في مكان واحد.
- APP_DIR: مجلد قابل للكتابة بجانب البرنامج (الإعدادات، النماذج، السجلات).
- RESOURCE_DIR: الملفات المضمَّنة مع البرنامج (ملفات اللغة).
عند التشغيل كملف exe (PyInstaller) يختلف الاثنان، وعند التشغيل من الكود هما نفس المجلد.
"""
import os
import sys

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESOURCE_DIR = APP_DIR

LOCALES_DIR = os.path.join(RESOURCE_DIR, "locales")
MODELS_DIR = os.path.join(APP_DIR, "models")
LOGS_DIR = os.path.join(APP_DIR, "logs")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
