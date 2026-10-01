<div dir="rtl">

# الباحث الصوتي في الملفات

برنامج لويندوز يحوّل التسجيلات الصوتية إلى نص مكتوب باستخدام نموذج Whisper، ويعمل على جهازك بالكامل دون إرسال أي تسجيل إلى الإنترنت.
صُمِّم ليُستخدم بالكامل من لوحة المفاتيح ومع قارئات الشاشة مثل NVDA، وواجهته بالعربية والإنجليزية.

[English](#audio-file-searcher)

## المزايا

- **تفريغ دقيق** للعربية وعشرات اللغات الأخرى، مع تخطي فترات الصمت والموسيقى حتى لا يكتب النموذج كلاماً وهمياً.
- **مراجعة سهلة**: تمييز الكلمات التي لم يتأكد منها النموذج، وتشغيل كل جملة بصوتها، وتعديل الجمل وتقسيمها ودمجها.
- **قواميس لكل مجال** (محاضرات، اجتماعات، قرآن...): تصحيحات تلقائية، ومصطلحات وأسماء تُقدَّم للنموذج تلميحاً فيكتبها صحيحة من البداية.
- **التعلّم من تصحيحاتك**: عندما تصحّح كلمة، يتذكرها البرنامج ويصحّحها في كل تفريغ قادم.
- **البحث الشامل** في كل ملفات التفريغ، وتشغيل الصوت من لحظة النتيجة مباشرة.
- **الاستكمال بعد الانقطاع**: يُحفظ التقدم أولاً بأول، فإذا انقطعت الكهرباء أكملت من حيث توقفت.
- **التصدير** بصيغ SRT وVTT وTXT وJSON وWord.
- دعم كامل لقارئات الشاشة، والمظهر الداكن، والشاشات عالية الدقة.

## التثبيت

1. حمّل ملف التثبيت `AudioFileSearcher-Setup-<الإصدار>.exe` من صفحة [الإصدارات (Releases)](../../releases).
2. شغّله واختر اللغة؛ فاللغة التي تختارها في المثبت تصبح لغة البرنامج.
3. عند أول تشغيل، يقترح البرنامج نموذجاً مناسباً لجهازك ويحمّله مرة واحدة، ثم يعمل دون إنترنت.

لا يحتاج التثبيت إلى صلاحيات المسؤول. وللتثبيت لجميع المستخدمين: `AudioFileSearcher-Setup-<الإصدار>.exe /ALLUSERS`.

دليل الاستخدام الكامل داخل البرنامج (زر F1)، وفي مجلد [docs](docs/guide_ar.md).

## التشغيل من الشفرة المصدرية

يتطلب Python 3.11 على ويندوز 10 أو أحدث (64 بت).

```
pip install -r requirements.txt
python main.py
```

## البناء

يتطلب [PyInstaller](https://pyinstaller.org) و[Inno Setup 7](https://jrsoftware.org/isdl.php):

```
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
```

ينتج عنه البرنامج في `dist\AudioFileSearcher`، وملف التثبيت `dist\AudioFileSearcher-Setup-<الإصدار>.exe`.
رقم الإصدار مصدره واحد: المفتاح `app_version` في ملفات اللغة `locales`.

## الاختبارات

```
pip install pytest pywinauto
python -m pytest
```

## الترخيص

حقوق النشر © 2026 محمد شعراوي، فريق Omnya للبرمجيات.

البرنامج حر ومفتوح المصدر بموجب [رخصة جنو العمومية العامة، الإصدار الثالث (GPL-3.0)](LICENSE): يمكنك استخدامه ونسخه وتعديله وتوزيعه، بشرط أن تبقى أي نسخة موزَّعة منه مفتوحة المصدر بالرخصة نفسها.

</div>

---

# Audio File Searcher

A Windows program that turns audio recordings into written text with Whisper. It runs entirely on your computer and never sends recordings to the internet.
It is designed to be fully usable from the keyboard and with screen readers such as NVDA, with an Arabic and English interface.

## Features

- **Accurate transcription** of Arabic and dozens of other languages, skipping silence and music so the model does not write made-up text.
- **Easy review**: words the model was unsure of are highlighted; play any sentence, edit, split and merge sentences.
- **Per-field dictionaries** (lectures, meetings, Quran...): automatic corrections, plus terms and names given to the model as hints so it writes them correctly from the start.
- **Learns from your corrections**: when you correct a word, the program remembers it for future transcriptions.
- **Global search** across all transcriptions, playing the audio from the matching moment.
- **Resume after interruption**: progress is saved continuously, so a power cut does not lose your work.
- **Export** to SRT, VTT, TXT, JSON and Word.
- Full screen reader support, dark mode, and high-DPI displays.

## Installation

1. Download `AudioFileSearcher-Setup-<version>.exe` from the [Releases](../../releases) page.
2. Run it and choose a language; the language you choose in the installer becomes the program's language.
3. On first run, the program suggests a model suited to your computer and downloads it once; after that it works offline.

No administrator rights are needed. To install for all users: `AudioFileSearcher-Setup-<version>.exe /ALLUSERS`.

The full user guide is inside the program (F1) and in the [docs](docs/guide_en.md) folder.

## Running from source

Requires Python 3.11 on Windows 10 or later (64-bit).

```
pip install -r requirements.txt
python main.py
```

## Building

Requires [PyInstaller](https://pyinstaller.org) and [Inno Setup 7](https://jrsoftware.org/isdl.php):

```
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
```

This produces the program in `dist\AudioFileSearcher` and the installer `dist\AudioFileSearcher-Setup-<version>.exe`.
The version number has a single source: the `app_version` key in the `locales` files.

## Tests

```
pip install pytest pywinauto
python -m pytest
```

## License

Copyright © 2026 محمد شعراوي, Omnya Software Team.

This program is free software, licensed under the [GNU General Public License v3.0](LICENSE).
