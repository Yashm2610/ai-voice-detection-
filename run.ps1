# Run from the folder that contains main.py
Set-Location $PSScriptRoot
Write-Host "Starting VoiceGuard from: $(Get-Location)"
Write-Host ""
Write-Host "Open in your browser:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ""
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
