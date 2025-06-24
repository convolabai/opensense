import React, { useState } from 'react'; // useEffect might not be needed if no initial data fetch is done here
import { Plus, Eye, RefreshCw, Bell, Trash2, List, ChevronDown, ChevronRight, Filter } from 'lucide-react';
import { apiFetch } from './apiUtils';

// Interfaces (copied from App.tsx, ensure they are consistent)
interface GateConfig {
  enabled: boolean;
  prompt: string;
}

interface Subscription {
  id: number;
  subscriber_id: string;
  description: string;
  pattern: string;
  channel_type: string | null;
  channel_config: any;
  active: boolean;
  disposable: boolean;
  used: boolean;
  gate: GateConfig | null;
  created_at: string;
  updated_at?: string;
}

interface SubscriptionCreate {
  description: string;
  channel_type?: string;
  channel_config?: any;
  gate?: GateConfig;
  disposable?: boolean;
}

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
  webhook_sent: boolean;
  webhook_response_status?: number;
  gate_passed?: boolean;
  gate_reason?: string;
  logged_at: string;
}

interface EventLogListResponse {
  event_logs: EventLog[];
  total: number;
  page: number;
  size: number;
}

interface SubscriptionsProps {
  subscriptions: Subscription[];
  refreshSubscriptions: () => Promise<void>;
}

const Subscriptions: React.FC<SubscriptionsProps> = ({ subscriptions, refreshSubscriptions }) => {
  const [subscriptionDescription, setSubscriptionDescription] = useState<string>('');
  const [webhookUrl, setWebhookUrl] = useState<string>('');
  const [isSubscriptionLoading, setIsSubscriptionLoading] = useState(false);
  const [subscriptionError, setSubscriptionError] = useState<string>('');
  const [subscriptionSuccess, setSubscriptionSuccess] = useState<string>('');
  const [deletingSubscriptionId, setDeletingSubscriptionId] = useState<number | null>(null);
  
  // LLM Gate state
  const [gateEnabled, setGateEnabled] = useState<boolean>(false);
  const [gatePrompt, setGatePrompt] = useState<string>('');
  
  // Disposable subscription state
  const [disposableEnabled, setDisposableEnabled] = useState<boolean>(false);
  
  // Expanded rows state
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  
  // Subscription events state
  const [selectedSubscription, setSelectedSubscription] = useState<Subscription | null>(null);
  const [subscriptionEvents, setSubscriptionEvents] = useState<EventLog[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string>('');
  const [showEventsModal, setShowEventsModal] = useState(false);
  const [eventsCurrentPage, setEventsCurrentPage] = useState(1);
  const [totalEvents, setTotalEvents] = useState(0);
  const [eventFilter, setEventFilter] = useState<'all' | 'blocked' | 'allowed'>('all');
  const [expandedEventRows, setExpandedEventRows] = useState<Set<number>>(new Set());
  
  const eventsPageSize = 20;

  const toggleRowExpansion = (subscriptionId: number) => {
    const newExpandedRows = new Set(expandedRows);
    if (newExpandedRows.has(subscriptionId)) {
      newExpandedRows.delete(subscriptionId);
    } else {
      newExpandedRows.add(subscriptionId);
    }
    setExpandedRows(newExpandedRows);
  };

  const createSubscription = async () => {
    if (!subscriptionDescription.trim()) {
      setSubscriptionError('Please provide a description');
      return;
    }

    setIsSubscriptionLoading(true);
    setSubscriptionError('');
    setSubscriptionSuccess('');

    try {
      const subscriptionData: SubscriptionCreate = {
        description: subscriptionDescription.trim(),
        ...(webhookUrl.trim() && {
          channel_type: 'webhook',
          channel_config: { url: webhookUrl.trim(), method: 'POST' }
        }),
        ...(gateEnabled && {
          gate: {
            enabled: true,
            prompt: gatePrompt.trim() || ''
          }
        }),
        disposable: disposableEnabled
      };

      const response = await apiFetch('/subscriptions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscriptionData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create subscription');
      }

      const result = await response.json();
      setSubscriptionSuccess(`Subscription created! Subject filter: ${result.pattern}`);
      setSubscriptionDescription('');
      setWebhookUrl('');
      setGateEnabled(false);
      setGatePrompt('');
      setDisposableEnabled(false);

      await refreshSubscriptions(); // Call the refresh function passed as a prop

    } catch (err) {
      setSubscriptionError(err instanceof Error ? err.message : 'Failed to create subscription');
    } finally {
      setIsSubscriptionLoading(false);
    }
  };

  const deleteSubscription = async (subscriptionId: number) => {
    if (!window.confirm('Are you sure you want to delete this subscription? This action cannot be undone.')) {
      return;
    }

    setDeletingSubscriptionId(subscriptionId);
    setSubscriptionError('');
    setSubscriptionSuccess('');

    try {
      const response = await apiFetch(`/subscriptions/${subscriptionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete subscription' }));
        throw new Error(errorData.detail || 'Failed to delete subscription');
      }

      setSubscriptionSuccess('Subscription deleted successfully');
      await refreshSubscriptions();

    } catch (err) {
      setSubscriptionError(err instanceof Error ? err.message : 'Failed to delete subscription');
    } finally {
      setDeletingSubscriptionId(null);
    }
  };

  const viewSubscriptionEvents = async (subscription: Subscription) => {
    setSelectedSubscription(subscription);
    setEventsCurrentPage(1);
    setShowEventsModal(true);
    await loadSubscriptionEvents(subscription.id, 1);
  };

  const loadSubscriptionEvents = async (subscriptionId: number, page: number) => {
    setEventsLoading(true);
    setEventsError('');
    
    try {
      const response = await apiFetch(`/subscriptions/${subscriptionId}/events?page=${page}&size=${eventsPageSize}`);
      if (!response.ok) {
        throw new Error('Failed to fetch subscription events');
      }
      const data: EventLogListResponse = await response.json();
      setSubscriptionEvents(data.event_logs);
      setTotalEvents(data.total);
      setEventsCurrentPage(page);
    } catch (err) {
      setEventsError(err instanceof Error ? err.message : 'Failed to fetch subscription events');
    } finally {
      setEventsLoading(false);
    }
  };

  const closeEventsModal = () => {
    setShowEventsModal(false);
    setSelectedSubscription(null);
    setSubscriptionEvents([]);
    setEventsError('');
    setEventFilter('all');
    setExpandedEventRows(new Set());
  };

  const toggleEventRowExpansion = (eventId: number) => {
    const newExpandedRows = new Set(expandedEventRows);
    if (newExpandedRows.has(eventId)) {
      newExpandedRows.delete(eventId);
    } else {
      newExpandedRows.add(eventId);
    }
    setExpandedEventRows(newExpandedRows);
  };

  const getFilteredEvents = () => {
    if (eventFilter === 'all') return subscriptionEvents;
    if (eventFilter === 'blocked') return subscriptionEvents.filter(event => event.gate_passed === false);
    if (eventFilter === 'allowed') return subscriptionEvents.filter(event => event.gate_passed === true);
    return subscriptionEvents;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  // Sort subscriptions by created_at in descending order (newest first)
  const sortedSubscriptions = [...subscriptions].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const eventsTotalPages = Math.ceil(totalEvents / eventsPageSize);

  const SubscriptionEventsModal = () => {
    if (!selectedSubscription) return null;

    const filteredEvents = getFilteredEvents();

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-hidden">
          <div className="flex justify-between items-center p-6 border-b border-gray-200">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Events for Subscription</h2>
              <p className="text-sm text-gray-600 mt-1">{selectedSubscription.description}</p>
              <p className="text-xs text-gray-500 font-mono mt-1">{selectedSubscription.pattern}</p>
            </div>
            <button
              onClick={closeEventsModal}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              ✕
            </button>
          </div>
          
          {/* Filter Controls */}
          {selectedSubscription.gate?.enabled && (
            <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-4">
                <Filter size={16} className="text-gray-500" />
                <span className="text-sm font-medium text-gray-700">Filter by gate result:</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEventFilter('all')}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                      eventFilter === 'all'
                        ? 'bg-blue-100 text-blue-800 border-blue-200'
                        : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    All Events ({subscriptionEvents.length})
                  </button>
                  <button
                    onClick={() => setEventFilter('allowed')}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                      eventFilter === 'allowed'
                        ? 'bg-green-100 text-green-800 border-green-200'
                        : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    Allowed ({subscriptionEvents.filter(e => e.gate_passed === true).length})
                  </button>
                  <button
                    onClick={() => setEventFilter('blocked')}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                      eventFilter === 'blocked'
                        ? 'bg-red-100 text-red-800 border-red-200'
                        : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    Blocked ({subscriptionEvents.filter(e => e.gate_passed === false).length})
                  </button>
                </div>
              </div>
            </div>
          )}
          
          <div className="overflow-y-auto max-h-[calc(90vh-200px)]">
            {eventsError && (
              <div className="p-4 m-6 rounded-md text-sm bg-red-100 border border-red-400 text-red-700">
                {eventsError}
              </div>
            )}

            {eventsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <span className="ml-3 text-gray-600">Loading events...</span>
              </div>
            ) : filteredEvents.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12"></th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Event</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resource</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                      {selectedSubscription.gate?.enabled && (
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Gate</th>
                      )}
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredEvents.map((event) => {
                      const isExpanded = expandedEventRows.has(event.id);
                      return (
                        <React.Fragment key={event.id}>
                          <tr className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <button
                                onClick={() => toggleEventRowExpansion(event.id)}
                                className="flex items-center justify-center w-6 h-6 text-gray-400 hover:text-gray-600 transition-colors"
                                title={isExpanded ? "Hide details" : "Show details"}
                              >
                                {isExpanded ? (
                                  <ChevronDown size={14} />
                                ) : (
                                  <ChevronRight size={14} />
                                )}
                              </button>
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <div className="text-gray-900 font-medium truncate max-w-xs" title={event.event_id}>
                                {event.event_id}
                              </div>
                              <div className="text-gray-500 text-xs">{event.publisher}</div>
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <div className="text-gray-900">{event.resource_type}</div>
                              <div className="text-gray-500 text-xs">{event.resource_id}</div>
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {event.action}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {formatTimestamp(event.timestamp)}
                            </td>
                            {selectedSubscription.gate?.enabled && (
                              <td className="px-4 py-3 text-sm">
                                {event.gate_passed !== null && event.gate_passed !== undefined ? (
                                  <div className="flex items-center gap-2">
                                    {event.gate_passed ? (
                                      <>
                                        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                                        <span className="text-green-600 text-xs font-medium">Allowed</span>
                                      </>
                                    ) : (
                                      <>
                                        <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                                        <span className="text-red-600 text-xs font-medium">Blocked</span>
                                      </>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-gray-400 text-xs">N/A</span>
                                )}
                              </td>
                            )}
                            <td className="px-4 py-3 text-sm">
                              {selectedSubscription.channel_type === 'webhook' && selectedSubscription.channel_config?.url ? (
                                <div className="flex items-center gap-2">
                                  {event.webhook_sent ? (
                                    <>
                                      <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                                      <span className="text-green-600 text-xs">Sent</span>
                                      {event.webhook_response_status && (
                                        <span className="text-xs text-gray-500">({event.webhook_response_status})</span>
                                      )}
                                    </>
                                  ) : (
                                    <>
                                      <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                                      <span className="text-red-600 text-xs">Failed</span>
                                    </>
                                  )}
                                </div>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
                                  <span className="text-purple-600 text-xs">Polling</span>
                                </div>
                              )}
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr>
                              <td colSpan={selectedSubscription.gate?.enabled ? 7 : 6} className="px-4 py-4 bg-gray-50">
                                <div className="space-y-4">
                                  {/* Gate Evaluation Details */}
                                  {selectedSubscription.gate?.enabled && event.gate_reason && (
                                    <div>
                                      <h5 className="text-sm font-medium text-gray-700 mb-2">Gate Reasoning</h5>
                                      <div className="bg-white p-3 rounded border text-sm text-gray-700">
                                        {event.gate_reason}
                                      </div>
                                    </div>
                                  )}

                                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    {/* Canonical Data */}
                                    <div>
                                      <h5 className="text-sm font-medium text-gray-700 mb-2">Canonical Data</h5>
                                      <div className="bg-gray-800 text-gray-200 p-3 rounded font-mono text-xs max-h-60 overflow-y-auto">
                                        <pre>{JSON.stringify(event.canonical_data, null, 2)}</pre>
                                      </div>
                                    </div>

                                    {/* Raw Payload */}
                                    {event.raw_payload && (
                                      <div>
                                        <h5 className="text-sm font-medium text-gray-700 mb-2">Raw Payload</h5>
                                        <div className="bg-gray-800 text-gray-200 p-3 rounded font-mono text-xs max-h-60 overflow-y-auto">
                                          <pre>{JSON.stringify(event.raw_payload, null, 2)}</pre>
                                        </div>
                                      </div>
                                    )}
                                  </div>

                                  {/* Additional Event Details */}
                                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pt-2 border-t border-gray-200 text-xs text-gray-500">
                                    <div><span className="font-medium">Source:</span> {event.source}</div>
                                    <div><span className="font-medium">Subject:</span> {event.subject}</div>
                                    <div><span className="font-medium">Logged:</span> {formatTimestamp(event.logged_at)}</div>
                                    {selectedSubscription.channel_config?.url && (
                                      <div className="truncate"><span className="font-medium">Webhook:</span> {selectedSubscription.channel_config.url}</div>
                                    )}
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-12">
                <List size={48} className="mx-auto mb-4 text-gray-300" />
                <p className="text-lg font-medium">
                  {eventFilter === 'all' ? 'No events found' : `No ${eventFilter} events found`}
                </p>
                <p className="text-sm">
                  {eventFilter === 'all' 
                    ? "This subscription hasn't matched any events yet."
                    : `No events match the ${eventFilter} filter.`
                  }
                </p>
              </div>
            )}

            {/* Pagination */}
            {eventsTotalPages > 1 && (
              <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
                <div className="text-sm text-gray-500">
                  Showing {((eventsCurrentPage - 1) * eventsPageSize) + 1} to {Math.min(eventsCurrentPage * eventsPageSize, totalEvents)} of {totalEvents} events
                  {eventFilter !== 'all' && (
                    <span className="ml-2 text-blue-600">
                      (filtered to {filteredEvents.length} {eventFilter})
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => selectedSubscription && loadSubscriptionEvents(selectedSubscription.id, eventsCurrentPage - 1)}
                    disabled={eventsCurrentPage === 1 || eventsLoading}
                    className="px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-2 text-sm font-medium text-gray-700">
                    Page {eventsCurrentPage} of {eventsTotalPages}
                  </span>
                  <button
                    onClick={() => selectedSubscription && loadSubscriptionEvents(selectedSubscription.id, eventsCurrentPage + 1)}
                    disabled={eventsCurrentPage === eventsTotalPages || eventsLoading}
                    className="px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      {/* Create Subscription Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
          <Plus size={24} className="text-blue-600" />
          Create New Subscription
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="subDesc" className="block text-sm font-medium text-gray-500 mb-2">
              Natural Language Description:
            </label>
            <textarea
              id="subDesc"
              className="w-full min-h-[100px] bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm transition-colors"
              value={subscriptionDescription}
              onChange={(e) => setSubscriptionDescription(e.target.value)}
              placeholder="e.g., 'GitHub PR opened' or 'Stripe payment > $100 succeeded'"
            />
          </div>

          <div>
            <label htmlFor="webhookUrl" className="block text-sm font-medium text-gray-500 mb-2">
              Webhook URL (Optional):
            </label>
            <input
              id="webhookUrl"
              type="url"
              className="w-full bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm transition-colors"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-service.com/webhook (leave empty for polling only)"
            />
          </div>
        </div>

        {/* LLM Gate Configuration Section */}
        <div className="mt-6">
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center gap-3 mb-4">
              <label htmlFor="gateEnabled" className="text-sm font-medium text-gray-700">
                Enable LLM Gate
              </label>
              <input
                id="gateEnabled"
                type="checkbox"
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                checked={gateEnabled}
                onChange={(e) => setGateEnabled(e.target.checked)}
              />
            </div>
            
            {gateEnabled && (
              <div>
                <label htmlFor="gatePrompt" className="block text-sm font-medium text-gray-500 mb-2">
                  Gate Prompt (Optional - leave empty to use description):
                </label>
                <textarea
                  id="gatePrompt"
                  className="w-full min-h-[80px] bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm transition-colors"
                  value={gatePrompt}
                  onChange={(e) => setGatePrompt(e.target.value)}
                  placeholder="e.g., 'Only allow critical issues' or leave empty to use the description field"
                />
                <p className="text-xs text-gray-500 mt-1">
                  If left empty, the subscription description will be used as the gate prompt.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Disposable Subscription Configuration Section */}
        <div className="mt-6">
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center gap-3 mb-2">
              <label htmlFor="disposableEnabled" className="text-sm font-medium text-gray-700">
                One-time Use Subscription
              </label>
              <input
                id="disposableEnabled"
                type="checkbox"
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                checked={disposableEnabled}
                onChange={(e) => setDisposableEnabled(e.target.checked)}
              />
            </div>
            <p className="text-xs text-gray-500">
              If enabled, this subscription will be automatically disabled after matching the first event.
            </p>
          </div>
        </div>

        <div className="mt-6">
          <button
            className="w-full sm:w-auto py-2 px-6 rounded-md font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={createSubscription}
            disabled={isSubscriptionLoading || !subscriptionDescription.trim()}
          >
            {isSubscriptionLoading ? (
              <span className="flex items-center gap-2">
                <div className="w-5 h-5 border-2 border-white/50 border-t-transparent rounded-full animate-spin" />
                Creating...
              </span>
            ) : (
              <> <Bell size={16} /> Create Subscription </>
            )}
          </button>
        </div>

        {subscriptionError && <div className="p-4 rounded-md mt-6 text-sm bg-red-100 border-red-400 text-red-700">{subscriptionError}</div>}
        {subscriptionSuccess && <div className="p-4 rounded-md mt-6 text-sm bg-green-100 border-green-400 text-green-700">{subscriptionSuccess}</div>}
      </div>

      {/* Active Subscriptions Table Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="flex items-center gap-3 text-xl font-semibold text-gray-800 tracking-tight">
            <Eye size={24} className="text-blue-600" />
            Active Subscriptions
          </h2>
          <button
            className="py-1 px-3 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm text-xs"
            onClick={refreshSubscriptions}
            aria-label="Refresh subscriptions"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        </div>

        {sortedSubscriptions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Topic Filter
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Create Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    LLM Gate
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Notification Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedSubscriptions.map((sub) => {
                  const isExpanded = expandedRows.has(sub.id);
                  return (
                    <React.Fragment key={sub.id}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-sm text-gray-900">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => toggleRowExpansion(sub.id)}
                              className="flex items-center justify-center w-6 h-6 text-gray-400 hover:text-gray-600 transition-colors"
                              title={isExpanded ? "Collapse details" : "Expand details"}
                            >
                              {isExpanded ? (
                                <ChevronDown size={16} />
                              ) : (
                                <ChevronRight size={16} />
                              )}
                            </button>
                            <div className="max-w-xs truncate" title={sub.description}>
                              {sub.description}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          <code className="bg-gray-100 px-2 py-1 rounded text-xs font-mono">
                            {sub.pattern}
                          </code>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          {formatTimestamp(sub.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {sub.gate?.enabled ? (
                            <span className="text-green-600 flex items-center gap-1">
                              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                              Enabled
                            </span>
                          ) : (
                            <span className="text-gray-400 flex items-center gap-1">
                              <span className="w-2 h-2 bg-gray-300 rounded-full"></span>
                              Disabled
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {sub.channel_type === 'webhook' && sub.channel_config?.url ? (
                            <span className="text-blue-600 flex items-center gap-1">
                              <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                              Webhook
                            </span>
                          ) : (
                            <span className="text-purple-600 flex items-center gap-1">
                              <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
                              Polling
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex items-center gap-2">
                            <button
                              className="text-blue-600 hover:text-blue-800 transition-colors"
                              onClick={() => viewSubscriptionEvents(sub)}
                              title="View events"
                            >
                              <List size={16} />
                            </button>
                            <button
                              className="text-red-600 hover:text-red-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              onClick={() => deleteSubscription(sub.id)}
                              disabled={deletingSubscriptionId === sub.id}
                              title="Delete subscription"
                            >
                              {deletingSubscriptionId === sub.id ? (
                                <div className="w-4 h-4 border-2 border-red-600/50 border-t-transparent rounded-full animate-spin" />
                              ) : (
                                <Trash2 size={16} />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={6} className="px-6 py-4 bg-gray-50">
                            <div className="space-y-4">
                              {sub.gate?.enabled && (
                                <div>
                                  <h4 className="text-sm font-medium text-gray-700 mb-2">LLM Gate Prompt</h4>
                                  <div className="bg-white border border-gray-200 px-3 py-2 rounded text-xs">
                                    {sub.gate.prompt || <span className="text-gray-500 italic">Using subscription description</span>}
                                  </div>
                                </div>
                              )}
                              <div className="flex justify-between items-center text-xs text-gray-500 pt-2 border-t border-gray-200">
                                <div className="flex items-center gap-4">
                                  <div>
                                    Status: {sub.active && (!sub.disposable || !sub.used) ? (
                                      <span className="text-green-600 font-medium">Active</span>
                                    ) : (
                                      <span className="text-red-600 font-medium">
                                        {sub.disposable && sub.used ? 'Used' : 'Inactive'}
                                      </span>
                                    )}
                                  </div>
                                  {sub.disposable && (
                                    <div>
                                      Type: <span className="text-orange-600 font-medium">One-time use</span>
                                      {sub.used && <span className="text-red-600 ml-1">(Used)</span>}
                                    </div>
                                  )}
                                </div>
                                {sub.channel_config?.url && (
                                  <div className="truncate max-w-xs">
                                    <span className="font-medium">Webhook URL:</span> {sub.channel_config.url}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-500 py-16 sm:py-20 text-base">
            No subscriptions yet. Create your first subscription above!
          </div>
        )}
      </div>
      
      {/* Subscription Events Modal */}
      {showEventsModal && <SubscriptionEventsModal />}
    </div>
  );
};

export default Subscriptions;
