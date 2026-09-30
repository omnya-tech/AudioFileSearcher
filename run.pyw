# تشغيل البرنامج بدون الشباك الأسود (دبل كليك على الملف ده)
import os
import runpy
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
runpy.run_path("main.py", run_name="__main__")
