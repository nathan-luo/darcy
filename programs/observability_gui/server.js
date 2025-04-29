import express from 'express';
import fs from 'fs';
import path from 'path';
import cors from 'cors';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

// Enable CORS
app.use(cors());

// Serve static files from the dist directory
app.use(express.static('dist'));
app.use(express.json());

// Get logs directory path
const logsDir = path.resolve(__dirname, '../../logs');

// API endpoint to get directory contents
app.get('/api/files', (req, res) => {
  try {
    const dirPath = req.query.path || logsDir;
    
    // Ensure the path is within our project (security check)
    if (!dirPath.startsWith(path.resolve(__dirname, '../..'))) {
      return res.status(403).json({ error: 'Access denied' });
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
    
    if (!filePath) {
      return res.status(400).json({ error: 'File path is required' });
    }
    
    // Ensure the path is within our project (security check)
    if (!filePath.startsWith(path.resolve(__dirname, '../..'))) {
      return res.status(403).json({ error: 'Access denied' });
    }
    
    const content = fs.readFileSync(filePath, 'utf-8');
    res.json({ path: filePath, content });
  } catch (error) {
    console.error('Error reading file:', error);
    res.status(500).json({ error: error.message });
  }
});

// Serve the index.html for any other route to support the SPA
app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Logs directory: ${logsDir}`);
});