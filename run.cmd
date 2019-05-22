@echo off
set PYTHONPATH=%PYTHONPATH%;.\
call venv\Scripts\activate.bat
python scripts\run_enso.py --no-console --log-level=ERROR
call deactivate.bat
pause
