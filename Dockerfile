# Start with an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY application/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && \ 
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY application/ .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]