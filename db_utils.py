import os
import sqlite3
import logging
import chromadb

# Configure logging
logger = logging.getLogger(__name__)

db_path = "./cache"
db_file = os.path.join(db_path, "db.sqlite3")
vector_db_file = os.path.join(db_path, "store.db")

# Create cache directory if it doesn't exist
os.makedirs(db_path, exist_ok=True)

def get_db_file():
    return db_file

def get_vector_db_file():
    return vector_db_file

def similarity_threshold():
    return 0.05

def set_up_db():
    """Initialize the SQLite database and create necessary tables."""
    try:
        # Create directory if it doesn't exist
        if not os.path.exists(db_path):
            os.makedirs(db_path, exist_ok=True)

        # Connect to SQLite database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Create cached_results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cached_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            metadata TEXT,
            result BLOB NOT NULL
        )
        ''')

        conn.commit()
        logger.info("Database setup completed successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error during setup: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database setup: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def store_result(id: int, query: str, result):
    """Store a result in the cache database."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cached_results (id, query, result) 
            VALUES (?, ?, ?)
            ''', (id, query, result))
        conn.commit()
        logger.info(f"Stored result with id {id}")
    except sqlite3.Error as e:
        logger.error(f"Database error storing result: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_result_by_id(id: str):
    """Retrieve a result from the cache by ID."""
    try:
        numeric_id = int(id[2:])
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT result FROM cached_results WHERE id=?', (numeric_id,))
        record = cursor.fetchone()
        return record[0] if record else None
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving result: {e}")
        return None
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_next_id() -> int:
    """Get the next available ID for cached results."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Ensure the table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cached_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            metadata TEXT,
            result BLOB NOT NULL
        )
        ''')
        conn.commit()

        # Get the largest id
        cursor.execute('SELECT MAX(id) FROM cached_results')
        record = cursor.fetchone()
        return (record[0] or 0) + 1
    except sqlite3.Error as e:
        logger.error(f"Database error getting next ID: {e}")
        return 1
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_cached_results():
    """Fetch all cached results from the database."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT id, query, metadata, result FROM cached_results ORDER BY id DESC')
        results = cursor.fetchall()
        return [{'id': r[0], 'query': r[1], 'metadata': r[2], 'result': r[3]} for r in results]
    except sqlite3.Error as e:
        logger.error(f"Database error fetching cached results: {e}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_cache_files():
    """Get list of all files in cache directory."""
    if not os.path.exists(db_path):
        return []
    return [f for f in os.listdir(db_path)]

def query_vector_cache(query:str):
    chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
    # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
    collection = chroma_client.get_or_create_collection(name="cached_docs")
    logger.debug(f"Querying cache with: {query}")
    cached_result = collection.query(
      query_texts=[query],
      n_results=5
    )
    # Format the results into a more usable structure
    results = {
        'ids': cached_result['ids'][0] if cached_result['ids'] else [],
        'distances': cached_result['distances'][0] if cached_result['distances'] else [],
        'metadatas': cached_result['metadatas'][0] if cached_result['metadatas'] else [],
        'documents': cached_result['documents'][0] if cached_result['documents'] else []
    }
    return results