# Windows batch file commands for development
# Alternative to Makefile for Windows users

@echo off

if "%1"=="" goto help
if "%1"=="install" goto install
if "%1"=="install-dev" goto install-dev
if "%1"=="run" goto run
if "%1"=="test" goto test
if "%1"=="clean" goto clean
goto help

:help
echo Available commands:
echo   dev.bat install      - Install production dependencies
echo   dev.bat install-dev  - Install development dependencies
echo   dev.bat run          - Run the application
echo   dev.bat test         - Run tests
echo   dev.bat clean        - Clean up generated files
goto end

:install
pip install -e .
goto end

:install-dev
pip install -e .[dev]
goto end

:run
python main.py
goto end

:test
pytest tests/
goto end

:clean
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f"
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist .pytest_cache rd /s /q .pytest_cache
goto end

:end
