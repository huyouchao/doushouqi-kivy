[app]

# Application metadata
title = 斗兽棋
package.name = doushouqi
package.domain = com.huyouchao
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttc,otf,txt,md,ico
source.exclude_dirs = .git,.venv,.vscode,__pycache__,bin,build,dist,cache,saves
source.exclude_patterns = *.pyc,*.pyo,*.log
version = 1.0.0

# Runtime requirements
requirements = python3,kivy
orientation = all
fullscreen = 0

# Android resources
icon.filename = assets/icon/icon_512.png
presplash.filename = assets/icon/presplash.png

# Android compatibility
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a

# The following values depend on the final cloud build environment.
# If the selected build image already provides compatible defaults,
# you can leave them commented out. Otherwise set them explicitly.
# android.api = 34
# android.ndk = 25b
# p4a.branch = master

# No special permissions are currently required.
# android.permissions =

# Keep only application sources and bundled resources in the APK.
android.add_assets =

[buildozer]
log_level = 2
warn_on_root = 1
