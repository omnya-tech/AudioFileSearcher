<#
تثبيت «الباحث الصوتي في الملفات» في حساب المستخدم الحالي (لا يحتاج صلاحيات المسؤول):
  - نسخ البرنامج إلى %LOCALAPPDATA%\Programs\AudioTranscriber
  - اختصارات في قائمة ابدأ وسطح المكتب
  - تسجيله في «التطبيقات» بويندوز لإزالته من هناك، وفي قائمة «فتح باستخدام» للملفات الصوتية
عند التحديث: تُستبدل ملفات البرنامج فقط، وتبقى الإعدادات والقواميس والنماذج كما هي.
#>
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\AudioTranscriber"),
    [string]$StartMenuDir = [Environment]::GetFolderPath("Programs"),
    [string]$DesktopDir = [Environment]::GetFolderPath("Desktop"),
    [string]$AppId = "AudioTranscriber",
    [switch]$NoDesktopShortcut,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms

$Arabic = (Get-UICulture).Name -like "ar*"
function T($ar, $en) { if ($Arabic) { $ar } else { $en } }
$AppName = T "الباحث الصوتي في الملفات" "Audio File Searcher"
$Version = "1.0.0"
$Publisher = "Omnya Software"
$ExeName = "AudioTranscriber.exe"
$AudioExtensions = @(".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".opus")
# ملفات بيانات المستخدم: لا تُمس عند التحديث
$UserData = @("config.json", "learning.json", "models", "logs", "recovery", "inbox")

function Say($text, $icon = "Information") {
    Write-Host $text
    if (-not $Quiet) {
        [System.Windows.Forms.MessageBox]::Show($text, $AppName, "OK", $icon) | Out-Null
    }
}

$Source = Join-Path $PSScriptRoot "AudioTranscriber"
if (-not (Test-Path (Join-Path $Source $ExeName))) {
    Say (T "لم يُعثر على ملفات البرنامج بجانب ملف التثبيت (المجلد AudioTranscriber)." `
           "Program files were not found next to the installer (AudioTranscriber folder).") "Error"
    exit 1
}

# البرنامج مفتوح: لا يمكن استبدال ملفاته
$running = Get-Process -Name "AudioTranscriber" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($InstallDir, [StringComparison]::OrdinalIgnoreCase) }
if ($running) {
    Say (T "البرنامج مفتوح حالياً. أغلقه ثم شغّل التثبيت مرة أخرى." `
           "The program is currently open. Close it and run the installer again.") "Warning"
    exit 2
}

$Upgrade = Test-Path (Join-Path $InstallDir $ExeName)
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# حذف ملفات الإصدار السابق فقط (ما عدا بيانات المستخدم)، ثم نسخ الإصدار الجديد
if ($Upgrade) {
    Get-ChildItem -LiteralPath $InstallDir -Force | Where-Object { $UserData -notcontains $_.Name } |
        Remove-Item -Recurse -Force
}
Copy-Item -Path (Join-Path $Source "*") -Destination $InstallDir -Recurse -Force
foreach ($f in @("uninstall.ps1", "uninstall.bat")) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $f) -Destination $InstallDir -Force
}
# نموذج مرفق مع حزمة التثبيت (اختياري): يُنسخ حتى يعمل البرنامج دون إنترنت من البداية
$BundledModels = Join-Path $PSScriptRoot "models"
if (Test-Path $BundledModels) {
    Copy-Item -Path (Join-Path $BundledModels "*") -Destination (Join-Path $InstallDir "models") -Recurse -Force
}

$Exe = Join-Path $InstallDir $ExeName
$Shell = New-Object -ComObject WScript.Shell
function New-Shortcut($path) {
    $lnk = $Shell.CreateShortcut($path)
    $lnk.TargetPath = $Exe
    $lnk.WorkingDirectory = $InstallDir
    $lnk.IconLocation = "$Exe,0"
    $lnk.Description = $AppName
    $lnk.Save()
}
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
New-Shortcut (Join-Path $StartMenuDir "$AppName.lnk")
if (-not $NoDesktopShortcut) {
    New-Item -ItemType Directory -Force -Path $DesktopDir | Out-Null
    New-Shortcut (Join-Path $DesktopDir "$AppName.lnk")
}

# «فتح باستخدام» للملفات الصوتية
$AppKey = "HKCU:\Software\Classes\Applications\$ExeName"
New-Item -Path "$AppKey\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path $AppKey -Name "FriendlyAppName" -Value $AppName
Set-ItemProperty -Path "$AppKey\shell\open\command" -Name "(default)" -Value "`"$Exe`" `"%1`""
New-Item -Path "$AppKey\SupportedTypes" -Force | Out-Null
foreach ($ext in $AudioExtensions) {
    Set-ItemProperty -Path "$AppKey\SupportedTypes" -Name $ext -Value ""
    $progIds = "HKCU:\Software\Classes\$ext\OpenWithList\$ExeName"
    New-Item -Path $progIds -Force | Out-Null
}

# التسجيل في «التطبيقات» بويندوز
$sizeKb = [int]((Get-ChildItem -LiteralPath $InstallDir -Recurse -File | Measure-Object Length -Sum).Sum / 1KB)
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
New-Item -Path $UninstallKey -Force | Out-Null
$props = @{
    DisplayName = $AppName; DisplayVersion = $Version; Publisher = $Publisher
    InstallLocation = $InstallDir; DisplayIcon = "$Exe,0"; EstimatedSize = $sizeKb
    UninstallString = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\uninstall.ps1`" -AppId $AppId"
    NoModify = 1; NoRepair = 1
}
foreach ($k in $props.Keys) { Set-ItemProperty -Path $UninstallKey -Name $k -Value $props[$k] }

if ($Upgrade) {
    Say (T "تم تحديث البرنامج إلى الإصدار $Version، وبقيت إعداداتك وقواميسك ونماذجك كما هي." `
           "The program was updated to version $Version. Your settings, dictionaries and models were kept.")
} else {
    Say (T "تم تثبيت البرنامج بنجاح.`nستجده في قائمة ابدأ وعلى سطح المكتب باسم «$AppName»." `
           "The program was installed successfully.`nYou will find «$AppName» in the Start menu and on the desktop.")
}
exit 0
