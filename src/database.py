import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="Rayan",
        password="12345",
        database="household"
    )
