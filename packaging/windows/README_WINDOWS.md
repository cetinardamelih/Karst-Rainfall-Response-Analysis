# Windows Packaging

This folder builds a normal Windows installer for Karst Rainfall-Response Analysis.

End users only need:

```text
dist\installer\setup.exe
```

They do not need Python, pip, Streamlit, or terminal commands.

## Developer Prerequisites

Install these on the Windows build machine:

1. Python 3.11, 3.12, or 3.13
2. Inno Setup 6

Inno Setup must either be on `PATH` as `iscc` or installed in one of the default locations:

```text
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
C:\Program Files\Inno Setup 6\ISCC.exe
```

## One Command Build

From the project root:

```bat
packaging\windows\build_windows.bat
```

The script automatically:

- creates `.venv` if needed
- installs `requirements.txt`
- cleans old `build` and `dist` outputs
- builds the PyInstaller onedir executable
- compiles the Inno Setup installer

Expected outputs:

```text
dist\Karst Rainfall-Response Analysis\Karst Rainfall-Response Analysis.exe
dist\installer\setup.exe
```

For PyInstaller-only diagnostics without compiling the installer:

```bat
set SKIP_INNO=1
packaging\windows\build_windows.bat
```

## Runtime Behavior

When the user opens the installed shortcut or EXE:

1. The launcher creates user-writable folders.
2. It finds a free localhost port.
3. It starts Streamlit as a hidden background process.
4. It waits until the app is ready.
5. It opens the default browser automatically.
6. If startup fails, it shows a Windows error dialog with the log path.

Logs are written to:

```text
%APPDATA%\Karst Rainfall-Response Analysis\logs\app.log
```

User output folders are created at:

```text
%USERPROFILE%\Documents\Karst Rainfall-Response Analysis\outputs
```

## Installer Behavior

The installer is per-user and does not require administrator rights. It installs to:

```text
%LOCALAPPDATA%\Programs\Karst Rainfall-Response Analysis
```

It creates:

- Start Menu shortcut
- Desktop shortcut
- `%APPDATA%\Karst Rainfall-Response Analysis\logs`
- `%USERPROFILE%\Documents\Karst Rainfall-Response Analysis\outputs`

## End User Instructions

1. Double-click `setup.exe`.
2. Finish the installer.
3. Open the app from the Desktop shortcut, Start Menu shortcut, or installed EXE.
4. The browser opens automatically when the app is ready.

## Troubleshooting

If the app does not open, check:

```text
%APPDATA%\Karst Rainfall-Response Analysis\logs\app.log
```

If the build fails before `setup.exe` is created, confirm Inno Setup 6 is installed and rerun:

```bat
packaging\windows\build_windows.bat
```
