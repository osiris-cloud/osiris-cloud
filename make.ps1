param (
    [Parameter(Position = 0, Mandatory = $true)]
    [string]$Target
)

$PYTHON = "python"
$PIP = ".\venv\Scripts\pip.exe"
$PY_VENV = ".\venv\Scripts\python.exe"


function Show-Help
{
    Write-Host "### Available targets:"
    Get-Content Makefile | Select-String -Pattern "^.PHONY:" | ForEach-Object { $_.Line -replace ".PHONY: ", ".\make.ps1 " }
}

function Create-Venv
{
    if (-not (Test-Path venv))
    {
        Write-Host "### Creating virtual environment"
        & $PYTHON -m venv venv
        & $PY_VENV -m pip install --upgrade pip
        & $PIP install -r requirements.txt
    }
}

function Install-NodeModules
{
    if (-not (Test-Path node_modules))
    {
        npm install
    }
}

function Start-Django
{
    Create-Venv
    Write-Host "### Starting Django"
    & $PY_VENV manage.py runserver
}

function Start-Web
{
    Install-NodeModules
    Write-Host "### Starting Webpack"
    & npm run dev
}

function Start-Celery
{
    if (Test-Path .env)
    {
        Write-Host "### Starting Celery"
        & $PY_VENV -m celery -A core worker --loglevel INFO
    }
    else
    {
        Write-Host "[Celery] env file missing"
    }
}

function Start-Migrations
{
    Write-Host "### Making migrations"
    & $PY_VENV manage.py makemigrations
    & $PY_VENV manage.py migrate
}

function Algolia-Reindex
{
    Write-Host "### Reindexing Algolia"
    & $PY_VENV manage.py algolia_reindex
}

function Algolia-ClearIndex
{
    Write-Host "### Clearing Algolia index"
    & $PY_VENV manage.py algolia_clear_index
}


function Parse-EnvFile
{
    param (
        [string]$FilePath
    )
    $envVars = @{ }

    if (Test-Path $FilePath)
    {
        Get-Content $FilePath | ForEach-Object {
            $line = $_.Trim()
            if ($line -and !$line.StartsWith("#"))
            {
                $keyValue = $line -split "=", 2
                if ($keyValue.Length -eq 2)
                {
                    $key = $keyValue[0].Trim()
                    $value = $keyValue[1].Trim()
                    $value = $value -replace '^["'']|["'']$'
                    $envVars[$key] = $value
                }
            }
        }
    }
    else
    {
        Write-Error "Environment file not found: $FilePath"
    }

    return $envVars
}


function Set-EnvVariables
{
    param (
        [hashtable]$EnvVars
    )
    foreach ($key in $EnvVars.Keys)
    {
        $value = $EnvVars[$key]
        [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
    }
}

function Load-Env
{
    doppler secrets download --no-file --format env | Out-File -FilePath .env -Encoding utf8
    $envVariables = Parse-EnvFile -FilePath ".env"
    if ($envVariables.Count -gt 0)
    {
        Set-EnvVariables -EnvVars $envVariables
    }
}


function DeleteDB
{
    if (Test-Path -Path "db.sqlite3")
    {
        Remove-Item -Path "db.sqlite3" -Force
    }
    Copy-Item -Path "db-orig.sqlite3" -Destination "db.sqlite3"
}


switch ($Target)
{
    "help" {
        Show-Help
    }
    "venv" {
        Create-Venv
    }
    "node_modules" {
        Install-NodeModules
    }
    "env" {
        Load-Env
    }
    "django" {
        Load-Env
        Start-Django
    }
    "web" {
        Start-Web
    }
    "celery" {
        Load-Env
        Start-Celery
    }
    "build" {
        Start-Build
    }
    "migrations" {
        Start-Migrations
    }
    "index" {
        Load-Env
        Algolia-Reindex
    }
    "clear-index" {
        Load-Env
        Algolia-ClearIndex
    }
    "app" {
        if ($args.Count -eq 0)
        {
            Write-Host "Please provide an app name."
        }
        else
        {
            Create-App $args[0] #TODO
        }
    }
    "clean" {
        Clean-Environment #TODO
    }
    "delete" {
        DeleteDB
    }
    "kill" {
        netstat -ano | findstr ":8000" | ForEach-Object { $_ -split "\s+" | Select-Object -Last 1 } | ForEach-Object { taskkill /PID $_ /F }
    }
    default {
        Show-Help
    }
}
