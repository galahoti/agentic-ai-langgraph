import sqlite3
import os
import json
from fastmcp import FastMCP
from contextlib import contextmanager
import tempfile

mcp = FastMCP(name="Expense Tracker")

# Use environment variable for data directory, fallback to temp directory for container environments
DATA_DIR = os.environ.get('MCP_DATA_DIR')
if not DATA_DIR:
    # Check if we're in a container environment (typical readonly filesystem)
    script_dir = os.path.dirname(__file__)
    if os.path.exists(script_dir) and os.access(script_dir, os.W_OK):
        DATA_DIR = script_dir
    else:
        # Use /tmp for container environments or fallback to system temp
        DATA_DIR = '/tmp' if os.path.exists('/tmp') else tempfile.gettempdir()

# Ensure the data directory exists and is writable
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, 'expense.db')
CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), 'categories.json')

print(f"[ExpenseTracker] Using expense database at: {os.path.abspath(DB_FILE)}")
print(f"[ExpenseTracker] Categories file at: {os.path.abspath(CATEGORIES_FILE)}")

@contextmanager
def get_db_connection():
    """Context manager for a database connection."""
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10.0)
        # Use DELETE mode instead of WAL for better compatibility in container environments
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()  # Commit changes before closing
        except Exception:
            conn.rollback()  # Rollback on error
            raise
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        print(f"[ExpenseTracker] Database error: {e}")
        print(f"[ExpenseTracker] DB path: {DB_FILE}")
        print(f"[ExpenseTracker] Directory writable: {os.access(os.path.dirname(DB_FILE), os.W_OK)}")
        raise

def init_db():
    """Initializes the database and creates the expenses table if it doesn't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                subcategory TEXT,
                amount REAL NOT NULL,
                notes TEXT,
                date TEXT NOT NULL
            )
        ''')
        # conn.commit() is now handled by the context manager

# MCP tool: Add expense
@mcp.tool
def add_expense(category: str, amount: float, notes: str, date: str, subcategory: str = None) -> dict:
    """Adds a new expense to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (category, subcategory, amount, notes, date) VALUES (?, ?, ?, ?, ?)",
            (category, subcategory, amount, notes, date)
        )
        # conn.commit() is now handled by the context manager
    return {"status": "success", "message": "Expense added."}

# MCP tool: List expenses
@mcp.tool
def list_expenses() -> list:
    """Retrieves all expenses from the database."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row  # Process rows as dictionary-like objects
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, subcategory, amount, notes, date FROM expenses")
        rows = cursor.fetchall()
        expenses = [dict(row) for row in rows]
    return expenses

# MCP resource: Expense categories
@mcp.resource("expense://categories")
def get_categories() -> str:
    """Returns the list of available expense categories from the JSON file."""
    try:
        with open(CATEGORIES_FILE, 'r') as f:
            categories_data = json.load(f)
            return json.dumps(categories_data, indent=2)
    except FileNotFoundError:
        return json.dumps({"error": "Categories file not found"}, indent=2)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON in categories file"}, indent=2)

init_db()  # Initialize the database

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)