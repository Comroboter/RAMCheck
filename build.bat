@echo off
REM Builds everything for a release into dist\
REM   RAMCheck-Setup-1.0.exe     installer (Start menu entry, uninstaller)
REM   RAMCheck-Portable-1.0.exe  single file, runs without installing
REM   RAMCheck-cli.exe           terminal version
REM   SHA256SUMS.txt             checksums, so people can verify their download
REM Needs Python. The installer also needs Inno Setup 6:  winget install JRSoftware.InnoSetup
REM GitHub Actions runs this same file for every release (see .github\workflows\release.yml).
setlocal
cd /d "%~dp0"
set ROOT=%~dp0
set VER=1.0
REM --noupx: packed exes look suspicious to virus scanners, so they stay unpacked
set COMMON=--noconfirm --clean --noupx --icon "%ROOT%ramcheck.ico" --version-file "%ROOT%version_info.txt" --specpath build --distpath dist

python -m pip install --upgrade pyinstaller psutil || goto :fail
if exist dist rmdir /s /q dist

echo.
echo [1/5] Window app for the installer
python -m PyInstaller %COMMON% --workpath build\app --onedir --windowed --name RAMCheck ram_check.py || goto :fail

echo.
echo [2/5] Portable single file
python -m PyInstaller %COMMON% --workpath build\portable --onefile --windowed --name RAMCheck-Portable-%VER% ram_check.py || goto :fail

echo.
echo [3/5] Terminal version
python -m PyInstaller %COMMON% --workpath build\cli --onefile --console --name RAMCheck-cli cli.py || goto :fail

echo.
echo [4/5] Installer
set ISCC=
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
  if exist %%P set ISCC=%%P
)
if not defined ISCC (
  echo Inno Setup 6 not found, skipping the installer.
  echo Install it with:  winget install JRSoftware.InnoSetup   and run build.bat again.
  goto :sums
)
%ISCC% /Qp installer.iss || goto :fail

:sums
echo.
echo [5/5] Checksums
powershell -NoProfile -Command "Get-ChildItem dist\*.exe | Get-FileHash -Algorithm SHA256 | ForEach-Object { $_.Hash.ToLower() + '  ' + (Split-Path $_.Path -Leaf) } | Set-Content -Encoding ascii dist\SHA256SUMS.txt" || goto :fail
type dist\SHA256SUMS.txt

echo.
echo Done. Files for the release are in dist\
if not defined CI pause
exit /b 0

:fail
echo.
echo Build failed, see the messages above.
if not defined CI pause
exit /b 1
