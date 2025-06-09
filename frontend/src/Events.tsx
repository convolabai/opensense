import React, { useState, useEffect } from 'react';

import { Send, Zap, ListChecks, Bell, Eye, RefreshCw, X } from 'lucide-react';

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

// Copied from App.tsx
interface CanonicalEvent {
  publisher: string;
  resource: {
    type: string;
    id: string | number;
  };
  action: string;
  timestamp: string;
  summary?: string;
  raw: any;
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

const samplePayloads = {
  github: {
    name: "GitHub PR Opened",
    payload: {
      action: "opened",
      pull_request: { number: 1374, title: "Add new feature", state: "open", user: { login: "alice" } },
      repository: { name: "test-repo", id: 12345 }
    }
  },
  stripe: {
    name: "Stripe Payment Succeeded",
    payload: {
      type: "payment_intent.succeeded",
      data: { object: { id: "pi_3OrFAb47K1Z2xQ8C0123", amount: 2000, currency: "usd", status: "succeeded" } }
    }
  },
  slack: {
    name: "Slack File Shared",
    payload: {
      type: "file_shared",
      file: { id: "F06A2G45T", name: "design.png", channels: ["C123456"] },
      user_id: "U123456"
    }
  }
};

interface EventsProps {
  subscriptions: Subscription[]; // Passed from App.tsx
}

const Events: React.FC<EventsProps> = ({ subscriptions }) => {
  const [selectedSource, setSelectedSource] = useState<string>('github');
  const [inputPayload, setInputPayload] = useState<string>('');
  const [outputEvent, setOutputEvent] = useState<CanonicalEvent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [matchedSubscriptions, setMatchedSubscriptions] = useState<Subscription[]>([]);
  
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
    const sample = samplePayloads[selectedSource as keyof typeof samplePayloads];
    if (sample) {
      setInputPayload(JSON.stringify(sample.payload, null, 2));
    }
  }, [selectedSource]);

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

  const checkSubscriptionMatches = (event: CanonicalEvent) => {
    const eventPattern = `langhook.events.${event.publisher}.${event.resource.type}.${event.resource.id}.${event.action}`;
    const matches = subscriptions.filter(sub => {
      if (!sub.active) return false;
      const regexPattern = sub.pattern.replace(/\*/g, '[^.]+').replace(/>/g, '.*');
      try {
        const regex = new RegExp(`^${regexPattern}$`);
        return regex.test(eventPattern);
      } catch { return false; }
    });
    setMatchedSubscriptions(matches);
  };

  const createMockCanonicalEvent = (source: string, payload: any): CanonicalEvent => {
    const timestamp = new Date().toISOString();
    switch (source) {
      case 'github':
        return {
          publisher: 'github',
          resource: { type: 'pull_request', id: payload.pull_request?.number || 1 },
          action: payload.action === 'opened' ? 'create' : 'update',
          timestamp,
          summary: `PR ${payload.pull_request?.number} ${payload.action} by ${payload.pull_request?.user?.login || 'user'}`,
          raw: payload
        };
      case 'stripe':
        return {
          publisher: 'stripe',
          resource: { type: 'payment_intent', id: payload.data?.object?.id || 'pi_unknown' },
          action: 'create',
          timestamp,
          summary: `PaymentIntent ${payload.data?.object?.id} succeeded`,
          raw: payload
        };
      case 'slack':
        // Handle different Slack event types
        const eventType = payload.event?.type;
        if (eventType === 'message') {
          return {
            publisher: 'slack',
            resource: { type: 'message', id: payload.event?.channel || 'C_unknown' },
            action: 'created',
            timestamp,
            summary: `Message posted to channel ${payload.event?.channel || 'unknown'}`,
            raw: payload
          };
        } else {
          // Default to file sharing event (original behavior)
          return {
            publisher: 'slack',
            resource: { type: 'file', id: payload.file?.id || 'F_unknown' },
            action: 'read',
            timestamp,
            summary: `File ${payload.file?.name} shared to channel`,
            raw: payload
          };
        }
      default:
        return { publisher: source, resource: { type: 'unknown', id: 'unknown' }, action: 'create', timestamp, raw: payload };
    }
  };

  const sendWebhook = async () => {
    setIsLoading(true);
    setError('');
    setSuccess('');
    setOutputEvent(null);
    setMatchedSubscriptions([]);

    try {
      let payload;
      try { payload = JSON.parse(inputPayload); }
      catch (e) { throw new Error('Invalid JSON payload'); }

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (selectedSource === 'github') { headers['X-GitHub-Event'] = 'pull_request'; }

      const response = await fetch(`/ingest/${selectedSource}`, { method: 'POST', headers, body: JSON.stringify(payload) });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send webhook');
      }

      const result = await response.json();
      setSuccess(`Event accepted with ID: ${result.request_id}`);

      const canonicalEvent = createMockCanonicalEvent(selectedSource, payload);
      setTimeout(() => { // Simulate processing delay
        setOutputEvent(canonicalEvent);
        checkSubscriptionMatches(canonicalEvent);
        // Refresh event logs to show the new event
        loadEventLogs();
      }, 1500);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const generateMapping = async () => {
    setIsLoading(true);
    setError('');
    try {
      const payload = JSON.parse(inputPayload);
      const response = await fetch('/map/suggest-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: selectedSource, payload: payload })
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate mapping');
      }
      const result = await response.json();
      setSuccess(`Generated JSONata mapping: ${result.jsonata}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate mapping');
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

            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Canonical Data</h3>
                <div className="bg-gray-800 text-gray-200 p-4 rounded-md font-mono text-sm overflow-x-auto">
                  <pre>{JSON.stringify(selectedEventLog.canonical_data, null, 2)}</pre>
                </div>
              </div>

              {selectedEventLog.raw_payload && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-2">Raw Payload</h3>
                  <div className="bg-gray-800 text-gray-200 p-4 rounded-md font-mono text-sm overflow-x-auto">
                    <pre>{JSON.stringify(selectedEventLog.raw_payload, null, 2)}</pre>
                  </div>
                </div>
              )}
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
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div>
            <h3 className="text-lg font-medium text-gray-800 mb-4">Webhook Input</h3>
            
            <div className="mb-4">
              <label htmlFor="source" className="block text-sm font-medium text-gray-500 mb-2">Source:</label>
              <select
                id="source"
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                className="w-full bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 transition-colors text-sm"
              >
                <option value="github">GitHub</option>
                <option value="stripe">Stripe</option>
                <option value="slack">Slack</option>
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

              <button
                className="flex-1 py-2 px-4 rounded-md font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 bg-white hover:bg-gray-50 active:bg-gray-100 active:scale-95 text-gray-700 border border-gray-300 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={generateMapping}
                disabled={isLoading || !inputPayload.trim()}
              >
                <Zap size={16} /> Suggest Mapping
              </button>
            </div>
          </div>

          {/* Output Section */}
          <div>
            <h3 className="text-lg font-medium text-gray-800 mb-4">Processed Event</h3>
            <div className="bg-gray-800 text-gray-200 p-4 rounded-md font-mono text-sm min-h-[300px] whitespace-pre-wrap overflow-x-auto">
              {outputEvent ? JSON.stringify(outputEvent, null, 2) : <span className="text-gray-500">Send a webhook to see the canonical event output...</span>}
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

      {/* Matched Subscriptions for the latest event */}
      {matchedSubscriptions.length > 0 && (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
          <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
            <Bell size={24} className="text-blue-600" />
            Notified Subscribers (for last event)
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pattern
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {matchedSubscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {sub.description}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-700">
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                        {sub.pattern}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      {/* Event Detail Modal */}
      {showEventModal && <EventDetailModal />}
    </div>
  );
};

export default Events;
