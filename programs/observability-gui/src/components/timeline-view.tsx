import React from 'react';
import { LLMgineEvent } from '@/types';
import { format } from 'date-fns';
import { getLogLevelColor, getEventTypeColor } from '@/lib/utils';
import { FileText, Activity, Gauge } from 'lucide-react';

interface TimelineViewProps {
  events: LLMgineEvent[];
  maxEvents?: number;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ events, maxEvents = 100 }) => {
  // Get the latest events up to maxEvents
  const displayEvents = events.slice(0, maxEvents);
  
  const getEventIcon = (event: LLMgineEvent) => {
    switch (event.event_type) {
      case 'LogEvent':
        return <FileText className="h-4 w-4 text-blue-500" />;
      case 'TraceEvent':
        return <Activity className="h-4 w-4 text-green-500" />;
      case 'MetricEvent':
        return <Gauge className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };
  
  const getEventTitle = (event: LLMgineEvent) => {
    switch (event.event_type) {
      case 'LogEvent':
        return `${event.level}: ${event.message}`;
      case 'TraceEvent':
        return `Span: ${event.name}${event.status ? ` (${event.status})` : ''}`;
      case 'MetricEvent':
        return event.metrics && event.metrics.length > 0
          ? `Metric: ${event.metrics[0].name}`
          : 'Metric Event';
      default:
        return 'Unknown Event';
    }
  };
  
  const getBadgeClass = (event: LLMgineEvent) => {
    if (event.event_type === 'LogEvent') {
      return getLogLevelColor(event.level);
    } else {
      return getEventTypeColor(event.event_type);
    }
  };
  
  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'HH:mm:ss.SSS');
    } catch (error) {
      return 'Invalid date';
    }
  };
  
  return (
    <div className="space-y-1">
      {displayEvents.map((event, index) => (
        <div 
          key={event.id || index}
          className={`p-2 rounded-md text-sm ${
            event.event_type === 'LogEvent' && event.level === 'ERROR' 
              ? 'border-l-4 border-red-500 bg-red-50' 
              : getEventTypeColor(event.event_type)
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center">
              {getEventIcon(event)}
              <span className="ml-2 font-mono text-xs text-gray-500">
                {formatTimestamp(event.timestamp)}
              </span>
              <span className={`ml-2 px-1.5 py-0.5 rounded text-xs ${getBadgeClass(event)}`}>
                {event.event_type === 'LogEvent' ? event.level : event.event_type}
              </span>
            </div>
            <span className="text-xs text-gray-500 truncate max-w-xs" title={event.source}>
              {event.source?.split('/').slice(-2).join('/')}
            </span>
          </div>
          
          <div className="font-medium">
            {getEventTitle(event)}
          </div>
          
          {event.event_type === 'LogEvent' && event.context && Object.keys(event.context).length > 0 && (
            <div className="mt-1 text-xs text-gray-600">
              Context: {Object.entries(event.context).map(([key, value]) => (
                <span key={key} className="mr-2">
                  {key}={String(value)}
                </span>
              ))}
            </div>
          )}
          
          {event.event_type === 'TraceEvent' && event.attributes && Object.keys(event.attributes).length > 0 && (
            <div className="mt-1 text-xs text-gray-600">
              Attributes: {Object.entries(event.attributes).map(([key, value]) => (
                <span key={key} className="mr-2">
                  {key}={String(value)}
                </span>
              ))}
            </div>
          )}
          
          {event.event_type === 'TraceEvent' && event.start_time && event.end_time && (
            <div className="mt-1 text-xs text-gray-600">
              Duration: {new Date(event.end_time).getTime() - new Date(event.start_time).getTime()}ms
            </div>
          )}
          
          {event.event_type === 'MetricEvent' && event.metrics && event.metrics.length > 0 && (
            <div className="mt-1 text-xs">
              {event.metrics.map((metric, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <span>{metric.name}</span>
                  <span className="font-mono">
                    {metric.value} {metric.unit || ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      
      {events.length > maxEvents && (
        <div className="text-center text-xs text-gray-500 mt-2">
          Showing {maxEvents} of {events.length} events. Use filters to narrow results.
        </div>
      )}
    </div>
  );
};