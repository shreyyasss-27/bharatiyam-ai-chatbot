# AWS Free Tier Deployment Guide

This guide explains how to deploy the Bharatiyam AI Chatbot on AWS Free Tier.

## Prerequisites

- AWS Account with Free Tier eligibility
- Basic knowledge of AWS EC2

## Step 1: Launch EC2 Instance

1. Log in to AWS Console
2. Navigate to EC2 → Instances → Launch Instance
3. Configure:
   - **Name**: Bharatiyam-Chatbot
   - **AMI**: Ubuntu Server 22.04 LTS or 24.04 LTS
   - **Instance Type**: t2.micro or t3.micro (Free Tier eligible)
   - **Key Pair**: Create or use existing SSH key
   - **Network Settings**:
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) from 0.0.0.0/0
     - Allow HTTPS (port 443) from 0.0.0.0/0
     - Allow custom port 8000 from 0.0.0.0/0 (for API)
     - Allow custom port 8080 from 0.0.0.0/0 (for VS Code Server)
4. Launch instance

## Step 2: Connect to Instance

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<public-ip>
```

## Step 3: Run Deployment Script

Upload the deployment script:

```bash
# On your local machine
scp -i your-key.pem deploy-aws.sh ubuntu@<public-ip>:/home/ubuntu/
```

On the instance:

```bash
chmod +x deploy-aws.sh
sudo bash deploy-aws.sh
```

## Step 4: Configure Environment

Edit the .env file:

```bash
cd /home/ubuntu/bharatiyam-ai-chatbot
nano .env
```

Add your API keys:
```ini
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
TESSERACT_CMD=/usr/bin/tesseract
POPPLER_PATH=/usr/bin
MONGO_URI=mongodb://localhost:27017/
DB_NAME=document_qa
DATA_TEXT_DIR=/home/ubuntu/bharatiyam-ai-chatbot/data/texts
DATA_PDF_DIR=/home/ubuntu/bharatiyam-ai-chatbot/data/pdfs
FAISS_DIR=/home/ubuntu/bharatiyam-ai-chatbot/data/faiss_index
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
GROQ_MODEL=llama-3.3-70b-versatile
```

## Step 5: Install as Systemd Service

```bash
# Upload service file
scp -i your-key.pem bharatiyam.service ubuntu@<public-ip>:/home/ubuntu/

# On instance
sudo mv /home/ubuntu/bharatiyam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bharatiyam
sudo systemctl start bharatiyam
sudo systemctl status bharatiyam
```

## Step 6: Access Services

- **API**: http://<public-ip>:8000
- **API Documentation**: http://<public-ip>:8000/docs
- **VS Code Server**: http://<public-ip>:8080 (password in ~/.config/code-server/config.yaml)

## Step 7: Upload Documents

Use VS Code Server or SCP to upload PDFs:

```bash
# From local machine
scp -i your-key.pem -r your-pdfs/* ubuntu@<public-ip>:/home/ubuntu/bharatiyam-ai-chatbot/data/pdfs/
```

Process documents:

```bash
cd /home/ubuntu/bharatiyam-ai-chatbot
source .venv/bin/activate
python -c "from app.main import DocumentQA; qa = DocumentQA(config={'auto_process_documents': False}); qa.process_documents('data/pdfs'); print('Ingestion complete')"
```

## AWS Free Tier Limits

- **EC2**: 750 hours/month of t2.micro or t3.micro
- **Storage**: 30 GB EBS (gp2 or gp3)
- **Data Transfer**: 100 GB/month out to internet

## Monitoring

Check service status:
```bash
sudo systemctl status bharatiyam
sudo systemctl status mongod
```

View logs:
```bash
sudo journalctl -u bharatiyam -f
tail -f /home/ubuntu/bharatiyam-ai-chatbot/app.log
```

## Security Recommendations

1. Use security groups to restrict access
2. Set up AWS IAM roles for EC2
3. Use AWS Secrets Manager for API keys
4. Enable AWS CloudWatch for monitoring
5. Regularly update system packages: `sudo apt-get update && sudo apt-get upgrade`

## Troubleshooting

**MongoDB not starting:**
```bash
sudo systemctl status mongod
sudo journalctl -u mongod -xe
```

**API not accessible:**
- Check security group allows port 8000
- Check service status: `sudo systemctl status bharatiyam`

**Out of memory on t2.micro:**
- Add swap space:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
