"""Integration tests for weather API functionality."""

import pytest
from typing import Dict, Any
from llmgine.llm.tools.weather import get_weather, get_station_list, WEATHER_STATIONS

def validate_weather_data(data: Dict[str, Any], expected_city: str) -> None:
    """Validate the structure and content of weather data.
    
    Args:
        data: Weather data to validate
        expected_city: Expected city name
    """
    # Check all required fields
    required_fields = {
        "location", "city", "temperature", "humidity", "wind_speed",
        "wind_direction", "pressure", "rain_since_9am", "observation_time"
    }
    assert all(field in data for field in required_fields), f"Missing required fields in data: {data}"
    
    # Validate city info
    assert data["city"] == expected_city.lower(), f"Wrong city returned: {data['city']}"
    assert data["location"] == WEATHER_STATIONS[expected_city.lower()]["name"], \
        f"Wrong location name: {data['location']}"
    
    # Validate data types
    assert isinstance(data["temperature"], (int, float)), "Temperature should be numeric"
    assert isinstance(data["humidity"], (int, float)), "Humidity should be numeric"
    assert isinstance(data["wind_speed"], (int, float)), "Wind speed should be numeric"
    assert isinstance(data["pressure"], (int, float)), "Pressure should be numeric"
    
    # Validate value ranges
    assert -50 <= data["temperature"] <= 50, f"Temperature out of range: {data['temperature']}"
    assert 0 <= data["humidity"] <= 100, f"Humidity out of range: {data['humidity']}"
    assert 0 <= data["wind_speed"] <= 200, f"Wind speed out of range: {data['wind_speed']}"
    assert 900 <= data["pressure"] <= 1100, f"Pressure out of range: {data['pressure']}"
    
    # Validate timestamp format
    assert len(data["observation_time"]) == 19, f"Invalid time format: {data['observation_time']}"

def test_get_station_list():
    """Test retrieving the list of weather stations."""
    stations = get_station_list()
    
    # Validate the returned station list
    assert len(stations) == len(WEATHER_STATIONS), "Station list length mismatch"
    assert all(isinstance(station, dict) for station in stations), "Invalid station format"
    assert all("city" in station and "name" in station for station in stations), \
        "Missing required station fields"

def test_get_weather_for_all_cities():
    """Test weather retrieval for all available cities."""
    for city in WEATHER_STATIONS.keys():
        data = get_weather(city)
        
        # Validate no errors
        assert "error" not in data, f"Error getting weather for {city}: {data.get('error')}"
        
        # Validate returned data
        validate_weather_data(data, city)

def test_get_weather_specific_cities():
    """Test weather retrieval for specific major cities."""
    test_cities = ["sydney", "melbourne"]
    
    for city in test_cities:
        data = get_weather(city)
        
        # Detailed validation for specific cities
        assert "error" not in data, f"Error getting weather for {city}: {data.get('error')}"
        validate_weather_data(data, city)
        
        # Validate city-specific info
        assert data["city"] == city
        assert WEATHER_STATIONS[city]["name"] in data["location"]
        
        # Print for manual verification
        print(f"\nWeather data for {city.title()}:")
        print(f"Temperature: {data['temperature']}°C")
        print(f"Humidity: {data['humidity']}%")
        print(f"Wind: {data['wind_speed']} km/h {data['wind_direction']}")
        print(f"Pressure: {data['pressure']} hPa")
        print(f"Rain since 9am: {data['rain_since_9am']} mm")
        print(f"Observation time: {data['observation_time']}")

def test_get_weather_invalid_city():
    """Test weather retrieval for invalid city."""
    data = get_weather("invalid_city")
    
    # Validate error response
    assert "error" in data, "Should return error for invalid city"
    assert "Available cities" in data["error"], "Should list available cities in error"
    for city in WEATHER_STATIONS.keys():
        assert city in data["error"].lower(), f"Available cities should include {city}"

def test_get_weather_case_insensitive():
    """Test case insensitive city names."""
    city_variants = [
        ("MELBOURNE", "melbourne"),
        ("Sydney", "sydney"),
        ("BrIsBaNe", "brisbane")
    ]
    
    for input_city, expected_city in city_variants:
        data = get_weather(input_city)
        assert "error" not in data, f"Error getting weather for {input_city}"
        assert data["city"] == expected_city
        validate_weather_data(data, expected_city)

@pytest.mark.asyncio
async def test_concurrent_weather_queries():
    """Test concurrent weather queries."""
    import asyncio
    
    async def get_weather_async(city: str) -> Dict[str, Any]:
        return get_weather(city)
    
    # Query multiple cities concurrently
    cities = ["sydney", "melbourne", "brisbane"]
    tasks = [get_weather_async(city) for city in cities]
    results = await asyncio.gather(*tasks)
    
    # Validate all results
    for city, data in zip(cities, results):
        assert "error" not in data, f"Error getting weather for {city}"
        validate_weather_data(data, city)

if __name__ == "__main__":
    # Run and print detailed info for specific cities
    test_get_weather_specific_cities()
