import React, { useState } from 'react';
import { LLMgineEvent, TraceEvent } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getTraceSpans, buildTraceTree } from '@/lib/utils';
import { ChevronRight, ChevronDown, Circle } from 'lucide-react';

interface TracesViewProps {
  events: LLMgineEvent[];
}

export const TracesView: React.FC<TracesViewProps> = ({ events }) => {
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(new Set());
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(new Set());
  
  // Get all unique trace IDs
  const traceEvents = events.filter((event): event is TraceEvent => 
    event.event_type === 'TraceEvent'
  );
  
  const traceIds = new Set<string>();
  traceEvents.forEach(event => {
    traceIds.add(event.span_context.trace_id);
  });
  
  // Convert to array and sort by timestamp of first span
  const sortedTraceIds = Array.from(traceIds).sort((a, b) => {
    const aSpans = getTraceSpans(events, a);
    const bSpans = getTraceSpans(events, b);
    
    if (aSpans.length === 0 || bSpans.length === 0) return 0;
    
    const aTime = new Date(aSpans[0].timestamp).getTime();
    const bTime = new Date(bSpans[0].timestamp).getTime();
    
    return bTime - aTime; // Newest first
  });
  
  const toggleTrace = (traceId: string) => {
    const newExpanded = new Set(expandedTraces);
    if (newExpanded.has(traceId)) {
      newExpanded.delete(traceId);
    } else {
      newExpanded.add(traceId);
    }
    setExpandedTraces(newExpanded);
  };
  
  const toggleSpan = (spanId: string) => {
    const newExpanded = new Set(expandedSpans);
    if (newExpanded.has(spanId)) {
      newExpanded.delete(spanId);
    } else {
      newExpanded.add(spanId);
    }
    setExpandedSpans(newExpanded);
  };
  
  const getSpanDuration = (span: TraceEvent) => {
    if (span.start_time && span.end_time) {
      return new Date(span.end_time).getTime() - new Date(span.start_time).getTime();
    }
    return null;
  };
  
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'ok':
      case 'success':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };
  
  const renderSpanTree = (spans: any[], level = 0) => {
    return spans.map((span) => {
      const hasChildren = span.children && span.children.length > 0;
      const isExpanded = expandedSpans.has(span.span_context.span_id);
      const duration = getSpanDuration(span);
      
      return (
        <div key={span.span_context.span_id} className="mb-1">
          <div
            className={`flex items-center py-1 pl-${level * 6} ${hasChildren ? 'cursor-pointer' : ''}`}
            onClick={() => hasChildren && toggleSpan(span.span_context.span_id)}
          >
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="h-3 w-3 mr-1 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-3 w-3 mr-1 flex-shrink-0" />
              )
            ) : (
              <Circle className="h-2 w-2 mr-2 flex-shrink-0" />
            )}
            
            <div className="flex-1 flex items-center justify-between">
              <div className="text-sm font-medium truncate max-w-md" title={span.name}>
                {span.name}
              </div>
              
              <div className="flex items-center space-x-2">
                {span.status && (
                  <span className={`text-xs ${getStatusColor(span.status)}`}>
                    {span.status}
                  </span>
                )}
                
                {duration !== null && (
                  <span className="text-xs text-gray-500">
                    {duration}ms
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {hasChildren && isExpanded && (
            <div className="border-l border-gray-200 ml-1 pl-2">
              {renderSpanTree(span.children, level + 1)}
            </div>
          )}
          
          {isExpanded && (
            <div className="ml-6 mb-2 text-xs text-gray-600">
              {Object.entries(span.attributes).length > 0 && (
                <div className="bg-gray-50 p-1 rounded mt-1">
                  {Object.entries(span.attributes).map(([key, value]) => (
                    <div key={key}>
                      <span className="font-medium">{key}:</span> {String(value)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      );
    });
  };
  
  return (
    <div className="space-y-4">
      {sortedTraceIds.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          No trace events found in the log data
        </div>
      ) : (
        sortedTraceIds.map(traceId => {
          const spans = getTraceSpans(events, traceId);
          const isExpanded = expandedTraces.has(traceId);
          
          if (spans.length === 0) return null;
          
          const rootSpan = spans[0];
          const duration = getSpanDuration(rootSpan);
          const traceTree = buildTraceTree(spans);
          
          return (
            <Card key={traceId} className="overflow-hidden">
              <CardHeader
                className="bg-gray-50 cursor-pointer py-2 px-4"
                onClick={() => toggleTrace(traceId)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <CardTitle className="text-sm font-medium">
                      {rootSpan.name}
                    </CardTitle>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                    <span>
                      Spans: {spans.length}
                    </span>
                    {duration !== null && (
                      <span>
                        Duration: {duration}ms
                      </span>
                    )}
                    {rootSpan.status && (
                      <span className={`${getStatusColor(rootSpan.status)}`}>
                        {rootSpan.status}
                      </span>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              {isExpanded && (
                <CardContent className="py-2">
                  {renderSpanTree(traceTree)}
                </CardContent>
              )}
            </Card>
          );
        })
      )}
    </div>
  );
};