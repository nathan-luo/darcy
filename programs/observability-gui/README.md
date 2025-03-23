# LLMgine Log Visualizer

A modern, feature-rich application for visualizing and analyzing logs from the LLMgine project.

## Features

- 📊 Dashboard with log statistics and metrics
- ⏱️ Timeline view for chronological log browsing
- 🔍 Trace analysis for distributed tracing visualization
- 📈 Metrics visualization with charts
- 🚨 Error analysis and reporting
- 🔎 Advanced filtering capabilities
- 📂 File browser integration

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Running on WSL2 (Recommended)

```bash
# Install dependencies (first time only)
npm install

# Start the development server with convenient IP display
./start.sh
```

This will:
1. Show your WSL2 IP address
2. Start the development server
3. Display URLs for accessing the app from both Windows and WSL2

Then open the provided URL in your Windows browser.

### Manual Installation and Running

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. For production build:
```bash
npm run build
```

## Usage

1. Launch the application
2. Navigate to the logs directory using the file browser
3. Select a log file (JSONL format)
4. Use the tabs to switch between different visualization views
5. Apply filters to focus on specific log events

## Log Format

The application is designed to work with LLMgine logs in JSONL format. Each log entry should contain:

- Common fields: `id`, `timestamp`, `source`, `event_type`
- Event-specific fields based on the event type:
  - `LogEvent`: level, message, context
  - `TraceEvent`: name, span_context, attributes, etc.
  - `MetricEvent`: metrics array with name, value, unit

## Tech Stack

- React
- TypeScript
- Vite
- TailwindCSS
- Recharts
- RadixUI Components

## Project Structure

```
/src
  /components    # UI components
  /lib           # Utility functions
  /styles        # CSS styles
  /types         # TypeScript type definitions
  App.tsx        # Main application component
  main.tsx       # Application entry point
```

## License

MIT