# بناء نسخة exe من البرنامج في مجلد dist\AudioTranscriber
# التشغيل:  powershell -ExecutionPolicy Bypass -File build.ps1
# النماذج لا تُضمَّن (حجمها جيجابايتات): انسخ مجلد models بجانب الـ exe، أو حمّل النموذج من داخل البرنامج.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller main.py `
    --name AudioTranscriber `
    --windowed `
    --onedir `
    --noconfirm `
    --clean `
    --add-data "locales;locales" `
    --add-data "assets;assets" `
    --icon "assets/app.ico" `
    --collect-data faster_whisper `
    --collect-binaries ctranslate2 `
    --collect-all onnxruntime `
    --collect-all av `
    --hidden-import docx `
    --exclude-module tests

if ($LASTEXITCODE -ne 0) { throw "Build failed" }
Write-Host "Done: dist\AudioTranscriber\AudioTranscriber.exe"
