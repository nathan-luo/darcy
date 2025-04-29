/**
 * Types for LLMgine log data
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export interface Metric {
  name: string;
  value: number;
  unit?: string;
  tags?: Record<string, string>;
}

export interface SpanContext {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
}

export interface BaseEvent {
  id: string;
  timestamp: string;
  source: string;
  event_type: 'LogEvent' | 'MetricEvent' | 'TraceEvent';
}

export interface LogEvent extends BaseEvent {
  event_type: 'LogEvent';
  level: LogLevel;
  message: string;
  context: Record<string, any>;
}

export interface MetricEvent extends BaseEvent {
  event_type: 'MetricEvent';
  metrics: Metric[];
}

export interface TraceEvent extends BaseEvent {
  event_type: 'TraceEvent';
  name: string;
  span_context: SpanContext;
  start_time: string | null;
  end_time: string | null;
  duration_ms: number | null;
  attributes: Record<string, any>;
  events: any[];
  status: string;
}

export type LLMgineEvent = LogEvent | MetricEvent | TraceEvent;

export interface FilterOptions {
  level?: LogLevel[];
  eventType?: ('LogEvent' | 'MetricEvent' | 'TraceEvent')[];
  component?: string[];
  timeRange?: [Date, Date];
  query?: string;
}

export interface StatsData {
  totalEvents: number;
  eventTypeCounts: Record<string, number>;
  logLevelCounts: Record<string, number>;
  components: string[];
  timeRange: [Date, Date];
  traceStatuses: Record<string, number>;
  avgTraceDurations: Record<string, number>;
}