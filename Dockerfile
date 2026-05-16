FROM python:3.13-slim

WORKDIR /app

# Copy requirements list first to optimize image build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app code (main.py, database.py, templates, static)
COPY . .

EXPOSE 8000

# Tell Bunny to run your Uvicorn server on container startup
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]