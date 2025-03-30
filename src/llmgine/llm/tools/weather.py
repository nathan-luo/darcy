"""Weather tool for LLM function calling."""

import http.client
import json
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Mapping of major Australian cities to their observation station IDs
WEATHER_STATIONS = {
    "melbourne": {"id": "IDV60901/IDV60901.94870", "name": "Melbourne (Moorabbin Airport)"},
    "sydney": {"id": "IDN60901/IDN60901.94768", "name": "Sydney (Observatory Hill)"},
    "brisbane": {"id": "IDQ60901/IDQ60901.94576", "name": "Brisbane"},
    "perth": {"id": "IDW60901/IDW60901.94608", "name": "Perth"},
    "adelaide": {"id": "IDS60901/IDS60901.94675", "name": "Adelaide (West Terrace)"},
    "hobart": {"id": "IDT60901/IDT60901.94970", "name": "Hobart (Ellerslie Road)"},
    "darwin": {"id": "IDD60901/IDD60901.94120", "name": "Darwin"},
    "canberra": {"id": "IDN60903/IDN60903.95926", "name": "Canberra Airport"}
}

def get_station_list() -> List[Dict[str, str]]:
    """Get list of available weather stations.
    
    Returns:
        List of dictionaries containing station information
    """
    return [
        {"city": city, "name": info["name"]}
        for city, info in WEATHER_STATIONS.items()
    ]

def get_weather(city: str) -> Dict[str, Any]:
    """Get current weather information for a specified Australian city.
    
    Args:
        city: Name of the city (e.g., 'melbourne', 'sydney', etc.)
        
    Returns:
        Dictionary containing weather information
    """
    city = city.lower()
    if city not in WEATHER_STATIONS:
        return {
            "error": f"City not found. Available cities: {', '.join(WEATHER_STATIONS.keys())}"
        }
    
    station = WEATHER_STATIONS[city]
    conn = http.client.HTTPConnection("www.bom.gov.au")
    
    try:
        # Get observation station data
        path = f"/fwo/{station['id']}.json"
        logger.debug(f"Requesting weather data from: {path}")
        
        conn.request("GET", path)
        res = conn.getresponse()
        
        # Check response status
        if res.status != 200:
            error_msg = f"HTTP Error {res.status}: {res.reason}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Read and parse data
        raw_data = res.read().decode('utf-8')
        logger.debug(f"Received raw data: {raw_data[:200]}...")
        
        data = json.loads(raw_data)
        
        if 'observations' not in data or 'data' not in data['observations'] or not data['observations']['data']:
            error_msg = "Invalid data format received from weather service"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Parse latest observation data
        latest_data = data['observations']['data'][0]
        
        # Format time
        local_time = datetime.strptime(latest_data['local_date_time_full'], '%Y%m%d%H%M%S')
        formatted_time = local_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Compile results
        result = {
            "location": station["name"],
            "city": city,
            "temperature": latest_data['air_temp'],
            "humidity": latest_data['rel_hum'],
            "wind_speed": latest_data['wind_spd_kmh'],
            "wind_direction": latest_data['wind_dir'],
            "pressure": latest_data['press'],
            "rain_since_9am": latest_data['rain_trace'],
            "observation_time": formatted_time
        }
        
        logger.debug(f"Successfully processed weather data for {city}")
        return result
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse weather data: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error getting weather data: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    finally:
        conn.close()

# Tool definition for OpenAI function calling
TOOL_DEFINITION = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather information for major Australian cities from the Bureau of Meteorology",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the Australian city (e.g., melbourne, sydney, brisbane, perth, adelaide, hobart, darwin, canberra)",
                    "enum": list(WEATHER_STATIONS.keys())
                }
            },
            "required": ["city"],
            "additionalProperties": False
        }
    }
}] 