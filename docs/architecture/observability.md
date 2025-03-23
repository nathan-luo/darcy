# Observability Architecture in LLMgine

LLMgine implements a comprehensive observability system built around a modular, extensible architecture.

## Core Components

### ObservabilityBus

The `ObservabilityBus` acts as the central hub for all observability concerns:

- **Logging**: Structured log events with levels, context, and source information
- **Metrics**: Numerical measurements with tags and units
- **Tracing**: Distributed tracing for request flows with parent-child relationships

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                 ObservabilityBus                    │
│                                                     │
└─┬───────────────────┬────────────────┬─────────────┘
  │                   │                │
  ▼                   ▼                ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│          │    │          │    │          │
│  Logs    │    │ Metrics  │    │ Traces   │
│          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘
```

## Handler-Based Architecture

Observability is implemented using a handler-based architecture:

```
┌─────────────────────────────────────────┐
│                                         │
│          ObservabilityBus               │
│                                         │
└───┬─────────────┬────────────┬─────────┘
    │             │            │
    ▼             ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Console │  │ File    │  │ Custom  │
│ Handler │  │ Handler │  │ Handler │
└─────────┘  └─────────┘  └─────────┘
```

### ObservabilityHandler

The base `ObservabilityHandler` class defines the interface for all handlers:

```python
class ObservabilityHandler(Generic[TEvent], ABC):
    @property
    def event_type(self) -> Type[TEvent]:
        # Event type this handler processes
        pass
        
    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        # Process the event
        pass
```

## Built-in Handlers

LLMgine provides several built-in handlers:

### Log Handlers
- **ConsoleLogHandler**: Outputs logs to the console
- **JsonFileHandler**: Writes all events to a JSON file

### Metric Handlers
- **ConsoleMetricsHandler**: Outputs metrics to the console
- **InMemoryMetricsHandler**: Stores metrics in memory for later retrieval

### Trace Handlers
- **ConsoleTraceHandler**: Outputs trace spans to the console
- **InMemoryTraceHandler**: Stores traces in memory with parent-child relationships

## Extensibility

The system is designed for easy extension:

```python
# Create a custom handler
class SlackLogHandler(ObservabilityHandler[LogEvent]):
    def __init__(self, webhook_url: str):
        super().__init__()
        self.webhook_url = webhook_url
        
    def _get_event_type(self) -> Type[LogEvent]:
        return LogEvent
        
    async def handle(self, event: LogEvent) -> None:
        # Post critical logs to Slack
        if event.level == LogLevel.CRITICAL:
            await self._post_to_slack(event.message)

# Register with ObservabilityBus
obs_bus = ObservabilityBus()
obs_bus.add_handler(SlackLogHandler("https://hooks.slack.com/..."))
```

## Event Types

### LogEvent
Represents log entries with levels, messages, and context:

```python
@dataclass
class LogEvent(BaseEvent):
    level: LogLevel = LogLevel.INFO
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
```

### MetricEvent
Represents metrics with names, values, and dimensions:

```python
@dataclass
class MetricEvent(BaseEvent):
    metrics: List[Metric] = field(default_factory=list)
```

### TraceEvent
Represents spans in a distributed trace:

```python
@dataclass
class TraceEvent(BaseEvent):
    name: str = ""
    span_context: SpanContext = field(default_factory=SpanContext)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
```

## Usage

### Basic Usage

```python
from llmgine.observability import ObservabilityBus
from llmgine.observability.events import LogLevel

# Get singleton instance
obs_bus = ObservabilityBus()

# Logging
obs_bus.log(LogLevel.INFO, "User logged in", {"user_id": "123"})

# Metrics
obs_bus.metric("api_requests", 1, tags={"endpoint": "/users"})

# Tracing
span = obs_bus.start_trace("process_request", {"request_id": "req123"})
# ... do work ...
obs_bus.end_trace(span, status="success")
```

### Custom Handlers

```python
from llmgine.observability.handlers import ObservabilityHandler
from llmgine.observability.events import LogEvent

# Create custom handler
class DatabaseLogHandler(ObservabilityHandler[LogEvent]):
    def _get_event_type(self):
        return LogEvent
        
    async def handle(self, event: LogEvent):
        # Store log in database
        await db.logs.insert_one({
            "level": event.level.value,
            "message": event.message,
            "timestamp": event.timestamp,
            "context": event.context
        })

# Register handler
obs_bus = ObservabilityBus()
obs_bus.add_handler(DatabaseLogHandler())
```

### Configuration

The ObservabilityBus can be configured with different handlers based on environment:

```python
# Development environment
if env == "development":
    obs_bus.add_handler(ConsoleLogHandler(min_level=LogLevel.DEBUG))
    obs_bus.add_handler(JsonFileHandler(log_dir="logs/dev"))

# Production environment
elif env == "production":
    obs_bus.add_handler(ConsoleLogHandler(min_level=LogLevel.INFO))
    obs_bus.add_handler(JsonFileHandler(log_dir="logs/prod"))
    obs_bus.add_handler(CloudWatchLogHandler(region="us-west-2"))
```

## Integration with MessageBus

The ObservabilityBus is integrated with the MessageBus to provide automatic logging of commands and events:

```
┌───────────────────┐       ┌───────────────────┐
│                   │       │                   │
│   MessageBus      │─────▶│  ObservabilityBus  │
│                   │       │                   │
└───────────────────┘       └───────────────────┘
         │                           │
         ▼                           ▼
┌───────────────────┐       ┌───────────────────┐
│                   │       │                   │
│   Commands &      │       │   Logs, Metrics,  │
│     Events        │       │     & Traces      │
│                   │       │                   │
└───────────────────┘       └───────────────────┘
```

This integration ensures comprehensive visibility into all system operations.