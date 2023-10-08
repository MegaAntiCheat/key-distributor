# Base image
FROM python:3.11-alpine3.18

# Listen on 4434/tcp (HTTP)
EXPOSE 4434/tcp
### We need a web server to terminate TLS/SSL on 443
### and forward it to the app

# Install dependencies
COPY requirements.txt /dev/shm/requirements.txt
RUN pip install -r /dev/shm/requirements.txt

# Copy the app
COPY src /app
WORKDIR /app

# Run the app
CMD ["python", "app.py"]