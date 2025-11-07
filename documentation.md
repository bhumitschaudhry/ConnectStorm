# Documentation

### app.py:

This is the main flask application and is basically the web server and the consumer in a single process (Render doesn't allow background workers on the free plan). It handles file uploads, processes them in Redis and stores the metadata in TimescaleDB.

### consumer.py:

This is the legacy consumer. It does the same job as the one integrated in app.py. This is for when we want the consumer to run independently from the web server.

### storage.py:

This is a file storage handler that supports both S3 storage and local storage. Provides a unified interface for uploading files and generating accessible URLs. Automatically detects storage mode from environment variables and handles file operations accordingly.

### status.py:

This basically shows the health and statistics of both the Redis as well as the TimescaleDB databases. It shows connection status, queue lengths, pending messages, total number of records, data sizes, and recent activity.

### reset.py:

This is a script that clears all data from Redis streams and TimescaleDB tables. It asks for confirmation before deleting to prevent any accidental data loss.

### selenium_producer.py:

This is the automation script that simulates multiple users uploading files through the web interface using Selenium. Useful for stress testing the setup we have built and validating the performance under load.

### schema.sql:

This is the database schema definition for TimescaleDB that creates the file_events hypertable and necessary indexes.

### dashboard.html:

This is a real-time dashboard interface that displays file upload statistics, system metrics, and recent activity.

### upload.html:

This is the file upload page with drag-and-drop functionality and progress indicators. It provides a user-friendly interface for selecting and uploading files to the system.
