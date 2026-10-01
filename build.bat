@echo off
REM Builds everything for a release into dist\
REM   Ramwise-Setup.exe       installer (Start menu entry, uninstaller)
REM   Ramwise-Portable.exe    single file, runs without installing
REM   Ramwise-cli.exe         terminal version
REM   SHA256SUMS.txt          checksums, so people can verify their download
REM The version number comes from VERSION in core.py, nothing else needs changing for a new release.
REM Needs Python. The installer also needs Inno Setup 6:  winget install JRSoftware.InnoSetup
REM GitHub Actions runs this same file for every release (see .github\workflows\release.yml).
setlocal
cd /d "%~dp0"
set ROOT=%~dp0

python -m pip install --upgrade pyinstaller psutil || goto :fail
for /f %%v in ('python tools\build_helpers.py version') do set VER=%%v
echo Building Ramwise %VER%
if exist dist rmdir /s /q dist
python tools\build_helpers.py version-info build\version_info.txt || goto :fail

REM --noupx: packed exes look suspicious to virus scanners, so they stay unpacked
REM --splash: the dark start screen that shows while the app loads
set COMMON=--noconfirm --clean --noupx --icon "%ROOT%ramwise.ico" --version-file "%ROOT%build\version_info.txt" --specpath build --distpath dist

echo.
echo [1/5] Window app for the installer
python -m PyInstaller %COMMON% --workpath build\app --onedir --windowed --splash "%ROOT%docs\splash.png" --name Ramwise ramwise.py || goto :fail

echo.
echo [2/5] Portable single file
python -m PyInstaller %COMMON% --workpath build\portable --onefile --windowed --splash "%ROOT%docs\splash.png" --name Ramwise-Portable ramwise.py || goto :fail

echo.
echo [3/5] Terminal version
python -m PyInstaller %COMMON% --workpath build\cli --onefile --console --name Ramwise-cli cli.py || goto :fail

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
%ISCC% /Qp /DAppVersion=%VER% installer.iss || goto :fail
REM Copy under the old name, so the update button in versions called RAMCheck (1.2.x) still finds it.
REM Can be removed once nobody uses those versions anymore.
copy /y dist\Ramwise-Setup.exe dist\RAMCheck-Setup.exe >nul

:sums
echo.
echo [5/5] Checksums
powershell -NoProfile -Command "Get-ChildItem dist\*.exe | Get-FileHash -Algorithm SHA256 | ForEach-Object { $_.Hash.ToLower() + '  ' + (Split-Path $_.Path -Leaf) } | Set-Content -Encoding ascii dist\SHA256SUMS.txt" || goto :fail
type dist\SHA256SUMS.txt

echo.
echo Done. Ramwise %VER% is in dist\
if not defined CI pause
exit /b 0

:fail
echo.
echo Build failed, see the messages above.
if not defined CI pause
exit /b 1
