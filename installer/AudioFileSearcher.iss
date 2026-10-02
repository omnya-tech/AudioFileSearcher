; مثبت «الباحث الصوتي في الملفات» (Inno Setup 7)
; يُبنى تلقائياً من build.ps1 بعد بناء نسخة exe، أو يدوياً:
;   ISCC.exe /DAppVersion=1.0.0 installer\AudioFileSearcher.iss
; يحتاج: dist\AudioFileSearcher (من PyInstaller)، وملفي الرخصة build\license_ar.txt و build\license_en.txt (من build.ps1)

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppExe "AudioFileSearcher.exe"
; الاسم التقني قبل الإصدار الذي غيّره: يُحذف ما بقي منه عند التحديث
#define LegacyName "AudioTranscriber"
; اسم البرنامج في ويندوز (قائمة ابدأ، وسطح المكتب، والتطبيقات المثبتة، و«فتح باستخدام») ثابت بالإنجليزية
; مهما كانت لغة المثبت: لغة الواجهة تتغير من الإعدادات، والاسم الذي يكتبه المثبت لا يتغير معها
#define AppName "Audio File Searcher"
#define AppPublisher "Omnya Software"
#define ProgId "AudioFileSearcher.AudioFile"

[Setup]
; معرّف ثابت: لا تغيّره أبداً، وإلا يُعامَل كل إصدار جديد كبرنامج مختلف.
; (بقي كما هو بعد تغيير الاسم التقني من AudioTranscriber، فيُحدَّث التثبيت القديم في مكانه ببياناته ونماذجه)
AppId={{9D0DC9B3-FF25-4F8C-903D-774923EB1FE2}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright © 2026 محمد شعراوي, Omnya Software Team
VersionInfoVersion={#AppVersion}
VersionInfoProductName=Audio File Searcher
VersionInfoDescription=Audio File Searcher Setup
VersionInfoCompany={#AppPublisher}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}

; التثبيت للمستخدم الحالي دون صلاحيات المسؤول (%LOCALAPPDATA%\Programs).
; التثبيت لكل المستخدمين في Program Files من سطر الأوامر:  AudioFileSearcher-Setup.exe /ALLUSERS
; (لا تُعرض نافذة الاختيار لأنها تظهر قبل اختيار اللغة، فلا تعرف اسم البرنامج المترجم)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
DefaultDirName={autopf}\AudioFileSearcher
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; البرنامج مفتوح: يطلب المثبت وبرنامج الإزالة إغلاقه أولاً (الاسم نفسه في main.py)
; والاسمان القديمان: الإصدار السابق المفتوح يُطلب إغلاقه أيضاً
AppMutex=AudioFileSearcher.Running,Global\AudioFileSearcher.Running,{#LegacyName}.Running,Global\{#LegacyName}.Running
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
WizardStyle=modern
SetupIconFile=..\assets\app.ico
OutputDir=..\dist
OutputBaseFilename=AudioFileSearcher-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
SetupLogging=yes

[Languages]
Name: "ar"; MessagesFile: "Arabic.isl"; LicenseFile: "..\build\license_ar.txt"
Name: "en"; MessagesFile: "compiler:Default.isl"; LicenseFile: "..\build\license_en.txt"

[Messages]
en.SelectLanguageLabel=Select the language to use during the installation. The program will use the same language.

[CustomMessages]
ar.TaskIntegration=التكامل مع ويندوز:
en.TaskIntegration=Windows integration:
ar.TaskOpenWith=إضافة البرنامج إلى قائمة «فتح باستخدام» للملفات الصوتية
en.TaskOpenWith=Add the program to the "Open with" menu for audio files
ar.AudioFileType=ملف صوتي
en.AudioFileType=Audio file
ar.DeleteUserData=هل تريد حذف بياناتك أيضاً؟%n%nتشمل: الإعدادات، والقواميس، وما تعلّمه البرنامج من تصحيحاتك، ونماذج الذكاء الاصطناعي المحمّلة (قد يبلغ حجمها عدة جيجابايتات).%n%nاختر «لا» للاحتفاظ بها إذا كنت ستعيد تثبيت البرنامج.
en.DeleteUserData=Do you also want to delete your data?%n%nThis includes your settings, dictionaries, what the program learned from your corrections, and the downloaded AI models (which can take several gigabytes).%n%nChoose No to keep them if you plan to reinstall the program.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "openwith"; Description: "{cm:TaskOpenWith}"; GroupDescription: "{cm:TaskIntegration}"

[InstallDelete]
; عند التحديث: حذف ملفات الإصدار السابق فقط حتى لا تختلط بالجديدة. بيانات المستخدم خارج هذا المجلد فتبقى كما هي
Type: filesandordirs; Name: "{app}\_internal"
; اختصارات الإصدارات السابقة: كان اسمها يتبع لغة المثبت، والآن بالإنجليزية دائماً
Type: files; Name: "{autoprograms}\الباحث الصوتي في الملفات.lnk"
Type: files; Name: "{autoprograms}\Audio File Searcher.lnk"
Type: files; Name: "{autodesktop}\الباحث الصوتي في الملفات.lnk"
Type: files; Name: "{autodesktop}\Audio File Searcher.lnk"
; البرنامج بالاسم التقني القديم (يُحدَّث التثبيت القديم في مكانه)
Type: files; Name: "{app}\{#LegacyName}.exe"

[Files]
Source: "..\dist\AudioFileSearcher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "config.json,config.json.tmp,learning.json,\models,\logs,\recovery,\inbox,installer_language"
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "{#AppName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "{#AppName}"; Tasks: desktopicon

[Registry]
; «فتح باستخدام»: نوع ملف خاص بالبرنامج يُضاف إلى قائمة البرامج المقترحة لكل صيغة، دون تغيير البرنامج الافتراضي للمستخدم
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueData: "{cm:AudioFileType}"; Flags: uninsdeletekey; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExe},0"; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: openwith
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: openwith
; «فتح باستخدام» بالاسم القديم: يُحذف عند التحديث حتى لا يظهر البرنامج مرتين في القائمة
Root: HKA; Subkey: "Software\Classes\{#LegacyName}.AudioFile"; ValueType: none; Flags: deletekey dontcreatekey
Root: HKA; Subkey: "Software\Classes\Applications\{#LegacyName}.exe"; ValueType: none; Flags: deletekey dontcreatekey
#define AddAudioType(Ext) \
  "Root: HKA; Subkey: ""Software\Classes\" + Ext + "\OpenWithProgids""; ValueType: string; ValueName: """ + ProgId + """; ValueData: """"; Flags: uninsdeletevalue; Tasks: openwith" + NewLine + \
  "Root: HKA; Subkey: ""Software\Classes\Applications\" + AppExe + "\SupportedTypes""; ValueType: string; ValueName: """ + Ext + """; ValueData: """"; Tasks: openwith" + NewLine + \
  "Root: HKA; Subkey: ""Software\Classes\" + Ext + "\OpenWithProgids""; ValueType: none; ValueName: """ + LegacyName + ".AudioFile""; Flags: deletevalue dontcreatekey" + NewLine
#emit AddAudioType(".mp3")
#emit AddAudioType(".wav")
#emit AddAudioType(".m4a")
#emit AddAudioType(".flac")
#emit AddAudioType(".ogg")
#emit AddAudioType(".aac")
#emit AddAudioType(".wma")
#emit AddAudioType(".opus")

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\installer_language"

[Code]
var
  DeleteUserData: Boolean;

{ ربط المثبت بالبرنامج: اللغة المختارة في المثبت تصبح لغة البرنامج (يقرؤها SettingsManager.apply_installer_language) }
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SaveStringToFile(ExpandConstant('{app}\installer_language'), ActiveLanguage, False);
end;

procedure DeleteDataIn(Dir: String);
begin
  DelTree(Dir + '\models', True, True, True);
  DelTree(Dir + '\logs', True, True, True);
  DelTree(Dir + '\recovery', True, True, True);
  DelTree(Dir + '\inbox', True, True, True);
  DeleteFile(Dir + '\config.json');
  DeleteFile(Dir + '\config.json.tmp');
  DeleteFile(Dir + '\learning.json');
end;

{ البيانات تكون بجانب البرنامج (تثبيت للمستخدم الحالي)، أو في %APPDATA% (تثبيت لكل المستخدمين).
  تُحذف عناصرها المعروفة فقط، لا المجلد كله، حتى لا يُحذف شيء آخر لو ثُبّت البرنامج في مجلد مشترك }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    DeleteUserData := SuppressibleMsgBox(CustomMessage('DeleteUserData'),
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES;

  if (CurUninstallStep = usPostUninstall) and DeleteUserData then
  begin
    DeleteDataIn(ExpandConstant('{app}'));
    RemoveDir(ExpandConstant('{app}'));
    DeleteDataIn(ExpandConstant('{userappdata}\AudioFileSearcher'));
    RemoveDir(ExpandConstant('{userappdata}\AudioFileSearcher'));
    DeleteDataIn(ExpandConstant('{userappdata}\{#LegacyName}'));
    RemoveDir(ExpandConstant('{userappdata}\{#LegacyName}'));
  end;
end;
