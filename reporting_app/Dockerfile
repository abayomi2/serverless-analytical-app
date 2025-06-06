# Use the same base image for consistency
FROM python:3.10-slim

WORKDIR /app

COPY reporting_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reporting_app/ .

# Run on a different port internally if desired, e.g. 8080, but can also be 8000
EXPOSE 8080

# Note the CMD points to this app's app.py file
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]