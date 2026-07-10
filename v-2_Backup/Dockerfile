FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Setup application directories
WORKDIR /app
RUN mkdir -p /var/log/supervisor /var/run/supervisor /app/extra_scripts

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Supervisor and Nginx configurations
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY nginx.conf /etc/nginx/sites-available/tempest.conf
RUN ln -sf /etc/nginx/sites-available/tempest.conf /etc/nginx/sites-enabled/default

# Copy static frontend files to Nginx root
COPY web/ /var/www/html/

# Copy Python application files
COPY app/ /app/app/
COPY app/main.py /app/main.py
COPY report_*.py /app/

# Expose port 80 for Nginx (the dashboard and proxied API)
EXPOSE 80

# Run Supervisor in the foreground to manage all processes
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
