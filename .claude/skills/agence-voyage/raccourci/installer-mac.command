#!/bin/bash
# Crée sur le bureau un raccourci « Agence de voyage » qui ouvre Claude Code avec le dépôt thinkup-site
# sélectionné et /agence-voyage déjà tapé. Dans le plist, & s'écrit &amp;.
set -e
ici="$(cd "$(dirname "$0")" && pwd)"
cible="$HOME/Desktop/Agence de voyage.webloc"
cat > "$cible" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>URL</key><string>https://claude.ai/code?prompt=/agence-voyage%20&amp;repositories=ThinkUP-Vers/thinkup-site</string></dict></plist>
PLIST
ICONE="$ici/agence-voyage.icns" CIBLE="$cible" osascript -l JavaScript -e '
  ObjC.import("AppKit");
  const env = $.NSProcessInfo.processInfo.environment;
  const image = $.NSImage.alloc.initWithContentsOfFile(env.objectForKey("ICONE"));
  $.NSWorkspace.sharedWorkspace.setIconForFileOptions(image, env.objectForKey("CIBLE"), 0);' >/dev/null
echo "Raccourci « Agence de voyage » créé sur le bureau."
