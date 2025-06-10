import React, { useState, useEffect } from 'react';
import { RefreshCw, Eye, Calendar, Hash, Tag, Code, Trash2 } from 'lucide-react';

interface IngestMappingData {
  fingerprint: string;
  publisher: string;
  event_name: string;
  mapping_expr: string;
  event_field_expr?: string;
  structure: any;
  created_at: string;
  updated_at?: string;
}

interface IngestMappingListResponse {
  mappings: IngestMappingData[];
  total: number;
  page: number;
  size: number;
}

const IngestMapping: React.FC = () => {
  const [mappings, setMappings] = useState<IngestMappingData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMapping, setSelectedMapping] = useState<IngestMappingData | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalMappings, setTotalMappings] = useState(0);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);
  const pageSize = 20;

  const loadMappings = async (page: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/subscriptions/ingest-mappings?page=${page}&size=${pageSize}`);
      if (response.ok) {
        const data: IngestMappingListResponse = await response.json();
        setMappings(data.mappings);
        setTotalMappings(data.total);
        setCurrentPage(page);
      } else {
        throw new Error(`Failed to load ingest mappings: ${response.statusText}`);
      }
    } catch (err) {
      console.error("Error loading ingest mappings:", err);
      setError(err instanceof Error ? err.message : "Failed to load ingest mappings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMappings();
  }, []);

  const totalPages = Math.ceil(totalMappings / pageSize);

  const handleViewDetails = (mapping: IngestMappingData) => {
    setSelectedMapping(mapping);
    setShowDetails(true);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const truncateFingerprint = (fingerprint: string) => {
    return `${fingerprint.slice(0, 8)}...${fingerprint.slice(-8)}`;
  };

  const formatStructure = (structure: any) => {
    return JSON.stringify(structure, null, 2);
  };

  const deleteMapping = async (fingerprint: string) => {
    setDeleteLoading(fingerprint);
    setDeleteError(null);
    setDeleteSuccess(null);

    try {
      const response = await fetch(`/subscriptions/ingest-mappings/${encodeURIComponent(fingerprint)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete ingest mapping' }));
        throw new Error(errorData.detail || 'Failed to delete ingest mapping');
      }

      setDeleteSuccess(`Ingest mapping ${fingerprint.slice(0, 8)}... deleted successfully`);
      await loadMappings(currentPage); // Refresh the mappings list

    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete ingest mapping');
    } finally {
      setDeleteLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-800">Ingest Mapping</h2>
          <p className="text-gray-600 mt-1">
            View and manage payload structure mappings for event transformation
          </p>
        </div>
        <button
          onClick={() => loadMappings(currentPage)}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          <p className="font-medium">Error loading ingest mappings</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Delete Error */}
      {deleteError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          <p className="font-medium">Error deleting ingest mapping</p>
          <p className="text-sm mt-1">{deleteError}</p>
        </div>
      )}

      {/* Delete Success */}
      {deleteSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
          <p className="font-medium">{deleteSuccess}</p>
        </div>
      )}

      {/* Mappings List */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-800">Mappings ({totalMappings})</h3>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => loadMappings(currentPage - 1)}
                  disabled={currentPage <= 1 || loading}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded disabled:opacity-50 hover:bg-gray-200"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-600">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => loadMappings(currentPage + 1)}
                  disabled={currentPage >= totalPages || loading}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded disabled:opacity-50 hover:bg-gray-200"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>

        {loading && mappings.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
            Loading ingest mappings...
          </div>
        ) : mappings.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            <Code className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="text-lg font-medium">No ingest mappings found</p>
            <p className="text-sm">Mappings will appear here after webhook events are processed</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {mappings.map((mapping) => (
              <div key={mapping.fingerprint} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <Hash className="h-4 w-4 text-gray-400" />
                        <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                          {truncateFingerprint(mapping.fingerprint)}
                        </code>
                      </div>
                      <div className="flex items-center gap-2">
                        <Tag className="h-4 w-4 text-blue-500" />
                        <span className="text-sm font-medium text-blue-600">{mapping.publisher}</span>
                      </div>
                    </div>
                    
                    <h4 className="text-lg font-medium text-gray-800 mb-1">
                      {mapping.event_name}
                    </h4>
                    
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        <span>Created {formatDate(mapping.created_at)}</span>
                      </div>
                      {mapping.updated_at && (
                        <div className="flex items-center gap-1">
                          <span>Updated {formatDate(mapping.updated_at)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleViewDetails(mapping)}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                    >
                      <Eye className="h-4 w-4" />
                      Details
                    </button>
                    <button
                      onClick={() => deleteMapping(mapping.fingerprint)}
                      disabled={deleteLoading === mapping.fingerprint}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title={`Delete mapping ${mapping.fingerprint.slice(0, 8)}...`}
                    >
                      {deleteLoading === mapping.fingerprint ? (
                        <div className="w-4 h-4 border-2 border-red-600/50 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Details Modal */}
      {showDetails && selectedMapping && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-xl font-semibold text-gray-800">Mapping Details</h3>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              <div className="space-y-6">
                {/* Basic Info */}
                <div>
                  <h4 className="text-lg font-medium text-gray-800 mb-3">Basic Information</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Fingerprint</label>
                      <code className="block text-sm font-mono bg-gray-100 p-2 rounded border break-all">
                        {selectedMapping.fingerprint}
                      </code>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Publisher</label>
                      <div className="text-sm bg-blue-50 text-blue-700 p-2 rounded border">
                        {selectedMapping.publisher}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Event Name</label>
                      <div className="text-sm bg-gray-50 p-2 rounded border">
                        {selectedMapping.event_name}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Created</label>
                      <div className="text-sm bg-gray-50 p-2 rounded border">
                        {formatDate(selectedMapping.created_at)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Structure */}
                <div>
                  <h4 className="text-lg font-medium text-gray-800 mb-3">Payload Structure</h4>
                  <div className="bg-gray-50 border rounded-lg p-4">
                    <pre className="text-sm font-mono text-gray-800 whitespace-pre-wrap overflow-x-auto">
                      {formatStructure(selectedMapping.structure)}
                    </pre>
                  </div>
                </div>

                {/* Mapping Expression */}
                <div>
                  <h4 className="text-lg font-medium text-gray-800 mb-3">JSONata Mapping Expression</h4>
                  <div className="bg-gray-900 text-green-400 border rounded-lg p-4">
                    <pre className="text-sm font-mono whitespace-pre-wrap overflow-x-auto">
                      {selectedMapping.mapping_expr}
                    </pre>
                  </div>
                </div>

                {/* Event Field Expression */}
                {selectedMapping.event_field_expr && (
                  <div>
                    <h4 className="text-lg font-medium text-gray-800 mb-3">Event Field JSONata Expression</h4>
                    <div className="bg-gray-900 text-yellow-400 border rounded-lg p-4">
                      <pre className="text-sm font-mono whitespace-pre-wrap overflow-x-auto">
                        {selectedMapping.event_field_expr}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IngestMapping;