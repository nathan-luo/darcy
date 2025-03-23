import React, { useState, useEffect } from 'react';
import { LLMgineEvent, MetricEvent } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';

interface MetricsViewProps {
  events: LLMgineEvent[];
}

interface MetricData {
  name: string;
  unit: string | null;
  values: {
    timestamp: number;
    value: number;
  }[];
  min: number;
  max: number;
  avg: number;
}

export const MetricsView: React.FC<MetricsViewProps> = ({ events }) => {
  const [metrics, setMetrics] = useState<Record<string, MetricData>>({});
  
  useEffect(() => {
    // Extract and organize metrics
    const metricEvents = events.filter((event): event is MetricEvent => 
      event.event_type === 'MetricEvent'
    );
    
    const metricsMap: Record<string, MetricData> = {};
    
    metricEvents.forEach(event => {
      event.metrics.forEach(metric => {
        const metricName = metric.name;
        
        if (!metricsMap[metricName]) {
          metricsMap[metricName] = {
            name: metricName,
            unit: metric.unit || null,
            values: [],
            min: Number.MAX_VALUE,
            max: Number.MIN_VALUE,
            avg: 0
          };
        }
        
        const timestamp = new Date(event.timestamp).getTime();
        metricsMap[metricName].values.push({
          timestamp,
          value: metric.value
        });
        
        // Update min/max
        if (metric.value < metricsMap[metricName].min) {
          metricsMap[metricName].min = metric.value;
        }
        if (metric.value > metricsMap[metricName].max) {
          metricsMap[metricName].max = metric.value;
        }
      });
    });
    
    // Calculate averages and sort values by timestamp
    Object.values(metricsMap).forEach(metric => {
      // Sort by timestamp
      metric.values.sort((a, b) => a.timestamp - b.timestamp);
      
      // Calculate average
      const sum = metric.values.reduce((acc, curr) => acc + curr.value, 0);
      metric.avg = sum / metric.values.length;
    });
    
    setMetrics(metricsMap);
  }, [events]);
  
  if (Object.keys(metrics).length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No metric events found in the log data
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.values(metrics).map(metric => (
          <Card key={metric.name}>
            <CardHeader className="py-4">
              <CardTitle className="text-base font-medium">{metric.name}</CardTitle>
            </CardHeader>
            <CardContent className="py-0">
              <div className="flex justify-between text-sm mb-2">
                <div>
                  <span className="text-gray-500">Min:</span>{' '}
                  <span className="font-medium">{metric.min.toFixed(2)}</span>
                  {metric.unit && <span className="ml-1 text-gray-500">{metric.unit}</span>}
                </div>
                <div>
                  <span className="text-gray-500">Avg:</span>{' '}
                  <span className="font-medium">{metric.avg.toFixed(2)}</span>
                  {metric.unit && <span className="ml-1 text-gray-500">{metric.unit}</span>}
                </div>
                <div>
                  <span className="text-gray-500">Max:</span>{' '}
                  <span className="font-medium">{metric.max.toFixed(2)}</span>
                  {metric.unit && <span className="ml-1 text-gray-500">{metric.unit}</span>}
                </div>
              </div>
              
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  {metric.values.length > 1 ? (
                    <LineChart
                      data={metric.values.map(v => ({
                        timestamp: v.timestamp,
                        value: v.value
                      }))}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis 
                        dataKey="timestamp" 
                        type="number"
                        scale="time"
                        domain={['dataMin', 'dataMax']}
                        tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        tick={{ fontSize: 10 }}
                      />
                      <YAxis 
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 10 }}
                      />
                      <Tooltip 
                        labelFormatter={(label) => new Date(label).toLocaleString()}
                        formatter={(value: number) => [`${value}${metric.unit ? ` ${metric.unit}` : ''}`, metric.name]}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  ) : (
                    // If there's only one data point, use a bar chart
                    <BarChart
                      data={[{ name: metric.name, value: metric.values[0].value }]}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#3b82f6" barSize={40} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
              
              <div className="text-xs text-gray-500 mt-2">
                Data points: {metric.values.length}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};