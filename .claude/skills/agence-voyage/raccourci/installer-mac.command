#!/bin/bash
# Crée sur le bureau un raccourci « Agence de voyage » vers Claude Code (claude.ai/code), avec son icône.
set -e
ici="$(cd "$(dirname "$0")" && pwd)"
cible="$HOME/Desktop/Agence de voyage.webloc"
cat > "$cible" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>URL</key><string>https://claude.ai/code</string></dict></plist>
PLIST
ICONE="$ici/agence-voyage.icns" CIBLE="$cible" osascript -l JavaScript -e '
  ObjC.import("AppKit");
  const env = $.NSProcessInfo.processInfo.environment;
  const image = $.NSImage.alloc.initWithContentsOfFile(env.objectForKey("ICONE"));
  $.NSWorkspace.sharedWorkspace.setIconForFileOptions(image, env.objectForKey("CIBLE"), 0);' >/dev/null
echo "Raccourci « Agence de voyage » créé sur le bureau."
