# بناء البرنامج ومثبته:
#   1) نسخة exe في dist\AudioTranscriber (PyInstaller)
#   2) المثبت dist\AudioTranscriber-Setup-<الإصدار>.exe (Inno Setup 7)
# التشغيل:  powershell -ExecutionPolicy Bypass -File build.ps1
#           أضف -SkipInstaller لبناء نسخة exe فقط.
# النماذج لا تُضمَّن (حجمها جيجابايتات): يحمّلها المستخدم من داخل البرنامج عند أول تشغيل.
param([switch]$SkipInstaller)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# رقم الإصدار له مصدر واحد: ملف اللغة (يظهر في عنوان النافذة وفي «حول البرنامج»)
$Version = (Get-Content "locales\en.json" -Raw -Encoding UTF8 | ConvertFrom-Json).app_version

python -m PyInstaller main.py `
    --name AudioTranscriber `
    --windowed `
    --onedir `
    --noconfirm `
    --clean `
    --add-data "locales;locales" `
    --add-data "assets;assets" `
    --add-data "docs;docs" `
    --icon "assets/app.ico" `
    --collect-data faster_whisper `
    --collect-binaries ctranslate2 `
    --collect-all onnxruntime `
    --collect-all av `
    --hidden-import docx `
    --exclude-module tests

if ($LASTEXITCODE -ne 0) { throw "Build failed" }
Write-Host "Done: dist\AudioTranscriber\AudioTranscriber.exe (version $Version)"
if ($SkipInstaller) { exit 0 }

# صفحة الاتفاقية في المثبت بلغته: إشعار بالعربية أو بالإنجليزية، ثم النص الرسمي للرخصة
$Utf8Bom = New-Object System.Text.UTF8Encoding $true
$License = [IO.File]::ReadAllText("$PSScriptRoot\LICENSE")
New-Item -ItemType Directory -Force -Path "build" | Out-Null
foreach ($lang in "ar", "en") {
    $notice = [IO.File]::ReadAllText("$PSScriptRoot\installer\license_notice_$lang.txt")
    [IO.File]::WriteAllText("$PSScriptRoot\build\license_$lang.txt", $notice + $License, $Utf8Bom)
}

$Iscc = @("${env:ProgramFiles}\Inno Setup 7\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "${env:LOCALAPPDATA}\Programs\Inno Setup 7\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup was not found. Install it from https://jrsoftware.org/isdl.php" }
& $Iscc /Q "/DAppVersion=$Version" "installer\AudioTranscriber.iss"
if ($LASTEXITCODE -ne 0) { throw "Installer build failed" }
Write-Host "Done: dist\AudioTranscriber-Setup-$Version.exe"
