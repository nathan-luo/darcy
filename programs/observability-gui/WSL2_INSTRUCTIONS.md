# Running the LLMgine Log Visualizer on WSL2

This document provides instructions for running the log visualizer application on WSL2 and accessing it from your Windows host.

## Setup and Run

1. Install dependencies:
```bash
cd /home/natha/dev/llmgine/programs/observability
npm install
```

2. Build the application:
```bash
npm run build
```

3. Start the server:
```bash
npm run server
```

Or you can do both build and start with:
```bash
npm start
```

## Accessing from Windows

When the server is running on WSL2, you can access it from your Windows browser using one of these methods:

### Method 1: Using localhost
In most WSL2 setups, you can access the server by simply navigating to:
```
http://localhost:3000
```

### Method 2: Using WSL2 IP address
If localhost forwarding isn't working, you can find your WSL2 IP address and use that:

1. In your WSL2 terminal, run:
```bash
ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1
```

2. This will display an IP address (typically like 172.x.x.x)

3. Open your Windows browser and navigate to:
```
http://[WSL2-IP-ADDRESS]:3000
```

## Troubleshooting

If you're having problems connecting:

1. **Firewall Issues**: Make sure Windows Firewall isn't blocking the connection. You may need to add an exception for port 3000.

2. **Port Conflict**: If something else is using port 3000, you can change the port in the server.js file.

3. **WSL Networking Issues**: Try restarting WSL with:
```
wsl --shutdown
```
Then restart your WSL terminal.

## Features

- Browser any directory in the logs folder
- View log files in a structured format
- Analyze traces, metrics, and errors
- Filter and search log contents