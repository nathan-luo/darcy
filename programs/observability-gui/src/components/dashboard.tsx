import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Gauge, 
  FileText, 
  Activity,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { StatsData } from '@/types';
import { format } from 'date-fns';

interface DashboardProps {
  stats: StatsData;
}

export const Dashboard: React.FC<DashboardProps> = ({ stats }) => {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Events</CardTitle>
          <FileText className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalEvents}</div>
          <p className="text-xs text-muted-foreground">
            {format(stats.timeRange[0], 'yyyy-MM-dd HH:mm:ss')} to {format(stats.timeRange[1], 'yyyy-MM-dd HH:mm:ss')}
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Log Events</CardTitle>
          <FileText className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.eventTypeCounts['LogEvent'] || 0}</div>
          <div className="mt-1 flex space-x-2">
            {Object.entries(stats.logLevelCounts || {}).map(([level, count]) => (
              <span 
                key={level} 
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                  ${level === 'DEBUG' ? 'bg-gray-100 text-gray-800' : 
                    level === 'INFO' ? 'bg-blue-100 text-blue-800' : 
                    level === 'WARNING' ? 'bg-yellow-100 text-yellow-800' : 
                    level === 'ERROR' ? 'bg-red-100 text-red-800' : 
                    'bg-purple-100 text-purple-800'}`}
              >
                {level}: {count}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Trace Events</CardTitle>
          <Activity className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.eventTypeCounts['TraceEvent'] || 0}</div>
          <div className="mt-1 flex space-x-2">
            {Object.entries(stats.traceStatuses || {}).map(([status, count]) => (
              <span 
                key={status} 
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                  ${status === 'success' || status === 'OK' ? 'bg-green-100 text-green-800' : 
                    status === 'error' ? 'bg-red-100 text-red-800' : 
                    'bg-gray-100 text-gray-800'}`}
              >
                {status}: {count}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Metric Events</CardTitle>
          <Gauge className="h-4 w-4 text-yellow-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.eventTypeCounts['MetricEvent'] || 0}</div>
          <p className="text-xs text-muted-foreground">
            {stats.eventTypeCounts['MetricEvent'] 
              ? `${((stats.eventTypeCounts['MetricEvent'] / stats.totalEvents) * 100).toFixed(1)}% of total events`
              : 'No metric events found'
            }
          </p>
        </CardContent>
      </Card>
      
      {/* Component Distribution */}
      <Card className="md:col-span-2">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Components</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {stats.components.map(component => (
              <div 
                key={component} 
                className="px-2 py-1 bg-blue-50 rounded-lg text-xs font-medium text-blue-700"
              >
                {component}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      
      {/* Top Trace Durations */}
      <Card className="md:col-span-2">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Top Trace Durations</CardTitle>
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(stats.avgTraceDurations || {})
              .sort((a, b) => b[1] - a[1])
              .slice(0, 5)
              .map(([name, duration]) => (
                <div key={name} className="flex items-center text-sm">
                  <div className="w-48 truncate" title={name}>{name}</div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${Math.min(100, (duration / 1000) * 100)}%` }}
                    ></div>
                  </div>
                  <div className="ml-2 text-xs text-gray-500">{duration.toFixed(2)} ms</div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};