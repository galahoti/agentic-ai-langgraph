import sqlite3
import os
import json
from fastmcp import FastMCP
from contextlib import contextmanager

mcp = FastMCP(name="Expense Tracker")

# Store the database at the repository root (one level above this file's directory)
DB_FILE = os.path.join(os.path.dirname(__file__), 'expense.db')
CATEGORIES_FILE = os.path.join(os.path.dirname(__file__), 'categories.json')

print(f"[ExpenseTracker] Using expense database at: {os.path.abspath(DB_FILE)}")
print(f"[ExpenseTracker] Categories file at: {os.path.abspath(CATEGORIES_FILE)}")

@contextmanager
def get_db_connection():
    """Context manager for a database connection."""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

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
        conn.commit()

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
        conn.commit()
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
    mcp.run()