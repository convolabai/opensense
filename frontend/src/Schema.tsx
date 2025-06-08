import React, { useState, useEffect } from 'react';
import { BookOpen, ChevronDown, ChevronRight, RefreshCw, AlertTriangle } from 'lucide-react';

interface SchemaData {
  publishers: string[];
  resource_types: { [publisher: string]: string[] };
  actions: string[];
}

const Schema: React.FC = () => {
  const [schemaData, setSchemaData] = useState<SchemaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPublishers, setExpandedPublishers] = useState<Set<string>>(new Set());

  const loadSchema = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/schema');
      if (response.ok) {
        const data = await response.json();
        setSchemaData(data);
      } else {
        setError(`Failed to load schema: ${response.status}`);
      }
    } catch (err) {
      setError('Error loading schema data');
      console.error("Error loading schema:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSchema();
  }, []);

  const togglePublisher = (publisher: string) => {
    const newExpanded = new Set(expandedPublishers);
    if (newExpanded.has(publisher)) {
      newExpanded.delete(publisher);
    } else {
      newExpanded.add(publisher);
    }
    setExpandedPublishers(newExpanded);
  };

  const isEmpty = schemaData && schemaData.publishers.length === 0;

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
      <h2 className="flex items-center gap-3 text-xl sm:text-2xl font-semibold mb-6 text-gray-800 tracking-tight">
        <BookOpen size={24} className="text-blue-600" />
        Canonical Event Schema
        <button
          className="ml-auto py-1 px-3 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm text-xs"
          onClick={loadSchema}
          disabled={loading}
          aria-label="Refresh schema"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
        </button>
      </h2>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw size={32} className="animate-spin text-blue-600" />
          <span className="ml-3 text-gray-600">Loading schema...</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {isEmpty && !loading && !error && (
        <div className="text-center py-12">
          <BookOpen size={64} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">No Schema Data Available</h3>
          <p className="text-gray-600 max-w-md mx-auto">
            No publishers, resource types, or actions have been discovered yet. 
            Send some webhook events to populate the schema registry.
          </p>
        </div>
      )}

      {schemaData && !isEmpty && !loading && (
        <div className="space-y-4">
          {schemaData.publishers.map((publisher) => {
            const isExpanded = expandedPublishers.has(publisher);
            const resourceTypes = schemaData.resource_types[publisher] || [];
            
            return (
              <div key={publisher} className="border border-gray-200 rounded-lg">
                <button
                  onClick={() => togglePublisher(publisher)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors duration-150 ease-in-out"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown size={20} className="text-gray-400" />
                    ) : (
                      <ChevronRight size={20} className="text-gray-400" />
                    )}
                    <span className="font-semibold text-gray-800 text-lg">
                      Publisher: {publisher}
                    </span>
                  </div>
                  <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                    {resourceTypes.length} resource{resourceTypes.length !== 1 ? 's' : ''}
                  </span>
                </button>

                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50">
                    {resourceTypes.map((resourceType) => {
                      // Get actions for this specific publisher/resource_type combination
                      // Since the API doesn't provide this granular breakdown, we'll show all actions
                      const relevantActions = schemaData.actions;
                      
                      return (
                        <div key={resourceType} className="p-4 border-b border-gray-200 last:border-b-0">
                          <div className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                            {resourceType}
                          </div>
                          <div className="ml-4 flex flex-wrap gap-2">
                            {relevantActions.map((action) => (
                              <span
                                key={action}
                                className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-md"
                              >
                                {action}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Schema;