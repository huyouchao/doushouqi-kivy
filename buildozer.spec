[app]

# Application metadata (NOTE: no Chinese, no BOM allowed!)
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
orientation = all
fullscreen = 0

# Android resources (must match actual filenames in assets/icon/)
icon.filename = %(source.dir)s/assets/icon/icon_512.png
splash.filename = %(source.dir)s/assets/icon/presplash.png

# Android compatibility settings
android.minapi = 26
android.api = 33
android.build_tools_version = 33.0.2
android.archs = arm64-v8a,armeabi-v7a
android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1
