FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY console/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY console/backend/app/ ./app/
COPY console/backend/tests/ ./tests/

# Create directory for uploaded files
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
