Write-Host "Creating virtual environment..."
py -3.12 -m venv .venv

Write-Host "Activating virtual environment..."
.\.venv\Scripts\activate

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies..."
pip install -r requirements.txt
playwright install chromium

Write-Host "Running database migrations..."
flask --app frontend-flask/app.py db upgrade

Write-Host "Setup complete!"