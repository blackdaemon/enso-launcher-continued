@echo off
set PYTHONPATH=%PYTHONPATH%;.\
call venv\Scripts\activate.bat
python scripts\run_enso.py %1 %2 %3 %4 %5 %6 %7 %8 %9
call deactivate.bat
pause
