; نسخة مراجَعة لغوياً من ترجمة Inno Setup العربية. أنشأها tools/make_arabic_isl.py، فلا تعدّلها يدوياً

; *** Inno Setup version 6.5.0+ arabic messages ***
; Arabic translation  Translated by nacer baaziz (nacerstile@gmail.com)
;
; To download user-contributed translations of this file, go to:
;   https://jrsoftware.org/files/istrans/
;
; Note: When translating this text, do not add periods (.) to the end of
; messages that didn't have them already, because on those messages Inno
; Setup adds the periods automatically (appending a period would result in
; two periods being displayed).

[LangOptions]
; The following three entries are very important. Be sure to read and 
; understand the '[LangOptions] section' topic in the help file.
LanguageName=العربية
LanguageID=$0401
LanguageCodePage=1256
RightToLeft=yes
; If the language you are translating to requires special font faces or
; sizes, uncomment any of the following entries and change them accordingly.
;DialogFontName=
;DialogFontSize=9
;DialogFontBaseScaleWidth=7
;DialogFontBaseScaleHeight=15
;WelcomeFontName=Segoe UI
;WelcomeFontSize=14

[Messages]

; *** Application titles
SetupAppTitle=تثبيت
SetupWindowTitle=تثبيت - %1
UninstallAppTitle=إزالة التثبيت
UninstallAppFullTitle=إزالة تثبيت %1

; *** Misc. common
InformationTitle=معلومات
ConfirmTitle=تأكيد
ErrorTitle=خطأ

; *** SetupLdr messages
SetupLdrStartupMessage=سيثبّت هذا المعالج %1. هل تريد المتابعة؟
LdrCannotCreateTemp=تعذّر إنشاء ملف مؤقت. أُلغي التثبيت
LdrCannotExecTemp=تعذّر تشغيل ملف من المجلد المؤقت. أُلغي التثبيت
HelpTextNote=

; *** Startup error messages
LastErrorMessage=%1.%n%nخطأ %2: %3
SetupFileMissing=الملف %1 مفقود من مجلد التثبيت. يُرجى إصلاح المشكلة أو الحصول على نسخة جديدة من البرنامج.
SetupFileCorrupt=ملفات التثبيت تالفة. يُرجى الحصول على نسخة جديدة من البرنامج.
SetupFileCorruptOrWrongVer=ملفات التثبيت تالفة، أو غير متوافقة مع هذا الإصدار من معالج التثبيت. يُرجى إصلاح المشكلة أو الحصول على نسخة جديدة من البرنامج.
InvalidParameter=مُرِّر معامل غير صالح في سطر الأوامر:%n%n%1
SetupAlreadyRunning=معالج التثبيت قيد التشغيل بالفعل.
WindowsVersionNotSupported=لا يدعم هذا البرنامج إصدار ويندوز المثبت على جهازك.
WindowsServicePackRequired=يتطلب هذا البرنامج %1 حزمة الخدمة %2 أو أحدث.
NotOnThisPlatform=لا يعمل هذا البرنامج على %1.
OnlyOnThisPlatform=يجب تشغيل هذا البرنامج على %1.
OnlyOnTheseArchitectures=لا يمكن تثبيت هذا البرنامج إلا على إصدارات ويندوز المصممة لمعماريات المعالجات التالية:%n%n%1
WinVersionTooLowError=يتطلب هذا البرنامج %1 الإصدار %2 أو أحدث.
WinVersionTooHighError=لا يمكن تثبيت هذا البرنامج على %1 الإصدار %2 أو أحدث.
AdminPrivilegesRequired=يجب تسجيل الدخول بحساب مسؤول لتثبيت هذا البرنامج.
PowerUserPrivilegesRequired=يجب تسجيل الدخول بحساب مسؤول أو بحساب عضو في مجموعة المستخدمين المتميزين لتثبيت هذا البرنامج.
SetupAppRunningError=اكتشف معالج التثبيت أن %1 قيد التشغيل حالياً.%n%nيُرجى إغلاقه الآن، ثم الضغط على «موافق» للمتابعة، أو «إلغاء الأمر» للخروج.
UninstallAppRunningError=اكتشف معالج الإزالة أن %1 قيد التشغيل حالياً.%n%nيُرجى إغلاقه الآن، ثم الضغط على «موافق» للمتابعة، أو «إلغاء الأمر» للخروج.

; *** Startup questions
PrivilegesRequiredOverrideTitle=تحديد وضع التثبيت
PrivilegesRequiredOverrideInstruction=تحديد وضع التثبيت
PrivilegesRequiredOverrideText1=يمكن تثبيت %1 لجميع المستخدمين (يتطلب صلاحيات المسؤول)، أو في حسابك فقط.
PrivilegesRequiredOverrideText2=يمكن تثبيت %1 في حسابك فقط، أو لجميع المستخدمين (يتطلب صلاحيات المسؤول).
PrivilegesRequiredOverrideAllUsers=التثبيت لـ&جميع المستخدمين
PrivilegesRequiredOverrideAllUsersRecommended=التثبيت لـ&جميع المستخدمين (مستحسن)
PrivilegesRequiredOverrideCurrentUser=التثبيت في حسابي &فقط
PrivilegesRequiredOverrideCurrentUserRecommended=التثبيت في حسابي &فقط (مستحسن)

; *** Misc. errors
ErrorCreatingDir=تعذّر على معالج التثبيت إنشاء المجلد «%1»
ErrorTooManyFilesInDir=تعذّر إنشاء ملف في المجلد «%1» لأنه يحتوي على عدد كبير جداً من الملفات

; *** Setup common messages
ExitSetupTitle=الخروج من معالج التثبيت
ExitSetupMessage=لم يكتمل التثبيت. إذا خرجت الآن فلن يُثبَّت البرنامج.%n%nيمكنك تشغيل معالج التثبيت مرة أخرى لاحقاً لإكمال التثبيت.%n%nهل تريد الخروج من معالج التثبيت؟
AboutSetupMenuItem=&حول معالج التثبيت...
AboutSetupTitle=حول معالج التثبيت
AboutSetupMessage=%1 الإصدار %2%n%3%n%nموقع %1 على الإنترنت:%n%4
AboutSetupNote=
TranslatorNote=الترجمة العربية: ناصر بعزيز، مع مراجعة لغوية من فريق Omnya للبرمجيات

; *** Buttons
ButtonBack=< ال&سابق
ButtonNext=ال&تالي >
ButtonInstall=&تثبيت
ButtonOK=موافق
ButtonCancel=إلغاء الأمر
ButtonYes=&نعم
ButtonYesToAll=نعم لل&كل
ButtonNo=&لا
ButtonNoToAll=لا &للكل
ButtonFinish=إ&نهاء
ButtonBrowse=اس&تعراض...
ButtonWizardBrowse=اس&تعراض...
ButtonNewFolder=إنشاء مجلد &جديد

; *** "Select Language" dialog messages
SelectLanguageTitle=اختيار لغة التثبيت
SelectLanguageLabel=اختر اللغة التي تريد استخدامها أثناء التثبيت. وسيعمل البرنامج باللغة نفسها.

; *** Common wizard text
ClickNext=اضغط «التالي» للمتابعة، أو «إلغاء الأمر» للخروج من معالج التثبيت.
BeveledLabel=
BrowseDialogTitle=استعراض المجلدات
BrowseDialogLabel=اختر مجلداً من القائمة التالية، ثم اضغط «موافق».
NewFolderName=مجلد جديد

; *** "Welcome" wizard page
WelcomeLabel1=مرحباً بك في معالج تثبيت [name]
WelcomeLabel2=سيثبّت هذا المعالج [name/ver] على جهازك.%n%nيُستحسن إغلاق جميع التطبيقات الأخرى قبل المتابعة.

; *** "Password" wizard page
WizardPassword=كلمة المرور
PasswordLabel1=هذا التثبيت محمي بكلمة مرور.
PasswordLabel3=يُرجى إدخال كلمة المرور، ثم الضغط على «التالي» للمتابعة. كلمات المرور تميّز بين الأحرف الكبيرة والصغيرة.
PasswordEditLabel=&كلمة المرور:
IncorrectPassword=كلمة المرور التي أدخلتها غير صحيحة. يرجى إعادة المحاولة.

; *** "License Agreement" wizard page
WizardLicense=اتفاقية الترخيص
LicenseLabel=يُرجى قراءة المعلومات المهمة التالية قبل المتابعة.
LicenseLabel3=يُرجى قراءة اتفاقية الترخيص التالية. يجب الموافقة على شروطها قبل متابعة التثبيت.
LicenseAccepted=قرأت الاتفاقية، و&أوافق على شروطها
LicenseNotAccepted=&لا أوافق على الاتفاقية

; *** "Information" wizard pages
WizardInfoBefore=معلومات
InfoBeforeLabel=يُرجى قراءة المعلومات المهمة التالية قبل المتابعة.
InfoBeforeClickLabel=عندما تكون مستعداً لمتابعة التثبيت، اضغط «التالي».
WizardInfoAfter=معلومات
InfoAfterLabel=يُرجى قراءة المعلومات المهمة التالية قبل المتابعة.
InfoAfterClickLabel=عندما تكون مستعداً للمتابعة، اضغط «التالي».

; *** "User Information" wizard page
WizardUserInfo=معلومات المستخدم
UserInfoDesc=يُرجى إدخال بياناتك.
UserInfoName=اسم ال&مستخدم:
UserInfoOrg=المن&ظمة:
UserInfoSerial=&الرقم التسلسلي:
UserInfoNameRequired=يجب إدخال اسم.

; *** "Select Destination Location" wizard page
WizardSelectDir=اختيار مجلد التثبيت
SelectDirDesc=أين تريد تثبيت [name]؟
SelectDirLabel3=سيثبّت المعالج [name] في المجلد التالي.
SelectDirBrowseLabel=للمتابعة اضغط «التالي». وإذا أردت اختيار مجلد آخر، فاضغط «استعراض».
DiskSpaceGBLabel=يلزم [gb] جيجابايت على الأقل من المساحة الفارغة.
DiskSpaceMBLabel=يلزم [mb] ميجابايت على الأقل من المساحة الفارغة.
CannotInstallToNetworkDrive=لا يمكن التثبيت على محرك أقراص شبكي.
CannotInstallToUNCPath=لا يمكن التثبيت على مسار شبكي (UNC).
InvalidPath=يجب إدخال مسار كامل يبدأ بحرف محرك الأقراص، مثل:%n%nC:\APP%n%nأو مسار شبكي بالصيغة:%n%n\\server\share
InvalidDrive=محرك الأقراص أو المسار الشبكي الذي اخترته غير موجود أو يتعذّر الوصول إليه. يُرجى اختيار غيره.
DiskSpaceWarningTitle=مساحة القرص غير كافية
DiskSpaceWarning=يحتاج التثبيت إلى %1 كيلوبايت على الأقل من المساحة الفارغة، والمتاح على محرك الأقراص المحدد %2 كيلوبايت فقط.%n%nهل تريد المتابعة على أي حال؟
DirNameTooLong=اسم المجلد أو المسار طويل جداً.
InvalidDirName=اسم المجلد غير صالح.
BadDirName32=لا يمكن أن يحتوي اسم المجلد على أي من الأحرف التالية:%n%n%1
DirExistsTitle=المجلد موجود بالفعل
DirExists=المجلد:%n%n%1%n%nموجود بالفعل. هل تريد التثبيت فيه على أي حال؟
DirDoesntExistTitle=المجلد غير موجود
DirDoesntExist=المجلد:%n%n%1%n%nغير موجود. هل تريد إنشاءه؟

; *** "Select Components" wizard page
WizardSelectComponents=اختيار المكونات
SelectComponentsDesc=ما المكونات التي تريد تثبيتها؟
SelectComponentsLabel2=اختر المكونات التي تريد تثبيتها، وألغِ اختيار المكونات التي لا تريدها. ثم اضغط «التالي» للمتابعة.
FullInstallation=تثبيت كامل
; if possible don't translate 'Compact' as 'Minimal' (I mean 'Minimal' in your language)
CompactInstallation=تثبيت محدود
CustomInstallation=تثبيت مخصص
NoUninstallWarningTitle=مكونات موجودة
NoUninstallWarning=اكتشف معالج التثبيت أن المكونات التالية مثبتة على جهازك بالفعل:%n%n%1%n%nإلغاء اختيارها لن يزيلها.%n%nهل تريد المتابعة على أي حال؟
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceGBLabel=يتطلب الاختيار الحالي [gb] جيجابايت على الأقل من المساحة الفارغة.
ComponentsDiskSpaceMBLabel=يتطلب الاختيار الحالي [mb] ميجابايت على الأقل من المساحة الفارغة.

; *** "Select Additional Tasks" wizard page
WizardSelectTasks=اختيار المهام الإضافية
SelectTasksDesc=ما المهام الإضافية التي تريد تنفيذها؟
SelectTasksLabel2=اختر المهام الإضافية التي تريد أن ينفّذها المعالج أثناء تثبيت [name]، ثم اضغط «التالي».

; *** "Select Start Menu Folder" wizard page
WizardSelectProgramGroup=اختيار مجلد قائمة ابدأ
SelectStartMenuFolderDesc=أين تريد وضع اختصارات البرنامج؟
SelectStartMenuFolderLabel3=سينشئ المعالج اختصارات البرنامج في مجلد قائمة ابدأ التالي.
SelectStartMenuFolderBrowseLabel=للمتابعة اضغط «التالي». وإذا أردت اختيار مجلد آخر، فاضغط «استعراض».
MustEnterGroupName=يجب إدخال اسم مجلد.
GroupNameTooLong=اسم المجلد أو المسار طويل جداً.
InvalidGroupName=اسم المجلد غير صالح.
BadGroupName=لا يمكن أن يحتوي اسم المجلد على أي من الأحرف التالية:%n%n%1
NoProgramGroupCheck2=&عدم إنشاء مجلد في قائمة ابدأ

; *** "Ready to Install" wizard page
WizardReady=جاهز للتثبيت
ReadyLabel1=المعالج جاهز الآن لبدء تثبيت [name] على جهازك.
ReadyLabel2a=اضغط «تثبيت» للمتابعة، أو «السابق» لمراجعة الإعدادات أو تغييرها.
ReadyLabel2b=اضغط «تثبيت» للمتابعة.
ReadyMemoUserInfo=معلومات المستخدم:
ReadyMemoDir=مجلد التثبيت:
ReadyMemoType=نوع التثبيت:
ReadyMemoComponents=المكونات المحددة:
ReadyMemoGroup=مجلد قائمة ابدأ:
ReadyMemoTasks=المهام الإضافية:

; *** TDownloadWizardPage wizard page and DownloadTemporaryFile
DownloadingLabel2=جارٍ تنزيل الملفات الإضافية...
ButtonStopDownload=إ&يقاف التنزيل
StopDownload=هل تريد إيقاف التنزيل؟
ErrorDownloadAborted=أُلغي التنزيل
ErrorDownloadFailed=فشل التنزيل: %1 %2
ErrorDownloadSizeFailed=خطأ في قراءة الحجم: %1 %2
ErrorProgress=تقدم غير صالح: %1 من %2
ErrorFileSize=حجم الملف غير صالح: المتوقع %1، الموجود %2

; *** TExtractionWizardPage wizard page and Extract7ZipArchive
ExtractingLabel=جارٍ فك ضغط الملفات الإضافية...
ButtonStopExtraction=إي&قاف فك الضغط
StopExtraction=هل تريد إيقاف فك الضغط؟
ErrorExtractionAborted=أُوقف فك الضغط
ErrorExtractionFailed=فشل فك الضغط: %1

; *** Archive extraction failure details
ArchiveIncorrectPassword=كلمة المرور غير صحيحة
ArchiveIsCorrupted=الأرشيف تالف
ArchiveUnsupportedFormat=صيغة الأرشيف غير مدعومة

; *** "Preparing to Install" wizard page
WizardPreparing=التحضير للتثبيت
PreparingDesc=يستعد المعالج لتثبيت [name] على جهازك.
PreviousInstallNotCompleted=لم يكتمل تثبيت برنامج سابق أو إزالته، ويلزم إعادة تشغيل الجهاز لإكماله.%n%nبعد إعادة التشغيل، شغّل معالج التثبيت مرة أخرى لإكمال تثبيت [name].
CannotContinue=لا يمكن متابعة التثبيت. يُرجى الضغط على «إلغاء الأمر» للخروج.
ApplicationsFound=التطبيقات التالية تستخدم ملفات يجب أن يحدّثها معالج التثبيت. يُستحسن السماح للمعالج بإغلاقها تلقائياً.
ApplicationsFound2=التطبيقات التالية تستخدم ملفات يجب أن يحدّثها معالج التثبيت. يُستحسن السماح للمعالج بإغلاقها تلقائياً، وسيحاول إعادة تشغيلها بعد اكتمال التثبيت.
CloseApplications=إغلاق التطبيقات &تلقائياً
DontCloseApplications=&عدم إغلاق التطبيقات
ErrorCloseApplications=تعذّر على المعالج إغلاق جميع التطبيقات تلقائياً. يُستحسن إغلاق التطبيقات التي تستخدم الملفات المطلوب تحديثها قبل المتابعة.
PrepareToInstallNeedsRestart=يجب إعادة تشغيل الجهاز. بعد إعادة التشغيل، شغّل معالج التثبيت مرة أخرى لإكمال تثبيت [name].%n%nهل تريد إعادة التشغيل الآن؟

; *** "Installing" wizard page
WizardInstalling=جارٍ التثبيت
InstallingLabel=يُرجى الانتظار حتى يُكمل المعالج تثبيت [name] على جهازك.

; *** "Setup Completed" wizard page
FinishedHeadingLabel=اكتمل تثبيت [name]
FinishedLabelNoIcons=أكمل المعالج تثبيت [name] على جهازك.
FinishedLabel=أكمل المعالج تثبيت [name] على جهازك. ويمكنك تشغيل البرنامج من الاختصارات التي أُنشئت.
ClickFinish=اضغط «إنهاء» للخروج من معالج التثبيت.
FinishedRestartLabel=لإكمال تثبيت [name] يجب إعادة تشغيل الجهاز. هل تريد إعادة التشغيل الآن؟
FinishedRestartMessage=لإكمال تثبيت [name] يجب إعادة تشغيل الجهاز.%n%nهل تريد إعادة التشغيل الآن؟
ShowReadmeCheck=نعم، أريد عرض ملف «اقرأني»
YesRadio=&نعم، أعد تشغيل الجهاز الآن
NoRadio=&لا، سأعيد تشغيل الجهاز لاحقاً
; used for example as 'Run MyProg.exe'
RunEntryExec=تشغيل %1
; used for example as 'View Readme.txt'
RunEntryShellExec=عرض %1

; *** "Setup Needs the Next Disk" stuff
ChangeDiskTitle=يحتاج برنامج الإعداد إلى القرص التالي
SelectDiskLabel2=يُرجى إدخال القرص %1 ثم الضغط على «موافق».%n%nإذا كانت ملفات هذا القرص في مجلد غير المجلد الظاهر أدناه، فأدخل المسار الصحيح أو اضغط «استعراض».
PathLabel=ال&مسار:
FileNotInDir2=تعذّر العثور على الملف «%1» في «%2». يُرجى إدخال القرص الصحيح أو اختيار مجلد آخر.
SelectDirectoryLabel=يُرجى تحديد موقع القرص التالي.

; *** Installation phase messages
SetupAborted=لم يكتمل التثبيت.%n%nيُرجى إصلاح المشكلة ثم تشغيل معالج التثبيت مرة أخرى.
AbortRetryIgnoreSelectAction=اختر إجراءً
AbortRetryIgnoreRetry=إعادة ال&محاولة
AbortRetryIgnoreIgnore=&تجاهل الخطأ والمتابعة
AbortRetryIgnoreCancel=إلغاء التثبيت
RetryCancelSelectAction=اختر إجراءً
RetryCancelRetry=إعادة ال&محاولة
RetryCancelCancel=إلغاء الأمر

; *** Installation status messages
StatusClosingApplications=جارٍ إغلاق التطبيقات...
StatusCreateDirs=جارٍ إنشاء المجلدات...
StatusExtractFiles=جارٍ استخراج الملفات...
StatusDownloadFiles=جارٍ تنزيل الملفات...
StatusCreateIcons=جارٍ إنشاء الاختصارات...
StatusCreateIniEntries=جارٍ إنشاء مدخلات INI...
StatusCreateRegistryEntries=جارٍ إنشاء مفاتيح السجل...
StatusRegisterFiles=جارٍ تسجيل الملفات...
StatusSavingUninstall=جارٍ حفظ معلومات الإزالة...
StatusRunProgram=جارٍ إنهاء التثبيت...
StatusRestartingApplications=جارٍ إعادة تشغيل التطبيقات...
StatusRollback=جارٍ التراجع عن التغييرات...

; *** Misc. errors
ErrorInternal2=خطأ داخلي: %1
ErrorFunctionFailedNoCode=فشل %1
ErrorFunctionFailed=فشل %1، رمز الخطأ %2
ErrorFunctionFailedWithMessage=فشل %1، رمز الخطأ %2.%n%3
ErrorExecutingProgram=تعذّر تشغيل الملف:%n%1

; *** Registry errors
ErrorRegOpenKey=خطأ في فتح مفتاح السجل:%n%1\%2
ErrorRegCreateKey=خطأ في إنشاء مفتاح السجل:%n%1\%2
ErrorRegWriteKey=خطأ في الكتابة إلى مفتاح السجل:%n%1\%2

; *** INI errors
ErrorIniEntry=حدث خطأ في إنشاء إدخال INI في الملف "%1".

; *** File copying errors
FileAbortRetryIgnoreSkipNotRecommended=&تخطي هذا الملف (غير مستحسن)
FileAbortRetryIgnoreIgnoreNotRecommended=&تجاهل الخطأ والمتابعة (غير مستحسن)
SourceIsCorrupted=الملف المصدر تالف
SourceVerificationFailed=فشل التحقق من الملف المصدر: %1
VerificationSignatureDoesntExist=ملف التوقيع "%1" غير موجود
VerificationSignatureInvalid=ملف التوقيع "%1" غير صالح
VerificationKeyNotFound=ملف التوقيع "%1" يستخدم مفتاحًا غير معروف
VerificationFileNameIncorrect=اسم الملف غير صحيح
VerificationFileTagIncorrect=علامة الملف غير صحيحة
VerificationFileSizeIncorrect=حجم الملف غير صحيح
VerificationFileHashIncorrect=تجزئة الملف (hash) غير صحيحة
SourceDoesntExist=الملف "%1" غير موجود
ExistingFileReadOnly2=تعذّر استبدال الملف الموجود لأنه للقراءة فقط.
ExistingFileReadOnlyRetry=إ&زالة خاصية القراءة فقط ثم إعادة المحاولة
ExistingFileReadOnlyKeepExisting=الا&حتفاظ بالملف الموجود
ErrorReadingExistingDest=حدث خطأ أثناء محاولة قراءة الملف الموجود:
FileExistsSelectAction=اختر إجراءً
FileExists2=الملف موجود بالفعل.
FileExistsOverwriteExisting=&استبدال الملف الموجود
FileExistsKeepExisting=الا&حتفاظ بالملف الموجود
FileExistsOverwriteOrKeepAll=تطبيق هذا الاختيار على التعارضات ال&تالية
ExistingFileNewerSelectAction=اختر إجراءً
ExistingFileNewer2=الملف الموجود أحدث من الملف الذي سيثبّته المعالج.
ExistingFileNewerOverwriteExisting=ا&ستبدال الملف الموجود
ExistingFileNewerKeepExisting=الا&حتفاظ بالملف الموجود (مستحسن)
ExistingFileNewerOverwriteOrKeepAll=تطبيق هذا الاختيار على التعارضات ال&تالية
ErrorChangingAttr=حدث خطأ أثناء محاولة تغيير سمات الملف الموجود:
ErrorCreatingTemp=حدث خطأ أثناء إنشاء ملف في مجلد التثبيت:
ErrorReadingSource=حدث خطأ أثناء قراءة ملف المصدر:
ErrorCopying=حدث خطأ أثناء نسخ ملف:
ErrorDownloading=حدث خطأ أثناء تنزيل ملف:
ErrorExtracting=حدث خطأ أثناء استخراج ملفات من الأرشيف:
ErrorReplacingExistingFile=حدث خطأ أثناء استبدال الملف الموجود:
ErrorRestartReplace=فشل الاستبدال عند إعادة التشغيل:
ErrorRenamingTemp=حدث خطأ أثناء إعادة تسمية ملف في مجلد التثبيت:
ErrorRegisterServer=تعذر تسجيل ملفات DLL/OCX: %1
ErrorRegSvr32Failed=فشل RegSvr32 برمز الخروج %1
ErrorRegisterTypeLib=تعذّر تسجيل مكتبة الأنواع: %1

; *** Uninstall display name markings
; used for example as 'My Program (32-bit)'
UninstallDisplayNameMark=%1 (%2)
; used for example as 'My Program (32-bit, All users)'
UninstallDisplayNameMarks=%1 (%2, %3)
UninstallDisplayNameMark32Bit=32-bit
UninstallDisplayNameMark64Bit=64-bit
UninstallDisplayNameMarkAllUsers=جميع المستخدمين
UninstallDisplayNameMarkCurrentUser=المستخدم الحالي

; *** Post-installation errors
ErrorOpeningReadme=حدث خطأ أثناء فتح ملف «اقرأني».
ErrorRestartingComputer=تعذّر على المعالج إعادة تشغيل الجهاز. يُرجى إعادة تشغيله يدوياً.

; *** Uninstaller messages
UninstallNotFound=الملف «%1» غير موجود. تتعذّر الإزالة.
UninstallOpenError=تعذّر فتح الملف «%1». تتعذّر الإزالة
UninstallUnsupportedVer=صيغة سجل الإزالة «%1» لا يتعرّف عليها هذا الإصدار من برنامج الإزالة. تتعذّر الإزالة
UninstallUnknownEntry=وُجد إدخال غير معروف (%1) في سجل الإزالة
ConfirmUninstall=هل تريد إزالة %1 وجميع مكوناته بالكامل؟
UninstallOnlyOnWin64=لا يمكن إزالة هذا البرنامج إلا على إصدار ويندوز 64 بت.
OnlyAdminCanUninstall=لا يمكن إزالة هذا البرنامج إلا بحساب له صلاحيات المسؤول.
UninstallStatusLabel=يُرجى الانتظار حتى تكتمل إزالة %1 من جهازك.
UninstalledAll=أُزيل %1 من جهازك بنجاح.
UninstalledMost=اكتملت إزالة %1.%n%nتعذّرت إزالة بعض العناصر، ويمكنك حذفها يدوياً.
UninstalledAndNeedsRestart=لإكمال إزالة %1 يجب إعادة تشغيل الجهاز.%n%nهل تريد إعادة التشغيل الآن؟
UninstallDataCorrupted=الملف «%1» تالف. تتعذّر الإزالة

; *** Uninstallation phase messages
ConfirmDeleteSharedFileTitle=إزالة ملف مشترك؟
ConfirmDeleteSharedFile2=يشير النظام إلى أن الملف المشترك التالي لم يعد يستخدمه أي برنامج. هل تريد حذفه؟%n%nإذا كانت هناك برامج ما زالت تستخدمه، فقد لا تعمل بشكل صحيح بعد حذفه. إذا لم تكن متأكداً فاختر «لا»؛ فبقاء الملف على جهازك لا يسبب أي ضرر.
SharedFileNameLabel=اسم الملف:
SharedFileLocationLabel=الموقع:
WizardUninstalling=حالة الإزالة
StatusUninstalling=جارٍ إزالة %1...

; *** Shutdown block reasons
ShutdownBlockReasonInstallingApp=جارٍ تثبيت %1.
ShutdownBlockReasonUninstallingApp=جارٍ إزالة %1.

; The custom messages below aren't used by Setup itself, but if you make
; use of them in your scripts, you'll want to translate them.

[CustomMessages]

NameAndVersion=%1 الإصدار %2
AdditionalIcons=اختصارات إضافية:
CreateDesktopIcon=إنشاء اختصار على سطح المكتب
CreateQuickLaunchIcon=إنشاء اختصار في شريط «التشغيل السريع»
ProgramOnTheWeb=موقع %1 على الإنترنت
UninstallProgram=إزالة %1
LaunchProgram=تشغيل %1
AssocFileExtension=ربط %1 بامتداد الملفات %2
AssocingFileExtension=جارٍ ربط %1 بامتداد الملفات %2...
AutoStartProgramGroupDescription=بدء التشغيل:
AutoStartProgram=تشغيل %1 تلقائياً
AddonHostProgramNotFound=تعذّر العثور على %1 في المجلد الذي اخترته.%n%nهل تريد المتابعة على أي حال؟
