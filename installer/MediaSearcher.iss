; مثبت «الباحث في الوسائط» (Inno Setup 7)
; يُبنى تلقائياً من build.ps1 بعد بناء نسخة exe، أو يدوياً:
;   ISCC.exe /DAppVersion=1.0.0 installer\MediaSearcher.iss
; يحتاج: dist\MediaSearcher (من PyInstaller)، وملفي الرخصة build\license_ar.txt و build\license_en.txt (من build.ps1)

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppExe "MediaSearcher.exe"
; الأسماء التقنية السابقة: يُحذف ما بقي منها عند التحديث
#define LegacyName "AudioTranscriber"
#define LegacyName2 "AudioFileSearcher"
; اسم البرنامج في ويندوز (قائمة ابدأ، وسطح المكتب، والتطبيقات المثبتة، و«فتح باستخدام») ثابت بالإنجليزية
; مهما كانت لغة المثبت: لغة الواجهة تتغير من الإعدادات، والاسم الذي يكتبه المثبت لا يتغير معها
#define AppName "Media Searcher"
#define AppPublisher "Omnya Software"
; معرّف البرنامج بلا أقواس: يُستخدم في AppId وفي البحث عن التثبيتات السابقة في الريجستري
#define AppGuid "9D0DC9B3-FF25-4F8C-903D-774923EB1FE2"
#define ProgId "MediaSearcher.AudioFile"

[Setup]
; معرّف ثابت: لا تغيّره أبداً، وإلا يُعامَل كل إصدار جديد كبرنامج مختلف.
; (بقي كما هو بعد تغيير الاسم التقني من AudioTranscriber ثم AudioFileSearcher؛ والتثبيت القديم للمستخدم وحده يُزال قبل التثبيت
; في Program Files، وينقل البرنامج بياناته ونماذجه إلى %APPDATA% عند أول تشغيل: انظر RemovePerUserInstall وcore/paths.py)
AppId={{{#AppGuid}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright © 2026 محمد شعراوي, Omnya Software Team
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup
VersionInfoCompany={#AppPublisher}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}

; البرنامج في Program Files (يحتاج موافقة المسؤول)، وبيانات كل مستخدم في مجلده %APPDATA%\MediaSearcher
; (الإعدادات والقواميس والنماذج والسجلات): انظر core/paths.py
PrivilegesRequired=admin
DefaultDirName={autopf}\MediaSearcher
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; البرنامج المفتوح يُغلق تلقائياً دون سؤال عند التحديث والإزالة (انظر CloseRunningProgram).
; لا نستخدم AppMutex لأنه يسأل المستخدم أن يغلقه بنفسه. وCloseApplications=force احتياط أخير
; لو بقي ملف مستخدماً: يغلق البرنامج الذي يستخدمه دون سؤال
CloseApplications=force
RestartApplications=no
ChangesAssociations=yes

ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
WizardStyle=modern
SetupIconFile=..\assets\app.ico
OutputDir=..\dist
OutputBaseFilename=MediaSearcher-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
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
Type: files; Name: "{autoprograms}\{#AppName}.lnk"
Type: files; Name: "{autodesktop}\{#AppName}.lnk"
; البرنامج بالأسماء التقنية القديمة (يُحدَّث التثبيت القديم في مكانه)
Type: files; Name: "{app}\{#LegacyName}.exe"
Type: files; Name: "{app}\{#LegacyName2}.exe"

[Files]
Source: "..\dist\MediaSearcher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; \
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
Root: HKA; Subkey: "Software\Classes\{#LegacyName2}.AudioFile"; ValueType: none; Flags: deletekey dontcreatekey
Root: HKA; Subkey: "Software\Classes\Applications\{#LegacyName2}.exe"; ValueType: none; Flags: deletekey dontcreatekey
#define AddAudioType(Ext) \
  "Root: HKA; Subkey: ""Software\Classes\" + Ext + "\OpenWithProgids""; ValueType: string; ValueName: """ + ProgId + """; ValueData: """"; Flags: uninsdeletevalue; Tasks: openwith" + NewLine + \
  "Root: HKA; Subkey: ""Software\Classes\Applications\" + AppExe + "\SupportedTypes""; ValueType: string; ValueName: """ + Ext + """; ValueData: """"; Tasks: openwith" + NewLine + \
  "Root: HKA; Subkey: ""Software\Classes\" + Ext + "\OpenWithProgids""; ValueType: none; ValueName: """ + LegacyName + ".AudioFile""; Flags: deletevalue dontcreatekey" + NewLine + \
  "Root: HKA; Subkey: ""Software\Classes\" + Ext + "\OpenWithProgids""; ValueType: none; ValueName: """ + LegacyName2 + ".AudioFile""; Flags: deletevalue dontcreatekey" + NewLine
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

{ الإصدارات السابقة كانت تُثبَّت للمستخدم الحالي فقط (%LOCALAPPDATA%\Programs، وسجلها في HKCU).
  نزيلها بصمت قبل التثبيت حتى لا يظهر البرنامج مرتين. برنامج الإزالة القديم في الوضع الصامت لا يحذف بيانات المستخدم
  (سؤال الحذف إجابته الافتراضية «لا»)، والبرنامج الجديد ينقل تلك البيانات إلى %APPDATA%\MediaSearcher عند أول تشغيل }
{ إغلاق البرنامج المفتوح (بالاسم الحالي والأسماء السابقة): طلب إغلاق عادي أولاً، ثم إجباري لو لم يُغلق.
  التفريغ الجاري يُستكمل بعد التحديث (يحفظ البرنامج التقدم كل بضع ثوانٍ) }
procedure CloseRunningProgram();
var
  ResultCode: Integer;
  Images: String;
begin
  Images := '/IM {#AppExe} /IM {#LegacyName}.exe /IM {#LegacyName2}.exe';
  Exec(ExpandConstant('{sys}	askkill.exe'), Images, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(2000);
  Exec(ExpandConstant('{sys}	askkill.exe'), '/F /T ' + Images, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
end;

{ قبل فحص الملفات المستخدمة وقبل التثبيت (بعد ضغط «تثبيت»، فإلغاء المثبت قبله لا يغلق البرنامج) }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  CloseRunningProgram();
  Result := '';
end;

procedure RemovePerUserInstall();
var
  Uninstaller: String;
  ResultCode: Integer;
begin
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#AppGuid}}_is1',
                         'UninstallString', Uninstaller) then
  begin
    Uninstaller := RemoveQuotes(Uninstaller);
    if FileExists(Uninstaller) then
      Exec(Uninstaller, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

{ ربط المثبت بالبرنامج: اللغة المختارة في المثبت تصبح لغة البرنامج (يقرؤها SettingsManager.apply_installer_language) }
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    RemovePerUserInstall();
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

{ البيانات في %APPDATA%\MediaSearcher (والإصدارات القديمة كانت تحفظها بجانب البرنامج أو في %APPDATA% بأسمائها القديمة).
  تُحذف عناصرها المعروفة فقط، لا المجلد كله، حتى لا يُحذف شيء آخر لو ثُبّت البرنامج في مجلد مشترك }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    { بعد تأكيد الإزالة، لا عند فتح برنامج الإزالة: لو تراجع المستخدم لا يُغلق البرنامج }
    CloseRunningProgram();
    DeleteUserData := SuppressibleMsgBox(CustomMessage('DeleteUserData'),
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES;
  end;

  if (CurUninstallStep = usPostUninstall) and DeleteUserData then
  begin
    DeleteDataIn(ExpandConstant('{app}'));
    RemoveDir(ExpandConstant('{app}'));
    DeleteDataIn(ExpandConstant('{userappdata}\MediaSearcher'));
    RemoveDir(ExpandConstant('{userappdata}\MediaSearcher'));
    DeleteDataIn(ExpandConstant('{userappdata}\{#LegacyName2}'));
    RemoveDir(ExpandConstant('{userappdata}\{#LegacyName2}'));
    DeleteDataIn(ExpandConstant('{userappdata}\{#LegacyName}'));
    RemoveDir(ExpandConstant('{userappdata}\{#LegacyName}'));
  end;
end;
