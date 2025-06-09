import React, { useState, useEffect } from 'react';

import { Send, ListChecks, Eye, RefreshCw, X } from 'lucide-react';
import { samplePayloads, payloadCategories } from './sampleWebhookPayloads';

interface EventLog {
  id: number;
  event_id: string;
  source: string;
  subject: string;
  publisher: string;
  resource_type: string;
  resource_id: string;
  action: string;
  canonical_data: any;
  raw_payload?: any;
  timestamp: string;
  logged_at: string;
}

interface EventLogListResponse {
  event_logs: EventLog[];
  total: number;
  page: number;
  size: number;
}

// Copied from App.tsx (assuming Subscription type is needed for checkSubscriptionMatches)
interface Subscription {
  id: number;
  subscriber_id: string;
  description: string;
  pattern: string;
  channel_type: string;
  channel_config: any;
  active: boolean;
  created_at: string;
  updated_at?: string;
}

interface EventsProps {
  subscriptions: Subscription[]; // Passed from App.tsx
}

const Events: React.FC<EventsProps> = ({ subscriptions }) => {
  const [selectedPayload, setSelectedPayload] = useState<string>('github_pr_opened');
  const [inputPayload, setInputPayload] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  
  // Event logs state
  const [eventLogs, setEventLogs] = useState<EventLog[]>([]);
  const [eventLogsLoading, setEventLogsLoading] = useState(false);
  const [eventLogsError, setEventLogsError] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalEventLogs, setTotalEventLogs] = useState(0);
  const [selectedEventLog, setSelectedEventLog] = useState<EventLog | null>(null);
  const [showEventModal, setShowEventModal] = useState(false);
  
  const pageSize = 20;


  useEffect(() => {
    const sample = samplePayloads[selectedPayload as keyof typeof samplePayloads];
    if (sample) {
      setInputPayload(JSON.stringify(sample.payload, null, 2));
    }
  }, [selectedPayload]);

  useEffect(() => {
    loadEventLogs();
  }, [currentPage]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadEventLogs = async () => {
    setEventLogsLoading(true);
    setEventLogsError('');
    try {
      const response = await fetch(`/event-logs?page=${currentPage}&size=${pageSize}`);
      if (!response.ok) {
        throw new Error('Failed to fetch event logs');
      }
      const data: EventLogListResponse = await response.json();
      setEventLogs(data.event_logs);
      setTotalEventLogs(data.total);
    } catch (err) {
      setEventLogsError(err instanceof Error ? err.message : 'Failed to fetch event logs');
    } finally {
      setEventLogsLoading(false);
    }
  };

  const sendWebhook = async () => {
    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      let payload;
      try { payload = JSON.parse(inputPayload); }
      catch (e) { throw new Error('Invalid JSON payload'); }

      const selectedSample = samplePayloads[selectedPayload as keyof typeof samplePayloads];
      const source = selectedSample?.source || 'github';

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (source === 'github') { headers['X-GitHub-Event'] = 'pull_request'; }

      const response = await fetch(`/ingest/${source}`, { method: 'POST', headers, body: JSON.stringify(payload) });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send webhook');
      }

      const result = await response.json();
      setSuccess(`Event accepted with ID: ${result.request_id}`);
      // Refresh event logs to show the new event
      loadEventLogs();

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const openEventModal = (eventLog: EventLog) => {
    setSelectedEventLog(eventLog);
    setShowEventModal(true);
  };

  const closeEventModal = () => {
    setShowEventModal(false);
    setSelectedEventLog(null);
  };

  const totalPages = Math.ceil(totalEventLogs / pageSize);

  const EventDetailModal = () => {
    if (!selectedEventLog) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
          <div className="flex justify-between items-center p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-800">Event Details</h2>
            <button
              onClick={closeEventModal}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={24} />
            </button>
          </div>
          
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Event Information</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="font-medium">Event ID:</span> {selectedEventLog.event_id}</div>
                  <div><span className="font-medium">Source:</span> {selectedEventLog.source}</div>
                  <div><span className="font-medium">Publisher:</span> {selectedEventLog.publisher}</div>
                  <div><span className="font-medium">Resource Type:</span> {selectedEventLog.resource_type}</div>
                  <div><span className="font-medium">Resource ID:</span> {selectedEventLog.resource_id}</div>
                  <div><span className="font-medium">Action:</span> {selectedEventLog.action}</div>
                </div>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Timestamps</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="font-medium">Event Time:</span> {formatTimestamp(selectedEventLog.timestamp)}</div>
                  <div><span className="font-medium">Logged At:</span> {formatTimestamp(selectedEventLog.logged_at)}</div>
                  <div><span className="font-medium">Subject:</span> {selectedEventLog.subject}</div>
                </div>
              </div>
            </div>

            {/* Side-by-side Raw and Canonical Payloads */}
            <div className="flex flex-col md:flex-row gap-6">
              <div className="w-full md:w-1/2">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Raw Payload</h3>
                <div className="bg-gray-800 text-gray-200 p-4 rounded-md font-mono text-sm overflow-x-auto max-h-60 md:max-h-[50vh]">
                  <pre>{JSON.stringify(selectedEventLog.raw_payload ?? {}, null, 2)}</pre>
                </div>
              </div>
              <div className="w-full md:w-1/2">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Canonical Data</h3>
                <div className="bg-gray-800 text-gray-200 p-4 rounded-md font-mono text-sm overflow-x-auto max-h-60 md:max-h-[50vh]">
                  <pre>{JSON.stringify(selectedEventLog.canonical_data, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      {/* Event Creation Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
          <Send size={24} className="text-blue-600" />
          Create New Event
        </h2>
        
        <div className="grid grid-cols-1 gap-8">
          {/* Input Section */}
          <div>
            <h3 className="text-lg font-medium text-gray-800 mb-4">Webhook Input</h3>
            
            <div className="mb-4">
              <label htmlFor="webhook-type" className="block text-sm font-medium text-gray-500 mb-2">Webhook Event Type:</label>
              <select
                id="webhook-type"
                value={selectedPayload}
                onChange={(e) => setSelectedPayload(e.target.value)}
                className="w-full bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 transition-colors text-sm"
              >
                {Object.entries(payloadCategories).map(([category, payloadKeys]) => (
                  <optgroup key={category} label={category}>
                    {payloadKeys.map((key) => (
                      <option key={key} value={key}>
                        {samplePayloads[key]?.name.replace(`${category} - `, '') || key}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            <textarea
              className="w-full min-h-[200px] bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm transition-colors"
              value={inputPayload}
              onChange={(e) => setInputPayload(e.target.value)}
              placeholder="Enter webhook payload JSON..."
            />

            <div className="flex flex-col sm:flex-row gap-4 mt-4">
              <button
                className="flex-1 py-2 px-4 rounded-md font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={sendWebhook}
                disabled={isLoading || !inputPayload.trim()}
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-white/50 border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </span>
                ) : ( <> <Send size={16} /> Send Webhook </> )}
              </button>
            </div>
          </div>
        </div>

        {error && <div className="p-4 rounded-md mt-6 text-sm bg-red-100 border border-red-400 text-red-700">{error}</div>}
        {success && <div className="p-4 rounded-md mt-6 text-sm bg-green-100 border border-green-400 text-green-700">{success}</div>}
      </div>

      {/* Event Logs Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="flex items-center gap-3 text-xl font-semibold text-gray-800 tracking-tight">
            <ListChecks size={24} className="text-blue-600" />
            Event Logs
          </h2>
          <button
            onClick={loadEventLogs}
            disabled={eventLogsLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={eventLogsLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {eventLogsError && (
          <div className="p-4 rounded-md mb-6 text-sm bg-red-100 border border-red-400 text-red-700">
            {eventLogsError}
          </div>
        )}

        {eventLogsLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-gray-600">Loading event logs...</span>
          </div>
        ) : eventLogs.length > 0 ? (
          <div className="space-y-4">
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Event</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Publisher</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resource</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {eventLogs.map((eventLog) => (
                    <tr key={eventLog.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <div className="font-medium">{eventLog.event_id}</div>
                        <div className="text-gray-500 text-xs">{eventLog.source}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">{eventLog.publisher}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <div>{eventLog.resource_type}</div>
                        <div className="text-gray-500 text-xs">{eventLog.resource_id}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {eventLog.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {formatTimestamp(eventLog.timestamp)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <button
                          onClick={() => openEventModal(eventLog)}
                          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700 font-medium"
                        >
                          <Eye size={14} />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <div className="text-sm text-gray-500">
                  Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalEventLogs)} of {totalEventLogs} events
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-2 text-sm font-medium text-gray-700">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8 sm:py-12 text-base">No event logs found.</p>
        )}
      </div>

      {/* Event Detail Modal */}
      {showEventModal && <EventDetailModal />}
    </div>
  );
};

export default Events;
