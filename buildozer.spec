[app]

# Application metadata
title = Jungle Chess
package.name = doushouqi
package.domain = org.doushouqi
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttc,otf,txt,md,ico
source.exclude_dirs = .git,.venv,.vscode,__pycache__,bin,build,dist,.buildozer,cache,saves
source.exclude_patterns = *.pyc,*.pyo,*.log
version = 1.0.0

# Runtime requirements
requirements = kivy
orientation = landscape
fullscreen = 0

# Android resources
icon.filename = %(source.dir)s/assets/icon/icon_512.png
splash.filename = %(source.dir)s/assets/icon/splash.png

# Android compatibility
android.minapi = 26
android.archs = arm64-v8a,armeabi-v7a
android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1