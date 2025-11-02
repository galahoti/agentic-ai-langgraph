import random
from fastmcp import FastMCP

mcp = FastMCP(name="Math Server")


@mcp.tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return the result"""
    return a + b


@mcp.tool
def generate_random_number(min_value: int = 0, max_value: int = 100) -> int:
    """Generate a random integer between min_value and max_value (inclusive)"""
    return random.randint(min_value, max_value)


@mcp.resource("math://server-info")
def get_server_info() -> str:
    """Returns information about the Math Server and its capabilities"""
    info = {
        "name": "Math Server",
        "version": "1.0.0",
        "description": "A simple MCP server for basic math operations and random number generation",
        "tools": [
            {
                "name": "add_numbers",
                "description": "Adds two numbers together",
                "parameters": ["a: float", "b: float"],
                "returns": "float"
            },
            {
                "name": "generate_random_number",
                "description": "Generates a random integer within a specified range",
                "parameters": ["min_value: int (default: 0)", "max_value: int (default: 100)"],
                "returns": "int"
            }
        ],
        "resources": [
            {
                "uri": "math://server-info",
                "description": "Server information and capabilities"
            }
        ]
    }
    
    import json
    return json.dumps(info, indent=2)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
