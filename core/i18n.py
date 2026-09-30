import os
import json

class LocalizationManager:
    def __init__(self, default_lang="ar"):
        self.language = default_lang
        self.translations = {}
        self._observers = []

        # تحديد مسار مجلد locales بدقة بناءً على مكان ملف i18n.py داخل مجلد core
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.locales_dir = os.path.join(self.base_dir, "locales")
        
        self.load_translations()

    def load_translations(self):
        """البحث عن ملفات اللغة (JSON) وتحميلها كقواميس"""
        if not os.path.exists(self.locales_dir):
            print(f"[تحذير] مجلد اللغات غير موجود: {self.locales_dir}")
            return
        
        # تم تصحيح الخطأ هنا (os.listdir بدلاً من os.path.listdir)
        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = filename.replace(".json", "")
                file_path = os.path.join(self.locales_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"[خطأ] تعذر تحميل ملف اللغة {filename}: {e}")

    RTL_LANGUAGES = ("ar",)

    @property
    def is_rtl(self):
        return self.language in self.RTL_LANGUAGES

    def apply_direction(self, window):
        """ضبط اتجاه النافذة حسب اللغة. يُستدعى مباشرة بعد إنشاء النافذة وقبل إضافة عناصرها"""
        import wx
        window.SetLayoutDirection(wx.Layout_RightToLeft if self.is_rtl else wx.Layout_LeftToRight)

    def fix_notebook(self, notebook):
        """
        أسماء التبويبات تظهر بحروف مقلوبة في ويندوز لو التبويبات نفسها من اليمين لليسار،
        فنجعل شريط التبويبات فقط من اليسار لليمين، ويبقى محتوى كل صفحة بالاتجاه الصحيح.
        """
        import wx
        notebook.SetLayoutDirection(wx.Layout_LeftToRight)

    def add_observer(self, callback):
        """تسجيل دالة يتم استدعاؤها عند تغيير لغة الواجهة"""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback):
        if callback in self._observers:
            self._observers.remove(callback)

    def set_language(self, lang_code):
        """تحديث اللغة النشطة في البرنامج وإبلاغ كل النوافذ المسجلة"""
        old_lang = self.language
        if lang_code in self.translations:
            self.language = lang_code
        else:
            self.language = "ar"  # لغة الطوارئ الافتراضية

        if self.language != old_lang:
            for callback in list(self._observers):
                try:
                    callback()
                except Exception as e:
                    print(f"[خطأ] فشل تحديث الواجهة بعد تغيير اللغة: {e}")

    def get(self, key, default=None, **kwargs):
        """
        المحرك الأساسي لجلب النصوص.
        يدعم دمج المتغيرات الديناميكية (Dynamic Formatting) بأمان تام عبر **kwargs
        """
        lang_dict = self.translations.get(self.language, {})
        
        # جلب النص من القاموس، وإن لم يوجد نرجع النص الافتراضي، وإلا نرجع المفتاح نفسه
        text = lang_dict.get(key, default if default is not None else key)
        
        # السحر المعماري: دمج المتغيرات داخل النص إن وجدت (مثل: {percent} أو {app_title})
        if kwargs and isinstance(text, str):
            try:
                return text.format(**kwargs)
            except KeyError:
                # تفادي انهيار البرنامج إذا احتوى ملف JSON على متغير لم نقم بتمريره
                pass
            except Exception:
                # تجاوز أي أخطاء صياغة غير متوقعة لضمان استقرار الواجهة
                pass

        return text