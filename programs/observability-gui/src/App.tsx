import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Clock, Activity, BarChart2, FileText, RefreshCw } from 'lucide-react';
import { FilePicker } from '@/components/file-picker';
import { Dashboard } from '@/components/dashboard';
import { TimelineView } from '@/components/timeline-view';
import { TracesView } from '@/components/traces-view';
import { ErrorsView } from '@/components/errors-view';
import { MetricsView } from '@/components/metrics-view';
import { Filters } from '@/components/filters';
// import { Button } from '@/components/ui/button';
import { LLMgineEvent, StatsData } from '@/types';
import { parseLogFile, calculateStats, filterEvents } from '@/lib/utils';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [logFilePath, setLogFilePath] = useState<string | null>(null);
  const [events, setEvents] = useState<LLMgineEvent[]>([]);
  const [filteredEvents, setFilteredEvents] = useState<LLMgineEvent[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [_filters, setFilters] = useState<any>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  const handleFileSelect = (path: string, content: string) => {
    setIsLoading(true);
    setLogFilePath(path);
    
    try {
      const parsedEvents = parseLogFile(content);
      setEvents(parsedEvents);
      setFilteredEvents(parsedEvents);
      setStats(calculateStats(parsedEvents));
    } catch (error) {
      console.error('Error parsing log file:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleFilterChange = (newFilters: any) => {
    setFilters(newFilters);
    
    if (Object.keys(newFilters).length === 0) {
      // No filters, show all events
      setFilteredEvents(events);
    } else {
      // Apply filters
      const filtered = filterEvents(events, newFilters);
      setFilteredEvents(filtered);
    }
  };
  
  const fileName = logFilePath?.split('/').pop() || 'No file selected';
  
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-bold text-gray-900">
              LLMgine Log Visualizer
            </h1>
            <div className="text-sm text-gray-500">
              {logFilePath ? (
                <div className="flex items-center">
                  <FileText className="h-4 w-4 mr-1" />
                  {fileName}
                </div>
              ) : (
                'No file loaded'
              )}
            </div>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <FilePicker onFileSelect={handleFileSelect} />
            
            {events.length > 0 && (
              <Filters events={events} onFilterChange={handleFilterChange} />
            )}
          </div>
          
          <div className="md:col-span-2">
            {isLoading ? (
              <Card className="h-64">
                <CardContent className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center">
                    <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mb-4" />
                    <p className="text-gray-500">Loading log data...</p>
                  </div>
                </CardContent>
              </Card>
            ) : !logFilePath ? (
              <Card className="h-64">
                <CardContent className="flex items-center justify-center h-full">
                  <div className="text-center text-gray-500">
                    <p className="text-lg font-medium mb-2">No log file loaded</p>
                    <p className="text-sm">Select a log file to visualize</p>
                  </div>
                </CardContent>
              </Card>
            ) : events.length === 0 ? (
              <Card className="h-64">
                <CardContent className="flex items-center justify-center h-full">
                  <div className="text-center text-gray-500">
                    <p className="text-lg font-medium mb-2">No events found</p>
                    <p className="text-sm">The selected file contains no valid log events</p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <>
                <div className="mb-6">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">Log Analysis</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-sm text-gray-600 mb-4">
                        {filteredEvents.length === events.length ? (
                          <span>Showing all {events.length} events</span>
                        ) : (
                          <span>Showing {filteredEvents.length} of {events.length} events (filtered)</span>
                        )}
                      </div>
                      
                      {stats && <Dashboard stats={stats} />}
                    </CardContent>
                  </Card>
                </div>
                
                <Tabs defaultValue="timeline" value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid grid-cols-4 mb-4">
                    <TabsTrigger value="timeline" className="flex items-center text-xs md:text-sm">
                      <Clock className="h-4 w-4 mr-2" />
                      Timeline
                    </TabsTrigger>
                    <TabsTrigger value="traces" className="flex items-center text-xs md:text-sm">
                      <Activity className="h-4 w-4 mr-2" />
                      Traces
                    </TabsTrigger>
                    <TabsTrigger value="metrics" className="flex items-center text-xs md:text-sm">
                      <BarChart2 className="h-4 w-4 mr-2" />
                      Metrics
                    </TabsTrigger>
                    <TabsTrigger value="errors" className="flex items-center text-xs md:text-sm">
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Errors
                    </TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="timeline" className="border rounded-md p-4 bg-white">
                    <h3 className="text-lg font-medium mb-4">Event Timeline</h3>
                    <TimelineView events={filteredEvents} maxEvents={100} />
                  </TabsContent>
                  
                  <TabsContent value="traces" className="border rounded-md p-4 bg-white">
                    <h3 className="text-lg font-medium mb-4">Trace Analysis</h3>
                    <TracesView events={filteredEvents} />
                  </TabsContent>
                  
                  <TabsContent value="metrics" className="border rounded-md p-4 bg-white">
                    <h3 className="text-lg font-medium mb-4">Metrics Analysis</h3>
                    <MetricsView events={filteredEvents} />
                  </TabsContent>
                  
                  <TabsContent value="errors" className="border rounded-md p-4 bg-white">
                    <h3 className="text-lg font-medium mb-4">Errors & Warnings</h3>
                    <ErrorsView events={filteredEvents} />
                  </TabsContent>
                </Tabs>
              </>
            )}
          </div>
        </div>
      </main>
      
      <footer className="max-w-7xl mx-auto px-4 py-4 sm:px-6 border-t mt-auto">
        <div className="text-center text-sm text-gray-500">
          LLMgine Log Visualizer &copy; {new Date().getFullYear()}
        </div>
      </footer>
    </div>
  );
}

export default App;