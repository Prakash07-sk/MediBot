FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy the entire Backend application
COPY . .

# Expose the port (will be overridden by env var)
EXPOSE 8000

# Run the application using python main.py (reads from config.py which uses env vars)
CMD ["python", "main.py"]
