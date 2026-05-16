FROM python:3.13-slim

# Force Python to print logs directly to the container terminal output without buffering
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the requirements file first to take advantage of Docker build caching
COPY requirements.txt .

# Install dependencies clean and quick
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your backend logic, SQLite configurations, and HTML templates into the container
COPY . .

# Expose the internal port your FastAPI app runs on
EXPOSE 8000

# Start Uvicorn and bind it to 0.0.0.0 so Bunny can route public internet traffic to it
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]