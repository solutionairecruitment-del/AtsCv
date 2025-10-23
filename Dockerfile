#Using Python 3.11 slim image for smaller size
FROM python:3.11-slim

#Setting working directory
WORKDIR /app

#Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

#System dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

#Copy requirements
COPY requirements.txt .

#Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

#Install production WSGI server
RUN pip install --no-cache-dir gunicorn

#Copy application code
COPY . .

#Create directory for SQLite database
RUN mkdir -p instance

#Expose the port (default 5008 - can be overwritten)
EXPOSE 5008

#Run with gunicorn
CMD gunicorn --bind 0.0.0.0:${PORT:-5008} --workers 4 --threads 2 --timeout 120 app:app
