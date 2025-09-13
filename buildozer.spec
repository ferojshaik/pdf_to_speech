[app]

# (str) Title of your application
title = PDF to Speech

# (str) Package name
package.name = pdftospeech

# (str) Package domain (needed for android/ios packaging)
package.domain = com.example.pdftospeech

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,txt

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
requirements = python3,kivy,pillow,pdfminer.six,plyer,pyjnius,android

# (str) Supported orientation (landscape, portrait or all)
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolkit)
android.presplash_color = #FFFFFF

# (list) Permissions
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,RECORD_AUDIO

# (str) The Android arch to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature
android.allow_backup = True

# (str) The format used to package the app for release mode
android.release_artifact = apk

# (str) The format used to package the app for debug mode  
android.debug_artifact = apk

# (str) Android SDK version to use
android.sdk = 33

# (str) Android NDK version to use
android.ndk = 25.1.8937393

#
# Python for android (p4a) specific
#

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (str) python-for-android fork to use
p4a.fork = kivy

# (str) python-for-android branch to use
p4a.branch = master

# (str) python-for-android specific commit to use
p4a.commit = HEAD

# (str) The directory in which python-for-android should look for your own build recipes
p4a.local_recipes =

# (str) Filename to the hook for p4a
p4a.hook =

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument
p4a.port =

# Control passing the --use-setup-py flag to p4a
p4a.use_setup_py = False

# Control passing the --private flag to p4a
p4a.private = False

# (str) Extra command line arguments to pass when invoking pythonforandroid.toolchain
p4a.extra_args =

# (str) python-for-android branch to use, or full git url
p4a.branch = master

# (str) python-for-android fork to use, or full git url
p4a.fork = kivy

# (str) python-for-android branch to use, or full git url
p4a.branch = master

# (str) python-for-android fork to use, or full git url
p4a.fork = kivy

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
