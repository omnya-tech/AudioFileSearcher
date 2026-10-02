<div dir="rtl">

# الباحث في الوسائط 🎙️

**تفريغ وبحث في الملفات الصوتية دون اتصال بالإنترنت، بدعم كامل لقارئات الشاشة.**

برنامج مخصص لنظام ويندوز يحوّل التسجيلات الصوتية إلى نصوص مكتوبة بدقة عالية باستخدام نموذج Whisper. يعمل البرنامج محلياً بالكامل على جهازك للحفاظ على خصوصيتك، دون إرسال أي بيانات إلى الإنترنت.

صُمِّم ليكون سهل الوصول، مع دعم كامل للاستخدام عبر لوحة المفاتيح وقارئات الشاشة (مثل NVDA)، ويوفر واجهة استخدام باللغتين العربية والإنجليزية.

[Read in English](#media-searcher-)

---

## ✨ المزايا الأساسية

* **تفريغ دقيق وذكي:** يدعم العربية وعشرات اللغات الأخرى. يتخطى فترات الصمت والموسيقى تلقائياً لمنع النموذج من كتابة نصوص غير دقيقة أو وهمية.
* **أدوات مراجعة مرنة:** يميّز الكلمات التي لم يتأكد النموذج منها لتراجعها بسهولة. يمكنك تشغيل أي جملة لسماع نطقها، مع إمكانية تعديل، تقسيم، أو دمج الجمل بسلاسة.
* **قواميس مخصصة لكل مجال:** سواء كانت محاضرات، اجتماعات، أو تلاوات قرآنية، يوفر البرنامج تصحيحات تلقائية. يمكنك تزويد النموذج بالمصطلحات والأسماء كتلميحات مسبقة لضمان كتابتها بشكل صحيح من المرة الأولى.
* **التعلّم المستمر:** بمجرد تصحيحك لكلمة معينة، يحفظها البرنامج في ذاكرته ويقوم بتصحيحها تلقائياً في أي تفريغ مستقبلي.
* **بحث شامل:** ابحث في جميع ملفات التفريغ الخاصة بك، وقم بتشغيل المقطع الصوتي مباشرة من لحظة ظهور نتيجة البحث.
* **حفظ تلقائي للتقدم:** يُحفظ عملك أولاً بأول؛ لتتمكن من الاستكمال من حيث توقفت في حال انقطاع الكهرباء أو إغلاق البرنامج فجأة.
* **خيارات تصدير متعددة:** احفظ تفريغاتك بصيغ متنوعة تشمل Word، JSON، TXT، VTT، وSRT.
* **دعم إمكانية الوصول:** توافق تام مع قارئات الشاشة، دعم للمظهر الداكن (Dark Mode)، وتوافق مع الشاشات عالية الدقة.

---

## 🚀 التثبيت

1. انتقل إلى صفحة [الإصدارات (Releases)](../../releases) وحمّل ملف التثبيت: `MediaSearcher-Setup-<الإصدار>.exe`.
2. شغّل الملف واختر لغة التثبيت (وهي التي ستصبح لغة واجهة البرنامج لاحقاً).
3. عند التشغيل لأول مرة، سيقترح عليك البرنامج النموذج الأنسب لمواصفات جهازك ويقوم بتحميله مرة واحدة فقط، ليعمل بعدها دون الحاجة للإنترنت نهائياً.

يظهر البرنامج في قائمة ابدأ باسم «Media Searcher».

> **ملاحظة:** عملية التثبيت العادية لا تتطلب صلاحيات المسؤول. إذا أردت تثبيت البرنامج لجميع المستخدمين على الجهاز، استخدم الأمر التالي:
> `MediaSearcher-Setup-<الإصدار>.exe /ALLUSERS`

دليل الاستخدام الشامل متوفر داخل البرنامج (بالضغط على زر `F1`)، أو من خلال مجلد [docs](docs/guide_ar.md).

---

## 💻 للمطورين

### التشغيل من الشفرة المصدرية

يتطلب البرنامج وجود Python 3.11 على نظام ويندوز 10 أو أحدث (بنية 64-بت).

```cmd
pip install -r requirements.txt
python main.py
```

### البناء

يتطلب [PyInstaller](https://pyinstaller.org) و[Inno Setup 7](https://jrsoftware.org/isdl.php):

```cmd
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
```

ينتج عنه البرنامج في `dist\MediaSearcher`، وملف التثبيت `dist\MediaSearcher-Setup-<الإصدار>.exe`.
رقم الإصدار مصدره واحد: المفتاح `app_version` في ملفات اللغة `locales`.

### الاختبارات

```cmd
pip install pytest pywinauto
python -m pytest
```

---

## الترخيص

حقوق النشر © 2026 محمد شعراوي، فريق Omnya للبرمجيات.

البرنامج حر ومفتوح المصدر بموجب [رخصة جنو العمومية العامة، الإصدار الثالث (GPL-3.0)](LICENSE): يمكنك استخدامه ونسخه وتعديله وتوزيعه، بشرط أن تبقى أي نسخة موزَّعة منه مفتوحة المصدر بالرخصة نفسها.

</div>

---

# Media Searcher 🎙️

**Transcribe and search your audio files offline — screen-reader friendly.**

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

1. Download `MediaSearcher-Setup-<version>.exe` from the [Releases](../../releases) page.
2. Run it and choose a language; the language you choose in the installer becomes the program's language.
3. On first run, the program suggests a model suited to your computer and downloads it once; after that it works offline.

The program appears in the Start menu as "Media Searcher".

No administrator rights are needed. To install for all users: `MediaSearcher-Setup-<version>.exe /ALLUSERS`.

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

This produces the program in `dist\MediaSearcher` and the installer `dist\MediaSearcher-Setup-<version>.exe`.
The version number has a single source: the `app_version` key in the `locales` files.

## Tests

```
pip install pytest pywinauto
python -m pytest
```

## License

Copyright © 2026 محمد شعراوي, Omnya Software Team.

This program is free software, licensed under the [GNU General Public License v3.0](LICENSE).
