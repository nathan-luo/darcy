from typing import Dict
import time
import statistics
from typing import Callable, List, Any, Optional
import functools


def time_execution(func: Callable, *args, **kwargs) -> float:
    """
    Measure the execution time of a function.
    
    Args:
        func: The function to time
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        float: Execution time in seconds
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return end_time - start_time


def benchmark(iterations: int = 10) -> Callable:
    """
    Decorator to benchmark a function over multiple iterations.
    
    Args:
        iterations: Number of times to run the function
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> dict:
            times: List[float] = []
            results = None
            
            for _ in range(iterations):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                if results is None:
                    results = result
                
                times.append(end_time - start_time)
            
            stats = {
                "min": min(times),
                "max": max(times),
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0,
                "total": sum(times),
                "iterations": iterations,
                "result": results
            }
            
            return stats
        
        return wrapper
    
    return decorator


class CodeTimer:
    """
    Context manager for timing code blocks.
    
    Example:
        with CodeTimer() as timer:
            # Code to time
            time.sleep(1)
        print(f"Execution time: {timer.execution_time} seconds")
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the timer.
        
        Args:
            name: Optional name for this timer
        """
        self.name = name
        self.execution_time = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.execution_time = time.time() - self.start_time
        print(f"Execution time: {self.execution_time:.4f} seconds")

class MemoryTracker:
    """
    Utility for tracking memory usage of Python objects.
    
    Example:
        obj = SomeClass()
        memory_info = MemoryTracker(obj)
        print(f"Object size: {memory_info.size} bytes")
        print(f"Detailed breakdown: {memory_info.detailed}")
    """
    
    def __init__(self, obj: Any):
        """
        Initialize the memory tracker for a given object.
        
        Args:
            obj: The object to track memory usage for
        """
        import sys
        import inspect
        from types import ModuleType, FunctionType
        
        self.obj = obj
        self._size = 0
        self._detailed = {}
        
        # Get the size of the object itself
        self._size = sys.getsizeof(obj)
        self._detailed["self"] = self._size
        
        # If it's a dictionary, add size of contents
        if isinstance(obj, dict):
            self._detailed["dict_contents"] = sum(
                sys.getsizeof(k) + sys.getsizeof(v) for k, v in obj.items()
            )
            self._size += self._detailed["dict_contents"]
            
        # If it's a custom object, examine its __dict__
        elif hasattr(obj, "__dict__"):
            dict_size = 0
            attr_sizes = {}
            
            for key, value in obj.__dict__.items():
                # Skip modules, functions, and methods to avoid recursion issues
                if isinstance(value, (ModuleType, FunctionType)) or inspect.ismethod(value):
                    continue
                    
                attr_size = sys.getsizeof(value)
                attr_sizes[key] = attr_size
                dict_size += attr_size
                
            self._detailed["attributes"] = attr_sizes
            self._detailed["total_attributes"] = dict_size
            self._size += dict_size
            
        # If it's a list or tuple, add size of contents
        elif isinstance(obj, (list, tuple)):
            contents_size = sum(sys.getsizeof(x) for x in obj)
            self._detailed["contents"] = contents_size
            self._size += contents_size
        
        print(f"Size in bytes: {self.size}")

    
    @property
    def size(self) -> int:
        """Total estimated memory size in bytes."""
        return self._size
    
    @property
    def detailed(self) -> Dict[str, Any]:
        """Detailed breakdown of memory usage."""
        return self._detailed
    
    def __str__(self) -> str:
        """String representation of memory usage."""
        return f"Memory usage: {self.size} bytes"


if __name__ == "__main__":
    # Insert your code here
    from openai import AsyncOpenAI
    with CodeTimer() as timer:
        client = AsyncOpenAI()
        MemoryTracker(client)
        


    # Example usage
    
    # # 1. Using the CodeTimer context manager
    # print("Example 1: Using CodeTimer context manager")
    # with CodeTimer() as timer:
    #     time.sleep(0.5)  # Simulate work
    # print(f"Execution time: {timer.execution_time:.4f} seconds\n")
    
    # # 2. Using the time_execution function
    # print("Example 2: Using time_execution function")
    # def example_function(n: int) -> int:
    #     """Calculate the sum of numbers from 0 to n-1."""
    #     return sum(range(n))
    
    # execution_time = time_execution(example_function, 1000000)
    # print(f"Time to sum 1 million numbers: {execution_time:.4f} seconds\n")
    
    # # 3. Using the benchmark decorator
    # print("Example 3: Using benchmark decorator")
    # @benchmark(iterations=5)
    # def fibonacci(n: int) -> int:
    #     """Calculate the nth Fibonacci number recursively."""
    #     if n <= 1:
    #         return n
    #     return fibonacci(n-1) + fibonacci(n-2)
    
    # results = fibonacci(20)
    # print(f"Fibonacci benchmark results:")
    # for key, value in results.items():
    #     if key != "result":
    #         if isinstance(value, float):
    #             print(f"  {key}: {value:.6f}")
    #         else:
    #             print(f"  {key}: {value}")
    # print(f"  result: {results['result']}")
