@echo off
REM Script to deploy Kafka Connect sink connector for telescope data (Windows version)

setlocal

set CONNECT_URL=http://localhost:8083
set CONFIG_FILE=postgres-sink.json

echo Waiting for Kafka Connect to be ready...
:wait_loop
curl -f -s %CONNECT_URL%/ >nul 2>&1
if errorlevel 1 (
    echo Kafka Connect is unavailable - sleeping
    timeout /t 5 /nobreak >nul
    goto wait_loop
)

echo Kafka Connect is ready!

REM Extract connector name from JSON (requires jq or manual specification)
set CONNECTOR_NAME=postgres-telescope-data-sink

echo Checking if connector exists...
curl -f -s %CONNECT_URL%/connectors/%CONNECTOR_NAME% >nul 2>&1
if not errorlevel 1 (
    echo Connector '%CONNECTOR_NAME%' already exists. Updating...
    curl -X PUT -H "Content-Type: application/json" --data @%CONFIG_FILE% %CONNECT_URL%/connectors/%CONNECTOR_NAME%/config
) else (
    echo Creating connector '%CONNECTOR_NAME%'...
    curl -X POST -H "Content-Type: application/json" --data @%CONFIG_FILE% %CONNECT_URL%/connectors
)

echo.
echo Connector deployment complete!
echo Check status with: curl %CONNECT_URL%/connectors/%CONNECTOR_NAME%/status

endlocal
