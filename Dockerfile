docker build -t discord-bot .
docker run --env-file .env -p 443:443 discord-bot

# Use an official Python runtime as a parent image
FROM Python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run bot.py when the container launches
CMD ["python", "bot.py"]
