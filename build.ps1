# Build Continuum as a Windows desktop bundle (PyInstaller onedir).
# Output: dist\Continuum\Continuum.exe

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing build dependencies..."
python -m pip install -r requirements.txt pyinstaller -q

Write-Host "Stopping any running Continuum instance..."
Stop-Process -Name Continuum -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "Building Continuum..."
python -m PyInstaller continuum.spec --noconfirm --clean

$exe = Join-Path $PSScriptRoot "dist\Continuum\Continuum.exe"
if (Test-Path $exe) {
    $size = (Get-ChildItem "dist\Continuum" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ""
    Write-Host "Build complete!"
    Write-Host "  Executable: $exe"
    Write-Host ("  Folder size: {0:N1} MB" -f $size)
    Write-Host ""
    Write-Host "Copy the entire dist\Continuum folder to distribute the app."
    Write-Host "User data is stored in %USERPROFILE%\.continuum\"
} else {
    Write-Error "Build failed — Continuum.exe not found."
    exit 1
}
