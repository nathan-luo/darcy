import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Clock, BarChart2, Activity } from 'lucide-react';

const LogVisualizer = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('timeline');
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await window.fs.readFile('paste.txt', { encoding: 'utf8' });
        const parsedLogs = JSON.parse(response);
        setLogs(parsedLogs);
        setLoading(false);
      } catch (err) {
        console.error('Error loading log data:', err);
        setError('Failed to load log data. Please check the console for details.');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64">Loading log data...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mt-4">
        <div className="flex">
          <AlertCircle className="h-5 w-5 mr-2" />
          <span>{error}</span>
        </div>
      </div>
    );
  }
  
  // Group logs by event type
  const eventTypes = {};
  logs.forEach(log => {
    if (!eventTypes[log.event_type]) {
      eventTypes[log.event_type] = [];
    }
    eventTypes[log.event_type].push(log);
  });
  
  // Extract command types for filtering
  const commandTypes = new Set();
  logs.forEach(log => {
    if (log.name && log.name.startsWith('command:')) {
      commandTypes.add(log.name.split(':')[1]);
    }
  });
  
  // Extract users for filtering
  const users = new Set();
  logs.forEach(log => {
    if (log.context && log.context.user_id) {
      users.add(log.context.user_id);
    }
  });
  
  // Calculate duration stats for spans
  const traceEvents = logs.filter(log => log.event_type === 'TraceEvent');
  const spanDurations = {};
  
  traceEvents.forEach(trace => {
    if (trace.end_time && trace.start_time) {
      const startTime = new Date(trace.start_time).getTime();
      const endTime = new Date(trace.end_time).getTime();
      const duration = endTime - startTime;
      
      if (!spanDurations[trace.name]) {
        spanDurations[trace.name] = [];
      }
      spanDurations[trace.name].push(duration);
    }
  });
  
  // Calculate avg durations
  const avgDurations = {};
  Object.keys(spanDurations).forEach(spanName => {
    const durations = spanDurations[spanName];
    const sum = durations.reduce((a, b) => a + b, 0);
    avgDurations[spanName] = sum / durations.length;
  });
  
  return (
    <div className="container mx-auto p-4">
      <Card className="mb-6">
        <CardHeader className="bg-blue-50">
          <CardTitle className="text-xl">LLMgine Log Visualizer</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="text-sm text-gray-600 mb-2">
            Total logs: {logs.length} | Time range: {new Date(logs[0].timestamp).toLocaleTimeString()} - {new Date(logs[logs.length-1].timestamp).toLocaleTimeString()}
          </div>
          
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded shadow">
              <div className="text-sm text-gray-600">Log Events</div>
              <div className="text-2xl font-bold">{eventTypes['LogEvent'] ? eventTypes['LogEvent'].length : 0}</div>
            </div>
            <div className="bg-green-50 p-4 rounded shadow">
              <div className="text-sm text-gray-600">Trace Events</div>
              <div className="text-2xl font-bold">{eventTypes['TraceEvent'] ? eventTypes['TraceEvent'].length : 0}</div>
            </div>
            <div className="bg-yellow-50 p-4 rounded shadow">
              <div className="text-sm text-gray-600">Metric Events</div>
              <div className="text-2xl font-bold">{eventTypes['MetricEvent'] ? eventTypes['MetricEvent'].length : 0}</div>
            </div>
            <div className="bg-purple-50 p-4 rounded shadow">
              <div className="text-sm text-gray-600">Commands</div>
              <div className="text-2xl font-bold">{commandTypes.size}</div>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Tabs defaultValue="timeline" className="w-full" value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-4 mb-4">
          <TabsTrigger value="timeline" className="flex items-center">
            <Clock className="h-4 w-4 mr-2" />
            Timeline
          </TabsTrigger>
          <TabsTrigger value="traces" className="flex items-center">
            <Activity className="h-4 w-4 mr-2" />
            Traces
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center">
            <BarChart2 className="h-4 w-4 mr-2" />
            User Activity
          </TabsTrigger>
          <TabsTrigger value="errors" className="flex items-center">
            <AlertCircle className="h-4 w-4 mr-2" />
            Errors
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="timeline" className="border rounded-md p-4">
          <h3 className="text-lg font-medium mb-4">Event Timeline</h3>
          <div className="space-y-2">
            {logs.slice(0, 20).map((log, index) => (
              <div key={index} className={`p-2 rounded text-sm ${
                log.level === 'ERROR' ? 'bg-red-50 border-l-4 border-red-500' : 
                log.level === 'DEBUG' ? 'bg-gray-50' : 
                log.level === 'INFO' ? 'bg-blue-50' : 
                log.event_type === 'TraceEvent' ? 'bg-green-50' :
                log.event_type === 'MetricEvent' ? 'bg-yellow-50' : 'bg-white border'
              }`}>
                <div className="flex justify-between">
                  <span className="font-mono text-xs">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className="font-medium">{log.event_type}{log.level ? ` - ${log.level}` : ''}</span>
                </div>
                <div>{log.message || log.name || (log.metrics && 'Metric: ' + log.metrics[0]?.name)}</div>
                {log.context && Object.keys(log.context).length > 0 && (
                  <div className="text-xs text-gray-600 mt-1">
                    Context: {Object.entries(log.context).map(([k, v]) => `${k}=${v}`).join(', ')}
                  </div>
                )}
              </div>
            ))}
            {logs.length > 20 && (
              <div className="text-center text-gray-500 text-sm py-2">
                Showing 20 of {logs.length} events. Full visualization would require additional implementation.
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="traces" className="border rounded-md p-4">
          <h3 className="text-lg font-medium mb-4">Trace Analysis</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-md">Trace Duration by Operation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.keys(avgDurations).map((spanName, idx) => (
                    <div key={idx} className="flex items-center">
                      <div className="w-48 truncate">{spanName}</div>
                      <div className="w-full bg-gray-200 rounded-full h-4">
                        <div 
                          className="bg-blue-600 h-4 rounded-full" 
                          style={{ width: `${Math.min(100, (avgDurations[spanName] / 10) * 100)}%` }}
                        ></div>
                      </div>
                      <div className="ml-2 text-sm">{avgDurations[spanName].toFixed(2)} ms</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-md">Trace Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div>
                  {['success', 'error', 'OK'].map(status => {
                    const count = traceEvents.filter(t => t.status === status).length;
                    const percentage = (count / traceEvents.length * 100).toFixed(1);
                    return (
                      <div key={status} className="mb-2">
                        <div className="flex justify-between mb-1">
                          <span className="capitalize">{status}</span>
                          <span>{count} ({percentage}%)</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-4">
                          <div 
                            className={`h-4 rounded-full ${
                              status === 'success' ? 'bg-green-500' : 
                              status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                            }`} 
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="users" className="border rounded-md p-4">
          <h3 className="text-lg font-medium mb-4">User Activity</h3>
          
          <div className="grid grid-cols-1 gap-4">
            {Array.from(users).map(userId => {
              const userLogs = logs.filter(log => 
                log.context && log.context.user_id === userId
              );
              
              const userRegistration = userLogs.find(log => 
                log.message && log.message.includes('registered')
              );
              
              const userGreeting = userLogs.find(log => 
                log.message && log.message.includes('greeted')
              );
              
              const emailSuccess = userLogs.some(log => 
                log.attributes && log.attributes.operation === 'send_email' && 
                log.status === 'success'
              );
              
              return (
                <Card key={userId} className="mb-4">
                  <CardHeader className="pb-2 bg-gray-50">
                    <CardTitle className="text-md">{userId}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {userRegistration && (
                        <div className="text-sm">{userRegistration.message}</div>
                      )}
                      {userGreeting && (
                        <div className="text-sm">{userGreeting.message}</div>
                      )}
                      <div className="flex mt-2">
                        <div className={`px-2 py-1 rounded text-xs mr-2 ${
                          userRegistration ? 'bg-green-100 text-green-800' : 'bg-gray-100'
                        }`}>
                          Registration
                        </div>
                        <div className={`px-2 py-1 rounded text-xs mr-2 ${
                          userGreeting ? 'bg-green-100 text-green-800' : 'bg-gray-100'
                        }`}>
                          Greeting
                        </div>
                        <div className={`px-2 py-1 rounded text-xs ${
                          emailSuccess ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          Email
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
        
        <TabsContent value="errors" className="border rounded-md p-4">
          <h3 className="text-lg font-medium mb-4">Errors & Warnings</h3>
          
          <div className="space-y-3">
            {logs.filter(log => log.level === 'ERROR' || log.status === 'error').map((log, idx) => (
              <div key={idx} className="bg-red-50 border-l-4 border-red-500 p-3 rounded">
                <div className="font-medium">{log.message || `Error in ${log.name}`}</div>
                <div className="text-xs text-gray-700 mt-1">
                  Time: {new Date(log.timestamp).toLocaleTimeString()}
                </div>
                {log.context && Object.keys(log.context).length > 0 && (
                  <div className="text-xs text-gray-600 mt-1">
                    Context: {Object.entries(log.context).map(([k, v]) => `${k}=${v}`).join(', ')}
                  </div>
                )}
                {log.attributes && Object.keys(log.attributes).length > 0 && (
                  <div className="text-xs text-gray-600 mt-1">
                    Attributes: {Object.entries(log.attributes).map(([k, v]) => `${k}=${v}`).join(', ')}
                  </div>
                )}
              </div>
            ))}
            
            {logs.filter(log => log.level === 'ERROR' || log.status === 'error').length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No errors found in the log data
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default LogVisualizer;