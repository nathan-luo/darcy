import React from 'react';
import { LLMgineEvent, LogEvent, TraceEvent } from '@/types';
import { AlertCircle, FileText, Activity } from 'lucide-react';
import { format } from 'date-fns';

interface ErrorsViewProps {
  events: LLMgineEvent[];
}

export const ErrorsView: React.FC<ErrorsViewProps> = ({ events }) => {
  // Get all error events (LogEvents with ERROR level or TraceEvents with error status)
  const errorEvents = events.filter(event => 
    (event.event_type === 'LogEvent' && (event as LogEvent).level === 'ERROR') ||
    (event.event_type === 'TraceEvent' && (event as TraceEvent).status?.toLowerCase() === 'error')
  );
  
  // Sort by timestamp (newest first)
  const sortedErrors = [...errorEvents].sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
  
  const getSourceFile = (source: string | undefined) => {
    if (!source) return 'Unknown source';
    
    // Extract the file name from a path like "/home/user/project/src/file.py:123"
    const parts = source.split('/');
    return parts[parts.length - 1];
  };
  
  const formatErrorTime = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'HH:mm:ss.SSS');
    } catch (error) {
      return 'Invalid date';
    }
  };
  
  return (
    <div className="space-y-4">
      {sortedErrors.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          No errors found in the log data
        </div>
      ) : (
        <div>
          <div className="text-sm font-medium mb-4">
            Found {sortedErrors.length} errors in the log data
          </div>
          
          <div className="space-y-3">
            {sortedErrors.map((error, index) => (
              <div
                key={error.id || index}
                className="bg-red-50 border-l-4 border-red-500 rounded-md p-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <AlertCircle className="h-4 w-4 text-red-500 mr-2" />
                    {error.event_type === 'LogEvent' ? (
                      <FileText className="h-4 w-4 text-blue-500 mr-2" />
                    ) : (
                      <Activity className="h-4 w-4 text-green-500 mr-2" />
                    )}
                    <span className="font-medium">
                      {error.event_type === 'LogEvent'
                        ? (error as LogEvent).message
                        : `Error in trace: ${(error as TraceEvent).name}`}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatErrorTime(error.timestamp)}
                  </div>
                </div>
                
                <div className="mt-2 text-xs">
                  <div className="text-gray-600">
                    Source: {getSourceFile(error.source)}
                  </div>
                  
                  {error.event_type === 'LogEvent' && (error as LogEvent).context && (
                    <div className="mt-1 text-gray-600">
                      <span className="font-medium">Context:</span>
                      <div className="ml-2">
                        {Object.entries((error as LogEvent).context).map(([key, value]) => (
                          <div key={key}>
                            {key}: {String(value)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {error.event_type === 'TraceEvent' && (error as TraceEvent).attributes && (
                    <div className="mt-1 text-gray-600">
                      <span className="font-medium">Attributes:</span>
                      <div className="ml-2">
                        {Object.entries((error as TraceEvent).attributes).map(([key, value]) => (
                          <div key={key}>
                            {key}: {String(value)}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};