# Use smaller base image
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY *.py ./

# Expose port
EXPOSE 8000

# Run the app using python module syntax (more reliable)
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
