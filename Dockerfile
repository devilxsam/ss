# Use an official Python runtime as a parent image
FROM python:3.8

# Set the working directory to /app
WORKDIR /app

# Copy the "bot.py" script, "config.json" file, and "requirements.txt" into the container
COPY bot.py config.json requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Create directories for video and screenshot storage
RUN mkdir videos screenshots

# Expose the port the app runs on (if needed)
# EXPOSE 80

# Run the application
CMD ["python", "bot.py"]
