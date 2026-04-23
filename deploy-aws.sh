#!/bin/bash
# AWS Free Tier Deployment Script for Bharatiyam AI Chatbot
# Tested on Ubuntu 22.04 LTS / 24.04 LTS
# Run as: sudo bash deploy-aws.sh

set -e

echo "=== Bharatiyam AI Chatbot - AWS Free Tier Deployment ==="
echo ""

# Update system
echo "[1/8] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python and pip
echo "[2/8] Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv git

# Install MongoDB
echo "[3/8] Installing MongoDB..."
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update -y
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
echo "MongoDB installed and started"

# Install Tesseract OCR
echo "[4/8] Installing Tesseract OCR..."
sudo apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng
sudo apt-get install -y tesseract-ocr-ben tesseract-ocr-tam tesseract-ocr-tel
sudo apt-get install -y tesseract-ocr-mar tesseract-ocr-kan tesseract-ocr-mal
echo "Tesseract installed with Indic language support"

# Install Poppler (required for pdf2image)
echo "[5/8] Installing Poppler..."
sudo apt-get install -y poppler-utils
echo "Poppler installed"

# Install VS Code Server
echo "[6/8] Installing VS Code Server..."
curl -fsSL https://code-server.dev/install.sh | sh
# Start code-server on port 8080
sudo systemctl enable --now code-server@$USER
echo "VS Code Server installed. Access at http://<public-ip>:8080"

# Clone repository (replace with your repo URL)
echo "[7/8] Cloning repository..."
cd /home/ubuntu
if [ -d "bharatiyam-ai-chatbot" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd bharatiyam-ai-chatbot
    git pull
else
    git clone https://github.com/shreyyasss-27/bharatiyam-ai-chatbot.git
    cd bharatiyam-ai-chatbot
fi

# Create virtual environment and install dependencies
echo "[8/8] Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p data/texts
mkdir -p data/pdfs
mkdir -p data/faiss_index

# Create .env file from example
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your API keys and configuration."
    echo "Edit with: nano /home/ubuntu/bharatiyam-ai-chatbot/.env"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys: nano /home/ubuntu/bharatiyam-ai-chatbot/.env"
echo "2. Access VS Code Server: http://<public-ip>:8080"
echo "3. Start the application: cd /home/ubuntu/bharatiyam-ai-chatbot && source .venv/bin/activate && python -m app.api"
echo ""
echo "MongoDB status: sudo systemctl status mongod"
echo "VS Code Server status: sudo systemctl status code-server@$USER"
