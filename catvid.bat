@ECHO OFF
if exist %~dp0\venv\Scripts\python.exe (
    %~dp0\venv\Scripts\python.exe %~dp0\catvid.py %*
) else (
    python %~dp0\catvid.py %*
)
