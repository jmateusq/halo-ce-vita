#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""
BUILD_LINUX.PY

Builds HaloCEVitaInstaller, the install helper as one native Linux program.
Run from any folder:

    python -m pip install -r tools/installer/requirements-build.txt
    python tools/installer/build_linux.py                 -> tools/installer/dist/HaloCEVitaInstaller
    python tools/installer/build_linux.py --no-ffmpeg     (a smaller program, no movie step without ffmpeg)
    python tools/installer/build_linux.py --ffmpeg PATH   (bundle this ffmpeg instead of the one on PATH)

The Linux program is the same tool as HaloCEVitaInstaller.exe: the window,
the five steps and the command line. PyInstaller bundles Python, tkinter,
the window's pictures and Modern look, and (unless --no-ffmpeg) the ffmpeg
found on PATH, with the shared libraries it needs. It is not a Windows .exe
and does not need Wine: it is an ELF program built for the machine it runs
on. The program needs a display for the window, like any Tk program; the
command-line steps run without one.

Because a Linux program bundles the ffmpeg it was built with, build it on the
oldest distribution you want it to run on (glibc and its FFmpeg libraries are
forward compatible, not backward compatible).
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FFMPEG_FOLDER = os.path.join(BUILD, "ffmpeg")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_ffmpeg(explicit):
    if explicit:
        return explicit if os.path.isfile(explicit) else shutil.which(explicit)
    return shutil.which("ffmpeg")


def stage_ffmpeg(path):
    """Puts ffmpeg in build/ffmpeg with the licence text PyInstaller bundles
    next to it. The shared libraries it needs are collected by PyInstaller
    (the spec passes it as a binary on Linux)."""
    shutil.rmtree(FFMPEG_FOLDER, ignore_errors=True)
    os.makedirs(FFMPEG_FOLDER)
    target = os.path.join(FFMPEG_FOLDER, "ffmpeg")
    shutil.copy2(path, target)
    os.chmod(target, 0o755)
    try:
        version = subprocess.run([target, "-hide_banner", "-version"], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
                                 check=False).stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError) as error:
        sys.exit("ffmpeg at %s does not run: %s" % (path, error))
    if not version:
        sys.exit("ffmpeg at %s printed no version: refusing it" % path)
    with open(os.path.join(FFMPEG_FOLDER, "README.txt"), "w", encoding="utf-8") as file:
        file.write("FFmpeg, bundled from %s for this Linux build of HaloCEVitaInstaller.\n\n%s\n\n"
                   "FFmpeg's source: https://ffmpeg.org/download.html#get-sources\n"
                   % (os.path.abspath(path), version))
    try:
        licence = subprocess.run([target, "-hide_banner", "-L"], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
                                 check=False).stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError):
        licence = ""
    with open(os.path.join(FFMPEG_FOLDER, "LICENSE"), "w", encoding="utf-8") as file:
        file.write((licence or "FFmpeg: see https://ffmpeg.org/legal.html") + "\n")
    print("ffmpeg ready in", FFMPEG_FOLDER, flush=True)


def main():
    parser = argparse.ArgumentParser(description="Build the Halo CE Vita install helper for Linux with PyInstaller.")
    parser.add_argument("--no-ffmpeg", action="store_true", help="leave ffmpeg out")
    parser.add_argument("--ffmpeg", metavar="PATH", help="the ffmpeg program to bundle (default: the one on PATH)")
    arguments = parser.parse_args()
    if arguments.no_ffmpeg:
        shutil.rmtree(FFMPEG_FOLDER, ignore_errors=True)
    else:
        ffmpeg = find_ffmpeg(arguments.ffmpeg)
        if not ffmpeg:
            sys.exit("ffmpeg was not found. Install it, give --ffmpeg PATH, or use --no-ffmpeg "
                     "(the movie step is optional).")
        stage_ffmpeg(ffmpeg)
    environment = dict(os.environ, HCV_FFMPEG_DIR="" if arguments.no_ffmpeg else FFMPEG_FOLDER)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", os.path.join(HERE, "dist"), "--workpath", os.path.join(BUILD, "pyinstaller"),
                    os.path.join(HERE, "halo_ce_vita_installer.spec")], check=True, env=environment)
    program = os.path.join(HERE, "dist", "HaloCEVitaInstaller")
    print("built", program, "SHA-256", sha256(program))


if __name__ == "__main__":
    main()
