@echo off
title IP Monitor
set firstrun=false

if exist ".venv\" (
    echo "Virtual Environment already created"
) else (
    echo "Creating Virtual Environment for Python..  You may need to press Enter if this is blank for too long."
    py -m venv .venv
    set firstrun=True
)

call ".venv\Scripts\Activate"

if "%firstrun%" == "True" (

    pip install -r requirements.txt

)

for /f "delims=" %%i in ('py -c "import yaml, sys;print(yaml.safe_load(open('config.yaml'))['AUTO_UPDATE'])"') do set AUTO_UPDATE=%%i

echo AUTO_UPDATE is %AUTO_UPDATE%

if /i "%AUTO_UPDATE%"=="True" (
    echo Running update.py...
    py update.py
)
py main.py

