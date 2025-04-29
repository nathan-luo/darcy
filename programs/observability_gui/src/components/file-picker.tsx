import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Folder, File, RefreshCw, Home } from 'lucide-react';

interface FileInfo {
  name: string;
  isDirectory: boolean;
  path: string;
}

interface FilePickerProps {
  onFileSelect: (path: string, content: string) => void;
}

export const FilePicker: React.FC<FilePickerProps> = ({ onFileSelect }) => {
  const [logDir, setLogDir] = useState<string | null>(null);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [currentDir, setCurrentDir] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const API_URL = '/api'; // Use relative URL for the API

  useEffect(() => {
    // Load the logs directory on component mount
    fetchLogDirectory();
  }, []);

  const fetchLogDirectory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      console.log('Fetching logs directory from API...');
      const response = await fetch(`${API_URL}/files`);
      
      // Check for non-OK responses
      if (!response.ok) {
        console.error('API returned error:', response.status, response.statusText);
        throw new Error(`Failed to fetch logs directory: ${response.statusText}`);
      }
      
      // Try to parse the response as JSON
      let data;
      try {
        const text = await response.text();
        console.log('Raw API response:', text.substring(0, 100) + '...');
        data = JSON.parse(text);
      } catch (parseError) {
        console.error('Failed to parse JSON response:', parseError);
        throw new Error('Invalid response from server. Not a valid JSON.');
      }
      
      if (data.error) {
        throw new Error(data.error);
      }

      console.log('Directory data:', data);
      setLogDir(data.path);
      setCurrentDir(data.path);
      setFiles(data.files || []);
    } catch (error) {
      console.error('Error fetching logs directory:', error);
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
  };

  const loadFiles = async (dirPath: string) => {
    setIsLoading(true);
    setError(null);
    try {
      console.log('Loading files from directory:', dirPath);
      const response = await fetch(`${API_URL}/files?path=${encodeURIComponent(dirPath)}`);
      
      // Check for non-OK responses
      if (!response.ok) {
        console.error('API returned error:', response.status, response.statusText);
        throw new Error(`Failed to load files: ${response.statusText}`);
      }
      
      // Try to parse the response as JSON
      let data;
      try {
        const text = await response.text();
        console.log('Raw API response:', text.substring(0, 100) + '...');
        data = JSON.parse(text);
      } catch (parseError) {
        console.error('Failed to parse JSON response:', parseError);
        throw new Error('Invalid response from server. Not a valid JSON.');
      }
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Sort: directories first, then files alphabetically
      const sortedFiles = (data.files || []).sort((a: FileInfo, b: FileInfo) => {
        if (a.isDirectory && !b.isDirectory) return -1;
        if (!a.isDirectory && b.isDirectory) return 1;
        return a.name.localeCompare(b.name);
      });
      
      setFiles(sortedFiles);
      setCurrentDir(dirPath);
      
      // If we have no files but we're in the logs directory, show a helpful message
      if (sortedFiles.length === 0 && dirPath === logDir) {
        setError("No log files found in the logs directory. Please check if logs have been generated.");
      }
    } catch (error) {
      console.error('Error loading files:', error);
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileClick = async (file: FileInfo) => {
    if (file.isDirectory) {
      loadFiles(file.path);
    } else if (file.path.endsWith('.jsonl') || file.path.endsWith('.json')) {
      try {
        setIsLoading(true);
        console.log('Reading file:', file.path);
        const response = await fetch(`${API_URL}/file?path=${encodeURIComponent(file.path)}`);
        
        // Check for non-OK responses
        if (!response.ok) {
          console.error('API returned error:', response.status, response.statusText);
          throw new Error(`Failed to read file: ${response.statusText}`);
        }
        
        // Try to parse the response as JSON
        let data;
        try {
          const text = await response.text();
          console.log('Raw API response (first 100 chars):', text.substring(0, 100) + '...');
          data = JSON.parse(text);
        } catch (parseError) {
          console.error('Failed to parse JSON response:', parseError);
          throw new Error('Invalid response from server. Not a valid JSON.');
        }
        
        if (data.error) {
          throw new Error(data.error);
        }
        
        if (data.content) {
          console.log('File loaded successfully, length:', data.content.length);
          onFileSelect(file.path, data.content);
        } else {
          throw new Error('File content is empty');
        }
      } catch (error) {
        console.error('Error reading file:', error);
        setError(error instanceof Error ? error.message : String(error));
      } finally {
        setIsLoading(false);
      }
    }
  };

  const navigateUp = () => {
    if (currentDir && currentDir !== logDir) {
      const parentDir = currentDir.split('/').slice(0, -1).join('/');
      loadFiles(parentDir);
    }
  };

  const navigateHome = () => {
    if (logDir) {
      loadFiles(logDir);
    }
  };

  const refreshDirectory = () => {
    if (currentDir) {
      loadFiles(currentDir);
    } else {
      fetchLogDirectory();
    }
  };

  return (
    <div className="p-4 border rounded-lg bg-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium">Log Files</h3>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm" onClick={refreshDirectory} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="outline" size="sm" onClick={navigateHome}>
            <Home className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      {currentDir && (
        <div className="mb-3 text-sm text-gray-500 truncate" title={currentDir}>
          Current directory: {currentDir}
        </div>
      )}
      
      {currentDir && currentDir !== logDir && (
        <Button 
          variant="ghost" 
          size="sm" 
          className="mb-2 text-xs" 
          onClick={navigateUp}
        >
          ⬆️ Up
        </Button>
      )}
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-3">
          <p className="text-sm">{error}</p>
        </div>
      )}
      
      <div className="max-h-96 overflow-y-auto border rounded bg-gray-50">
        {isLoading ? (
          <div className="flex justify-center items-center h-20">
            <RefreshCw className="h-5 w-5 animate-spin text-blue-500 mr-2" />
            <span className="text-sm text-gray-500">Loading...</span>
          </div>
        ) : files.length === 0 ? (
          <div className="flex justify-center items-center h-20">
            <span className="text-sm text-gray-500">No log files found</span>
          </div>
        ) : (
          <ul className="divide-y">
            {files.map((file) => (
              <li 
                key={file.path}
                onClick={() => handleFileClick(file)}
                className="flex items-center p-2 hover:bg-gray-100 cursor-pointer"
              >
                {file.isDirectory ? (
                  <Folder className="h-4 w-4 mr-2 text-blue-500" />
                ) : file.name.endsWith('.jsonl') || file.name.endsWith('.json') ? (
                  <File className="h-4 w-4 mr-2 text-green-500" />
                ) : (
                  <File className="h-4 w-4 mr-2 text-gray-400" />
                )}
                <span className={file.isDirectory ? "font-medium" : "text-sm"}>
                  {file.name}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};