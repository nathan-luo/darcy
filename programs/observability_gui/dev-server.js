import express from 'express';
import { createServer as createViteServer } from 'vite';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import cors from 'cors';
import os from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get the local IP address of the WSL instance
function getLocalIP() {
  try {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
      for (const iface of interfaces[name]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;
        }
      }
    }
    return 'localhost';
  } catch (e) {
    return 'localhost';
  }
}

async function createServer() {
  const app = express();
  
  // Enable CORS
  app.use(cors());
  
  // Parse JSON
  app.use(express.json());

  // Get the absolute path to the logs directory
  // You can override with environment variable
  let logsDir = process.env.LOGS_PATH || path.resolve(__dirname, '../../logs');
  
  // Make sure we have a local logs directory for fallback
  const localLogsDir = path.resolve(__dirname, 'logs');
  if (!fs.existsSync(localLogsDir)) {
    try {
      fs.mkdirSync(localLogsDir, { recursive: true });
    } catch (err) {
      console.error('Error creating local logs directory:', err);
    }
  }
  
  // Verify the logs directory exists
  if (!fs.existsSync(logsDir)) {
    console.warn('WARNING: Logs directory not found:', logsDir);
    
    // Try alternative paths
    const alternatives = [
      path.resolve(process.cwd(), '../..', 'logs'),
      path.resolve(process.cwd(), 'logs'),
      localLogsDir,
      '/home/natha/dev/llmgine/logs'
    ];
    
    for (const altPath of alternatives) {
      if (fs.existsSync(altPath)) {
        logsDir = altPath;
        console.log('Using alternative logs directory:', logsDir);
        break;
      }
    }
  }
  
  // If we still don't have a valid logs directory, use the local one
  if (!fs.existsSync(logsDir)) {
    logsDir = localLogsDir;
    console.log('Using local logs directory as fallback:', logsDir);
  }

  console.log('Logs directory:', logsDir);
  
  // Make the logs directory if it doesn't exist
  if (!fs.existsSync(logsDir)) {
    console.log('Creating logs directory...');
    try {
      fs.mkdirSync(logsDir, { recursive: true });
    } catch (err) {
      console.error('Error creating logs directory:', err);
    }
  }

  // API routes first to prevent Vite middleware from handling them
  // API endpoint to get directory contents
  app.get('/api/files', (req, res) => {
    try {
      const dirPath = req.query.path || logsDir;
      console.log('Getting files from:', dirPath);
      
      if (!fs.existsSync(dirPath)) {
        console.log('Directory does not exist:', dirPath);
        return res.status(404).json({ error: 'Directory not found' });
      }
      
      const files = fs.readdirSync(dirPath, { withFileTypes: true }).map(dirent => ({
        name: dirent.name,
        isDirectory: dirent.isDirectory(),
        path: path.join(dirPath, dirent.name)
      }));
      
      res.json({ path: dirPath, files });
    } catch (error) {
      console.error('Error reading directory:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // API endpoint to read a file
  app.get('/api/file', (req, res) => {
    try {
      const filePath = req.query.path;
      console.log('Reading file:', filePath);
      
      if (!filePath) {
        return res.status(400).json({ error: 'File path is required' });
      }
      
      if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: 'File not found' });
      }
      
      const content = fs.readFileSync(filePath, 'utf-8');
      res.setHeader('Content-Type', 'application/json');
      res.json({ path: filePath, content });
    } catch (error) {
      console.error('Error reading file:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // Create Vite server in middleware mode and use its middleware
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'spa',
  });
  
  // Use vite's connect instance as middleware (after API routes)
  app.use(vite.middlewares);

  // Fallback route handler for SPA
  app.use('*', async (req, res, next) => {
    // Only handle GET requests
    if (req.method !== 'GET') return next();
    
    try {
      // 404 for API requests that weren't handled
      if (req.path.startsWith('/api/')) {
        return res.status(404).json({ error: 'API endpoint not found' });
      }
      
      // Let vite transform the index.html
      let template = fs.readFileSync(
        path.resolve(__dirname, 'index.html'),
        'utf-8'
      );
      template = await vite.transformIndexHtml(req.originalUrl, template);
      
      res.status(200).set({ 'Content-Type': 'text/html' }).end(template);
    } catch (e) {
      vite.ssrFixStacktrace(e);
      console.log(e.stack);
      res.status(500).end(e.stack);
    }
  });

  const PORT = parseInt(process.env.PORT || '5173');
  
  app.listen(PORT, '0.0.0.0', () => {
    const ip = getLocalIP();
    console.log();
    console.log('\x1b[32m%s\x1b[0m', '🚀 LLMgine Log Visualizer running at:');
    console.log('\x1b[36m%s\x1b[0m', `  > Local:    http://localhost:${PORT}`);
    console.log('\x1b[36m%s\x1b[0m', `  > WSL/LAN:  http://${ip}:${PORT}`);
    console.log();
    console.log('\x1b[33m%s\x1b[0m', 'API Endpoints:');
    console.log('\x1b[36m%s\x1b[0m', `  > Files:    http://${ip}:${PORT}/api/files`);
    console.log('\x1b[36m%s\x1b[0m', `  > File:     http://${ip}:${PORT}/api/file?path=<file_path>`);
    console.log();
  });
}

createServer().catch((e) => {
  console.error(e);
  process.exit(1);
});