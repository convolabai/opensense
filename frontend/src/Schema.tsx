import React, { useState, useEffect } from 'react';
import { BookOpen, ChevronDown, ChevronRight, RefreshCw, AlertTriangle, Trash2 } from 'lucide-react';

interface SchemaData {
  publishers: string[];
  resource_types: { [publisher: string]: string[] };
  actions: string[];
  publisher_resource_actions?: { [publisher: string]: { [resource_type: string]: string[] } };
}

const Schema: React.FC = () => {
  const [schemaData, setSchemaData] = useState<SchemaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPublishers, setExpandedPublishers] = useState<Set<string>>(new Set());
  const [deleteLoading, setDeleteLoading] = useState<{
    type: 'publisher' | 'resource_type' | 'action';
    publisher?: string;
    resource_type?: string;
    action?: string;
  } | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);

  const loadSchema = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/schema/');
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

  const deletePublisher = async (publisher: string) => {
    if (!window.confirm(`Are you sure you want to delete all schema entries for publisher "${publisher}"? This action cannot be undone.`)) {
      return;
    }

    setDeleteLoading({ type: 'publisher', publisher });
    setDeleteError(null);
    setDeleteSuccess(null);

    try {
      const response = await fetch(`/schema/publishers/${encodeURIComponent(publisher)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete publisher' }));
        throw new Error(errorData.detail || 'Failed to delete publisher');
      }

      setDeleteSuccess(`Publisher "${publisher}" deleted successfully`);
      await loadSchema(); // Refresh the schema data

    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete publisher');
    } finally {
      setDeleteLoading(null);
    }
  };

  const deleteResourceType = async (publisher: string, resourceType: string) => {
    if (!window.confirm(`Are you sure you want to delete all schema entries for resource type "${resourceType}" under publisher "${publisher}"? This action cannot be undone.`)) {
      return;
    }

    setDeleteLoading({ type: 'resource_type', publisher, resource_type: resourceType });
    setDeleteError(null);
    setDeleteSuccess(null);

    try {
      const response = await fetch(`/schema/publishers/${encodeURIComponent(publisher)}/resource-types/${encodeURIComponent(resourceType)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete resource type' }));
        throw new Error(errorData.detail || 'Failed to delete resource type');
      }

      setDeleteSuccess(`Resource type "${resourceType}" deleted successfully`);
      await loadSchema(); // Refresh the schema data

    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete resource type');
    } finally {
      setDeleteLoading(null);
    }
  };

  const deleteAction = async (publisher: string, resourceType: string, action: string) => {
    if (!window.confirm(`Are you sure you want to delete action "${action}" for publisher "${publisher}" and resource type "${resourceType}"? This action cannot be undone.`)) {
      return;
    }

    setDeleteLoading({ type: 'action', publisher, resource_type: resourceType, action });
    setDeleteError(null);
    setDeleteSuccess(null);

    try {
      const response = await fetch(`/schema/publishers/${encodeURIComponent(publisher)}/resource-types/${encodeURIComponent(resourceType)}/actions/${encodeURIComponent(action)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete action' }));
        throw new Error(errorData.detail || 'Failed to delete action');
      }

      setDeleteSuccess(`Action "${action}" deleted successfully`);
      await loadSchema(); // Refresh the schema data

    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete action');
    } finally {
      setDeleteLoading(null);
    }
  };

  const isDeleteLoading = (type: string, publisher?: string, resourceType?: string, action?: string) => {
    if (!deleteLoading) return false;
    if (deleteLoading.type !== type) return false;
    if (publisher && deleteLoading.publisher !== publisher) return false;
    if (resourceType && deleteLoading.resource_type !== resourceType) return false;
    if (action && deleteLoading.action !== action) return false;
    return true;
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
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 mb-4">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {deleteError && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 mb-4">
          <AlertTriangle size={20} />
          <span>{deleteError}</span>
        </div>
      )}

      {deleteSuccess && (
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800 mb-4">
          <div className="w-5 h-5 bg-green-600 rounded-full flex items-center justify-center">
            <div className="w-2 h-2 bg-white rounded-full"></div>
          </div>
          <span>{deleteSuccess}</span>
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
                <div className="flex items-center justify-between p-4">
                  <button
                    onClick={() => togglePublisher(publisher)}
                    className="flex-1 flex items-center gap-3 text-left hover:bg-gray-50 transition-colors duration-150 ease-in-out rounded"
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
                  
                  <button
                    onClick={() => deletePublisher(publisher)}
                    disabled={isDeleteLoading('publisher', publisher)}
                    className="ml-2 p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={`Delete publisher "${publisher}"`}
                  >
                    {isDeleteLoading('publisher', publisher) ? (
                      <div className="w-4 h-4 border-2 border-red-600/50 border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50">
                    {resourceTypes.map((resourceType) => {
                      // Get actions for this specific publisher/resource_type combination
                      const relevantActions = schemaData.publisher_resource_actions?.[publisher]?.[resourceType] 
                        || schemaData.actions; // Fallback to all actions if granular data not available
                      
                      return (
                        <div key={resourceType} className="p-4 border-b border-gray-200 last:border-b-0">
                          <div className="flex items-center justify-between mb-2">
                            <div className="font-medium text-gray-700 flex items-center gap-2">
                              <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                              {resourceType}
                            </div>
                            <button
                              onClick={() => deleteResourceType(publisher, resourceType)}
                              disabled={isDeleteLoading('resource_type', publisher, resourceType)}
                              className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title={`Delete resource type "${resourceType}"`}
                            >
                              {isDeleteLoading('resource_type', publisher, resourceType) ? (
                                <div className="w-3 h-3 border-2 border-red-600/50 border-t-transparent rounded-full animate-spin" />
                              ) : (
                                <Trash2 size={12} />
                              )}
                            </button>
                          </div>
                          <div className="ml-4 flex flex-wrap gap-2">
                            {relevantActions.map((action) => (
                              <div
                                key={action}
                                className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-md group"
                              >
                                <span>{action}</span>
                                <button
                                  onClick={() => deleteAction(publisher, resourceType, action)}
                                  disabled={isDeleteLoading('action', publisher, resourceType, action)}
                                  className="ml-1 p-0.5 text-red-600 hover:text-red-800 opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                                  title={`Delete action "${action}"`}
                                >
                                  {isDeleteLoading('action', publisher, resourceType, action) ? (
                                    <div className="w-2 h-2 border border-red-600/50 border-t-transparent rounded-full animate-spin" />
                                  ) : (
                                    <Trash2 size={8} />
                                  )}
                                </button>
                              </div>
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