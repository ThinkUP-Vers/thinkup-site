@echo off
chcp 65001 >nul
rem Crée sur le bureau un raccourci « Agence de voyage » vers Claude Code (claude.ai/code), avec son icône.
rem L'icône est copiée dans %LOCALAPPDATA%\ThinkUP pour survivre à la suppression du dossier téléchargé.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d = Join-Path $env:LOCALAPPDATA 'ThinkUP';" ^
  "New-Item -ItemType Directory -Force -Path $d | Out-Null;" ^
  "Copy-Item -Force -LiteralPath '%~dp0agence-voyage.ico' -Destination $d;" ^
  "$bureau = [Environment]::GetFolderPath('Desktop');" ^
  "Set-Content -Encoding ASCII -LiteralPath (Join-Path $bureau 'Agence de voyage.url') -Value @('[InternetShortcut]', 'URL=https://claude.ai/code', ('IconFile=' + (Join-Path $d 'agence-voyage.ico')), 'IconIndex=0')"
if errorlevel 1 (
  echo Échec : voir LISEZMOI.md, méthode manuelle.
) else (
  echo Raccourci « Agence de voyage » créé sur le bureau.
)
pause
