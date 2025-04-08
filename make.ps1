param (
    [string]$Target = "help"
)

$PYTHON = "py"
$PIP = ".\venv\Scripts\pip.exe"
$PY_VENV = ".\venv\Scripts\python.exe"


function Show-Help
{
    Write-Host "### Available targets:"
    Write-Host "### .\make.ps1 init - Create py virtual environment and install node modules"
    Write-Host "### .\make.ps1 venv - Create py virtual environment"
    Write-Host "### .\make.ps1 node_modules - Install node modules"
    Write-Host "### .\make.ps1 env - Load environment variables from doppler to .env file"
    Write-Host "### .\make.ps1 django - Start Django server"
    Write-Host "### .\make.ps1 web - Start Webpack"
    Write-Host "### .\make.ps1 celery - Start Celery worker"
    Write-Host "### .\make.ps1 build - Build static files"
    Write-Host "### .\make.ps1 migrations - Make and apply migrations"
    Write-Host "### .\make.ps1 index - Reindex Algolia"
    Write-Host "### .\make.ps1 clear-index - Clear Algolia index"
    Write-Host "### .\make.ps1 clean - Clean environment"
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
    else
    {
        Write-Host "### Node modules already installed"
    }
}

function Start-Django
{
    Create-Venv
    Write-Host "### Starting Django"
    & $PY_VENV manage.py runserver
}

function Start-Django-HTTPS
{
    Create-Venv
    Write-Host "### Starting Django with HTTPS"
    & $PY_VENV -m daphne -e ssl:8000:privateKey=./dev-certs/localhost.key:certKey=./dev-certs/localhost.crt --proxy-headers core.asgi:application
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

function Clean-Environment
{
    Write-Host "### Cleaning environment"
    Remove-Item -Path "node_modules" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "venv" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ".env" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "staticfiles/*" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "static/dist/*" -Force -ErrorAction SilentlyContinue
    Write-Host "### Done"
}

function Start-Build
{
    npm run build
    python manage.py collectstatic --no-input
}


switch ($Target)
{
    "help" {
        Show-Help
    }
    "init" {
        Create-Venv
        Install-NodeModules
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
    "django-https" {
        Load-Env
        Start-Django-HTTPS
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
    "clean" {
        Clean-Environment
    }
    "reset" {
        DeleteDB
    }
    "kill" {
        netstat -ano | findstr ":8000" | ForEach-Object { $_ -split "\s+" | Select-Object -Last 1 } | ForEach-Object { taskkill /PID $_ /F }
    }
    default {
        Write-Host "### Unknown target: $Target"
        Show-Help
    }
}
