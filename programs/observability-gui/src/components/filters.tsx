import React, { useState } from 'react';
import { Button } from './ui/button';
import { LLMgineEvent, LogLevel } from '@/types';

interface FiltersProps {
  events: LLMgineEvent[];
  onFilterChange: (filters: any) => void;
}

export const Filters: React.FC<FiltersProps> = ({ events, onFilterChange }) => {
  const [selectedLevels, setSelectedLevels] = useState<LogLevel[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedComponents, setSelectedComponents] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Extract available filters from events
  const availableLevels = new Set<LogLevel>();
  const availableComponents = new Set<string>();
  const availableTypes = new Set<string>();
  
  events.forEach(event => {
    availableTypes.add(event.event_type);
    
    if (event.event_type === 'LogEvent') {
      availableLevels.add(event.level);
      
      if (event.context && event.context.component) {
        availableComponents.add(event.context.component);
      }
    }
  });
  
  const handleLevelChange = (level: LogLevel) => {
    if (selectedLevels.includes(level)) {
      setSelectedLevels(selectedLevels.filter(l => l !== level));
    } else {
      setSelectedLevels([...selectedLevels, level]);
    }
  };
  
  const handleTypeChange = (type: string) => {
    if (selectedTypes.includes(type)) {
      setSelectedTypes(selectedTypes.filter(t => t !== type));
    } else {
      setSelectedTypes([...selectedTypes, type]);
    }
  };
  
  const handleComponentChange = (component: string) => {
    if (selectedComponents.includes(component)) {
      setSelectedComponents(selectedComponents.filter(c => c !== component));
    } else {
      setSelectedComponents([...selectedComponents, component]);
    }
  };
  
  const applyFilters = () => {
    onFilterChange({
      level: selectedLevels.length > 0 ? selectedLevels : undefined,
      eventType: selectedTypes.length > 0 ? selectedTypes : undefined,
      component: selectedComponents.length > 0 ? selectedComponents : undefined,
      query: searchQuery.trim() || undefined,
    });
  };
  
  const clearFilters = () => {
    setSelectedLevels([]);
    setSelectedTypes([]);
    setSelectedComponents([]);
    setSearchQuery('');
    
    onFilterChange({});
  };
  
  const getLogLevelColor = (level: LogLevel): string => {
    switch (level) {
      case 'DEBUG': return 'bg-gray-100 text-gray-800';
      case 'INFO': return 'bg-blue-100 text-blue-800';
      case 'WARNING': return 'bg-yellow-100 text-yellow-800';
      case 'ERROR': return 'bg-red-100 text-red-800';
      case 'CRITICAL': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  const getEventTypeColor = (type: string): string => {
    switch (type) {
      case 'LogEvent': return 'bg-blue-50 text-blue-800';
      case 'TraceEvent': return 'bg-green-50 text-green-800';
      case 'MetricEvent': return 'bg-yellow-50 text-yellow-800';
      default: return 'bg-gray-50 text-gray-800';
    }
  };
  
  return (
    <div className="p-4 border rounded-lg bg-white mb-4">
      <h3 className="text-lg font-medium mb-4">Filters</h3>
      
      <div className="space-y-4">
        {/* Search */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Search
          </label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 border rounded-md text-sm"
            placeholder="Search in logs..."
          />
        </div>
        
        {/* Log Levels */}
        {Array.from(availableLevels).length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-1">
              Log Levels
            </label>
            <div className="flex flex-wrap gap-2">
              {Array.from(availableLevels).map(level => (
                <button
                  key={level}
                  onClick={() => handleLevelChange(level)}
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    selectedLevels.includes(level)
                      ? getLogLevelColor(level)
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Event Types */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Event Types
          </label>
          <div className="flex flex-wrap gap-2">
            {Array.from(availableTypes).map(type => (
              <button
                key={type}
                onClick={() => handleTypeChange(type)}
                className={`px-2 py-1 rounded-full text-xs font-medium ${
                  selectedTypes.includes(type)
                    ? getEventTypeColor(type)
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
        
        {/* Components */}
        {Array.from(availableComponents).length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-1">
              Components
            </label>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
              {Array.from(availableComponents).map(component => (
                <button
                  key={component}
                  onClick={() => handleComponentChange(component)}
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    selectedComponents.includes(component)
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {component}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="flex space-x-2 pt-2">
          <Button
            variant="default"
            onClick={applyFilters}
            size="sm"
          >
            Apply Filters
          </Button>
          <Button
            variant="outline"
            onClick={clearFilters}
            size="sm"
          >
            Clear
          </Button>
        </div>
      </div>
    </div>
  );
};