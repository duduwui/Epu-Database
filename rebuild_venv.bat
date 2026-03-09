@echo off
echo === Rebuilding MIS virtual environment ===
cd /d "C:\Users\DATA FORCE\OneDrive\Pictures\Screenshots\Desktop\MIS"

echo Step 1: Removing old broken venv...
rmdir /s /q .venv

echo Step 2: Creating new venv with system Python...
python -m venv .venv

echo Step 3: Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt

echo Step 4: Testing...
set PATH=C:\Program Files\PostgreSQL\17\bin;%PATH%
.venv\Scripts\python.exe -c "import flask, psycopg; print('All OK - ready to run!')"

echo.
echo === Done! Run the server with: ===
echo .venv\Scripts\python.exe app.py
pause
