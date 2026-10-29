"""Small MySQL connection factory shared by the microservices."""
import os
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "brewlux"),
        user=os.getenv("DB_USER", "brewlux_app"),
        password=os.getenv("DB_PASSWORD", ""),
        connection_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        autocommit=False,
    )
