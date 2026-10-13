#!/usr/bin/env python3
"""Transcrit un enregistrement d'audit en local avec faster-whisper.

L'audio ne quitte pas la machine : seul le modèle est téléchargé (une fois,
depuis Hugging Face) au premier lancement.

  pip install faster-whisper
  transcrire.py entretien.m4a [--modele small|medium|large-v3] >> 00-source.md

Sortie : une ligne par segment, « [hh:mm:ss] texte ». Pas de séparation des
locuteurs : le signaler dans l'en-tête de 00-source.md. « small » tient sur un
portable sans carte graphique ; « large-v3 » est nettement plus juste sur les
noms propres et les chiffres, mais plusieurs fois plus lent.
"""
import argparse
import shutil
import subprocess
import sys


def horodatage(s):
    s = int(s)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def charger_audio(chemin):
    """Décode en PCM 16 kHz mono via ffmpeg : évite le décodeur PyAV embarqué,
    dont certaines versions sont incompatibles avec faster-whisper."""
    if not shutil.which("ffmpeg"):
        return chemin
    import numpy as np
    brut = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", chemin, "-f", "s16le",
                           "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(brut, np.int16).astype(np.float32) / 32768.0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("audio")
    p.add_argument("--modele", default="small")
    p.add_argument("--langue", default="fr")
    a = p.parse_args()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper absent : pip install faster-whisper "
                 "(ou importer l'enregistrement dans Noota et repartir de sa transcription)")
    modele = WhisperModel(a.modele, device="auto", compute_type="int8")
    segments, info = modele.transcribe(charger_audio(a.audio), language=a.langue, vad_filter=True, beam_size=5)
    print(f"<!-- Transcription automatique locale (faster-whisper, modèle {a.modele}), "
          f"durée {horodatage(info.duration)}, sans séparation des locuteurs. -->\n")
    n = 0
    for seg in segments:
        texte = seg.text.strip()
        if texte:
            print(f"[{horodatage(seg.start)}] {texte}", flush=True)
            n += 1
    if n == 0:
        sys.exit("Aucune parole détectée : vérifier le fichier audio.")
    print(f"{n} segments transcrits.", file=sys.stderr)


if __name__ == "__main__":
    main()
