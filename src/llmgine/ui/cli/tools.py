"""Sample tools for the LLMgine chatbot."""

import datetime
import logging
import math
import random
from typing import Any, Dict

logger = logging.getLogger(__name__)


def calculator(expression: str) -> float:
    """Calculate the result of a mathematical expression.
    
    Args:
        expression: The mathematical expression to evaluate
        
    Returns:
        The result of the calculation
        
    Raises:
        ValueError: If the expression is invalid
    """
    # Simple sanitization to prevent code execution
    allowed_chars = "0123456789+-*/().^ "
    if any(c not in allowed_chars for c in expression):
        raise ValueError(f"Invalid characters in expression: {expression}")

    # Replace ^ with ** for exponentiation
    expression = expression.replace("^", "**")

    try:
        # Add math functions to the namespace
        namespace = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "pi": math.pi,
            "e": math.e,
            "abs": abs,
            "round": round
        }

        # Evaluate the expression
        result = eval(expression, {"__builtins__": {}}, namespace)
        return result
    except Exception as e:
        logger.exception(f"Error evaluating expression {expression}: {e}")
        raise ValueError(f"Error evaluating expression: {e!s}")


def get_current_time() -> str:
    """Get the current date and time.
    
    Returns:
        The current date and time as a formatted string
    """
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_weather(location: str) -> Dict[str, Any]:
    """Get the current weather for a location (mock implementation).
    
    Args:
        location: The location to get weather for
        
    Returns:
        A dictionary with weather information
    """
    # Mock weather data
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorm", "Snowy"]

    # Use a seed based on the location name to ensure consistent results
    random.seed(hash(location))

    weather = {
        "location": location,
        "temperature": round(random.uniform(0, 35), 1),
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 90),
        "wind_speed": round(random.uniform(0, 30), 1),
        "timestamp": get_current_time()
    }

    return weather
