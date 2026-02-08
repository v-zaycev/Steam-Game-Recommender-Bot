import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

class PgsqlClient:
    def __init__(self, env : str = None):
        if env is not None:
            load_dotenv(env)
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', 5432))
        self.db_base = os.getenv('DB_NAME')
        self.db_user = os.getenv('DB_USER')
        self.db_pass = os.getenv('DB_PASSWORD')
        self.connection = None
 
    def get_connection(self):
        return psycopg2.connect(
            host = self.db_host,
            port = self.db_port,
            database = self.db_base,
            user = self.db_user,
            password = self.db_pass
        )

    def select(self, attributes: list[str], table: str, where : str = None) -> tuple:
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                query = f"SELECT {', '.join(attributes)} FROM {table}"
                if where is not None:
                    query += " WHERE " + where
                cursor.execute(query)
                result = (cursor.fetchall(), cursor.description)
                self.connection.commit()
                return result
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise
    
    def insert(self, attributes: list[str], table: str, data: list):
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                placeholders = ', '.join(['%s'] * len(data))
                query = f"INSERT INTO {table} ({', '.join(attributes)}) VALUES ({placeholders})"
                cursor.execute(query, data)
                self.connection.commit()
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise

    def update(self, attributes: list[str], table: str, data: list, id_column : str, id : int):
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                result = [f"{k} = '{v}'" for k, v in zip(attributes, data)]
                query = f"UPDATE {table} SET {', '.join(result)} WHERE {id_column} = {id}"
                cursor.execute(query)
                self.connection.commit()
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise

    def delete(self, attributes: list[str], table: str):
        try:
            if self.connection is None:
                self.connection = self.get_connection()
            with self.connection.cursor() as cursor:
                query = f"DELETE FROM {table} WHERE id IN ({', '.join(attributes)})"
                cursor.execute(query)
                self.connection.commit()
        except psycopg2.Error:
            try:
                self.connection.rollback()
            except psycopg2.Error:
                self.connection = None
                raise
            raise
