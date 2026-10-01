<#
إزالة «الباحث الصوتي في الملفات». يسأل المستخدم: هل يحذف بياناته أيضاً (الإعدادات والقواميس والنماذج)؟
#>
param(
    [string]$AppId = "AudioTranscriber",
    [string]$StartMenuDir = [Environment]::GetFolderPath("Programs"),
    [string]$DesktopDir = [Environment]::GetFolderPath("Desktop"),
    [switch]$Quiet,
    [switch]$KeepData,
    [switch]$RemoveData
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
$Arabic = (Get-UICulture).Name -like "ar*"
function T($ar, $en) { if ($Arabic) { $ar } else { $en } }
$AppName = T "الباحث الصوتي في الملفات" "Audio File Searcher"
$ExeName = "AudioTranscriber.exe"
$InstallDir = $PSScriptRoot
$UserData = @("config.json", "learning.json", "models", "logs", "recovery", "inbox")

function Ask($text) {
    if ($Quiet) { return "Yes" }
    return [System.Windows.Forms.MessageBox]::Show($text, $AppName, "YesNo", "Question").ToString()
}

if ((Ask (T "هل تريد إزالة «$AppName»؟" "Remove «$AppName»?")) -ne "Yes") { exit 0 }

$running = Get-Process -Name "AudioTranscriber" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($InstallDir, [StringComparison]::OrdinalIgnoreCase) }
if ($running) {
    if (-not $Quiet) {
        [System.Windows.Forms.MessageBox]::Show((T "البرنامج مفتوح حالياً. أغلقه ثم أعد المحاولة." `
            "The program is open. Close it and try again."), $AppName, "OK", "Warning") | Out-Null
    }
    exit 2
}

# البيانات: الإعدادات والقواميس وما تعلّمه البرنامج والنماذج (قد تكون عدة جيجابايتات)
$deleteData = $RemoveData
if (-not $KeepData -and -not $RemoveData -and -not $Quiet) {
    $deleteData = (Ask (T "هل تريد حذف بياناتك أيضاً؟`n(الإعدادات، والقواميس، وما تعلّمه البرنامج، والنماذج المحمّلة)`n`nاختر «لا» للاحتفاظ بها إذا كنت ستعيد تثبيت البرنامج." `
        "Also delete your data?`n(settings, dictionaries, what the program learned, and downloaded models)`n`nChoose No to keep them if you plan to reinstall.")) -eq "Yes"
}

Remove-Item -LiteralPath (Join-Path $StartMenuDir "$AppName.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $DesktopDir "$AppName.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Classes\Applications\$ExeName" -Recurse -Force -ErrorAction SilentlyContinue
foreach ($ext in @(".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".opus")) {
    Remove-Item -Path "HKCU:\Software\Classes\$ext\OpenWithList\$ExeName" -Recurse -Force -ErrorAction SilentlyContinue
}
Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId" -Recurse -Force -ErrorAction SilentlyContinue

# ملفات البرنامج (هذا السكريبت نفسه آخرها، فيُحذف بعد انتهائه)
Get-ChildItem -LiteralPath $InstallDir -Force | Where-Object {
    $_.Name -ne "uninstall.ps1" -and ($deleteData -or $UserData -notcontains $_.Name)
} | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$self = Join-Path $InstallDir "uninstall.ps1"
$left = @(Get-ChildItem -LiteralPath $InstallDir -Force | Where-Object { $_.Name -ne "uninstall.ps1" })
# حذف السكريبت والمجلد بعد خروج PowerShell (لا يمكن حذف ملف أثناء تشغيله)
$cleanup = if ($left.Count -eq 0) { "rmdir /s /q `"$InstallDir`"" } else { "del /f /q `"$self`"" }
Start-Process -WindowStyle Hidden cmd.exe -ArgumentList "/c timeout /t 2 /nobreak >nul & $cleanup"

if (-not $Quiet) {
    $msg = if ($deleteData) { T "تمت إزالة البرنامج وبياناته." "The program and its data were removed." } `
           else { T "تمت إزالة البرنامج، وبقيت بياناتك في:`n$InstallDir" "The program was removed. Your data was kept in:`n$InstallDir" }
    [System.Windows.Forms.MessageBox]::Show($msg, $AppName, "OK", "Information") | Out-Null
}
exit 0
