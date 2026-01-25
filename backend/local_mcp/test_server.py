# maths server

from __future__ import annotations
from fastmcp import FastMCP

mcp = FastMCP("maths-local-server")

def _as_number(x):

      if isinstance(x, (int, float)):
            return float(x)
      if isinstance(x, str):
            return float(x.strip())
      raise TypeError("Expected a number (int/float or numeric string)")

@mcp.tool()
async def add(a: float, b: float) -> float:
       """ returns the sum of a and b """
       return _as_number(a) + _as_number(b)

@mcp.tool()
async def subtract(a: float, b: float) -> float:
       """ returns the difference of a and b """
       return _as_number(a) - _as_number(b)

@mcp.tool()
async def multiply(a: float, b: float) -> float:
       """ returns the multiplication of a and b """
       return _as_number(a) * _as_number(b)

@mcp.tool()
async def divide(a: float, b: float) -> float:
       """ returns the division of a by b """
       b = _as_number(b)
       if b == 0:
            raise ValueError("Division by zero is not allowed")
       return _as_number(a) / b

@mcp.tool()
async def modulus(a: float, b: float) -> float:
       """ returns the remainder when a is divided by b """
       b = _as_number(b)
       if b == 0:
            raise ValueError("Modulus by zero is not allowed")
       return _as_number(a) % b

@mcp.tool()
async def power(a: float, b: float) -> float:
       """ returns a raised to the power b """
       return _as_number(a) ** _as_number(b)

if __name__ == "__main__":
    mcp.run()
