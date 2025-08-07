"""
pip install psycopg2
or
pip install psycopg2-binary

https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-identity
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-azure-ad-authentication
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-configure-sign-in-azure-ad-authentication

TODO: Store credentials in Azure Key Vault

"""
import os
import sys
import time
import json
import psycopg2
from psycopg2 import sql

# Add the parent directory to the system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.logger import get_logger

logger = get_logger("Postgres")

# -------------------------------------------------------------------------------------------------
#
class PostgresClient:
    # ---------------------------------------------------------------------------------------------
    #
    def __init__(self):
        self.connection = None

    # ---------------------------------------------------------------------------------------------
    #
    def connect(self, info:dict) -> bool:
        try:
            self.connection = psycopg2.connect(
                host=info["host"],
                database=info["database"],
                user=info["user"],
                password=info["password"],
                port=int(info["port"]),
                sslmode=info["sslmode"]
            )

            return True

        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL database: {e}")
            raise

    # ---------------------------------------------------------------------------------------------
    #
    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")

    # ---------------------------------------------------------------------------------------------
    #
    def check_and_create_schema(self, schema_name) -> bool:
        if not self.connection:
            raise Exception("Connection not established. Call connect() first.")

        check_schema_query = sql.SQL("SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s")
        create_schema_query = sql.SQL("CREATE SCHEMA {schema_name}").format(schema_name=sql.Identifier(schema_name))

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(check_schema_query, (schema_name,))
                if not cursor.fetchone():
                    cursor.execute(create_schema_query)
                    self.connection.commit()
                    print(f"Schema '{schema_name}' created")
                else:
                    print(f"Schema '{schema_name}' already exists")

                return True

        except Exception as e:
            self.connection.rollback()
            print(f"Error checking/creating schema '{schema_name}': {e}")
            raise

    # ---------------------------------------------------------------------------------------------
    #
    def check_and_create_table(self, schema_name, table_name, table_definition) -> bool:
        if not self.connection:
            raise Exception("Connection not established. Call connect() first.")

        check_table_query = sql.SQL(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_name = %s"
        )
        create_table_query = sql.SQL("CREATE TABLE {schema_name}.{table_name} ({table_definition})").format(
            schema_name=sql.Identifier(schema_name),
            table_name=sql.Identifier(table_name),
            table_definition=sql.SQL(table_definition)
        )

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(check_table_query, (schema_name, table_name))
                if not cursor.fetchone():
                    cursor.execute(create_table_query)
                    self.connection.commit()
                    print(f"Table '{schema_name}.{table_name}' created")
                else:
                    print(f"Table '{schema_name}.{table_name}' already exists")

                return True

        except Exception as e:
            self.connection.rollback()
            print(f"Error checking/creating table '{schema_name}.{table_name}': {e}")
            raise

    # ---------------------------------------------------------------------------------------------
    #
    def insert_data(self, table, device, timestamp, data, on_conflict = "") -> bool:
        if not self.connection:
            raise Exception("Connection not established. Call connect() first.")

        query = f'INSERT INTO {table} ("device", "timestamp", "data") VALUES (%s, TO_TIMESTAMP(%s), %s) {on_conflict}'
        # logger.info(query)
        insert_query = sql.SQL(query)

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_query, (device, timestamp, data))
                self.connection.commit()
                logger.debug(f"Row inserted into {table} table")
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error inserting row into {table} table: {e}")
            raise

    # ---------------------------------------------------------------------------------------------
    #
    def insert_data_with_uuid(self, table, device, uuid, timestamp, data, on_conflict = 'ON CONFLICT ("uuid") DO NOTHING') -> bool:
        if not self.connection:
            raise Exception("Connection not established. Call connect() first.")

        query = f'INSERT INTO {table} ("device", "uuid", "timestamp", "data") VALUES (%s, %s, TO_TIMESTAMP(%s), %s) {on_conflict}'
        # logger.info(query)
        insert_query = sql.SQL(query)

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_query, (device, uuid, timestamp, data))
                self.connection.commit()
                logger.debug(f"Row inserted into {table} table")
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error inserting row into {table} table: {e}")
            raise

    # ---------------------------------------------------------------------------------------------
    #
    def read_config(self, table, key):
        if not self.connection:
            raise Exception("Connection not established. Call connect() first.")

        query = sql.SQL(f"SELECT * FROM {table} WHERE key = %s")
        logger.debug(query)

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (key,))
                result = cursor.fetchone()

                if result:
                    logger.info(f"Record found: {result}")
                else:
                    logger.info(f"No record found for key: {key}")

                return result

        except Exception as e:
            logger.error(f"Error reading record from config table: {e}")
            raise

    # ---------------------------------------------------------------------------------------------
    #
    def upsert_config(self, table, key, data):
        if not self.connection:
            raise Exception("Connection not established. Call connect() first.")

        query = f'''
        INSERT INTO {table} (key, data)
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data
        '''
        upsert_query = sql.SQL(query)

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(upsert_query, (key, data))
                self.connection.commit()
                logger.info(f"Record upserted into config table with key: {key}")
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error upserting record into config table: {e}")
            raise

# ---------------------------------------------------------------------------------------------
#
def run_test():
    # Load database configuration from environment variables or use default values
    db_config = {
        "host": os.getenv("AZURE_POSTGRESQL_HOST", "psql-ret-dev-21b6d3.postgres.database.azure.com"),
        "database": os.getenv("AZURE_POSTGRESQL_DATABASE", "ret001_sandbox"),
        "user": os.getenv("AZURE_POSTGRESQL_USERNAME", "tiazuret918d001"),
        "password": os.getenv("AZURE_POSTGRESQL_PASSWORD", "Jd?KeNaAdFZ5tUXP2vr.Ajg!x!bJfK"),
        "port": int(os.getenv("AZURE_POSTGRESQL_PORT", 5432)),
        "sslmode": os.getenv("AZURE_POSTGRESQL_SSLMODE", "require")
    }

    table_definition = """
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE,
    device VARCHAR,
    data json
    """

    now = int(time.time())
    drift = {"Drift status": 0, "timestamp": now}
    device = "BATLAB-TEST"

    # Example data to insert
    data_to_insert = {
        "data": json.dumps(drift)
    }

    # Initialize Postgres
    db_handler = PostgresClient()

    try:
        db_handler.connect(db_config)
        # db_handler.check_and_create_schema("rci_capteurs")
        db_handler.check_and_create_table("rci_capteurs", "rci_test", table_definition)
        db_handler.insert_data("rci_capteurs.rci_test", device, now, json.dumps(drift))
    finally:
        db_handler.close()

# -------------------------------------------------------------------------------------------------
#
if __name__ == "__main__":
    run_test()