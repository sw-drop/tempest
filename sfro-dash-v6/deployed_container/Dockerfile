FROM python:3.11-slim

# Install minimal compiler dependencies for numpy/astropy if binary wheels aren't used
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set execution rights
RUN chmod +x dash-scripts/daemon.py

CMD ["python", "dash-scripts/daemon.py"]
