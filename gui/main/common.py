"""ثوابت ودوال مشتركة بين أجزاء النافذة الرئيسية"""
import wx
import os
from core.cross_file_search import AUDIO_EXTENSIONS
from core import exporters


# مقدار التقديم والترجيع بـ Alt+الأسهم


SEEK_SECONDS = 5

# كل كم ثانية يُحفظ التقدم على القرص أثناء التفريغ
RECOVERY_SAVE_INTERVAL = 5

EXPORT_FORMATS = exporters.FORMATS
# اسم كل صيغة يُترجم حسب لغة الواجهة (المفتاح في ملفات اللغة: wc_<الصيغة>)
EXPORT_FORMAT_KEYS = {"srt": "wc_srt", "txt": "wc_txt", "vtt": "wc_vtt", "json": "wc_json", "docx": "wc_docx"}


def list_audio_files(folder):
    return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                  if is_audio_file(f) and os.path.isfile(os.path.join(folder, f)))


def is_audio_file(path):
    return path.lower().endswith(AUDIO_EXTENSIONS)


class AudioDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        wx.CallAfter(self.window.on_files_dropped, filenames)
        return True
