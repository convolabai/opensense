import React, { useState, useEffect } from 'react';
import { Send, ArrowRight, Zap, ListChecks, Bell } from 'lucide-react'; // Add other icons as needed

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
  const [recentEvents, setRecentEvents] = useState<CanonicalEvent[]>([]);


  useEffect(() => {
    const sample = samplePayloads[selectedSource as keyof typeof samplePayloads];
    if (sample) {
      setInputPayload(JSON.stringify(sample.payload, null, 2));
    }
  }, [selectedSource]);

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
        return {
          publisher: 'slack',
          resource: { type: 'file', id: payload.file?.id || 'F_unknown' },
          action: 'read',
          timestamp,
          summary: `File ${payload.file?.name} shared to channel`,
          raw: payload
        };
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
        setRecentEvents(prevEvents => [canonicalEvent, ...prevEvents.slice(0, 4)]); // Keep last 5 events
        checkSubscriptionMatches(canonicalEvent);
        // loadMetrics(); // Removed: App.tsx or Dashboard.tsx should handle metrics refresh if needed
      }, 1000);

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

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
          <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
            <Send size={24} className="text-blue-600" />
            Webhook Input
          </h2>

          <div className="mb-6">
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

          <div className="flex flex-col sm:flex-row gap-4 mt-6">
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

          {error && <div className="p-4 rounded-md mt-6 text-sm bg-red-100 border border-red-400 text-red-700">{error}</div>}
          {success && <div className="p-4 rounded-md mt-6 text-sm bg-green-100 border border-green-400 text-green-700">{success}</div>}
        </div>

        {/* Output Section */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
          <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
            <ArrowRight size={24} className="text-blue-600" />
            Processed Event
          </h2>
          <div className="bg-gray-800 text-gray-200 p-4 rounded-md font-mono text-sm min-h-[420px] whitespace-pre-wrap overflow-x-auto">
            {outputEvent ? JSON.stringify(outputEvent, null, 2) : <span className="text-gray-500">Send a webhook to see the canonical event output...</span>}
          </div>
        </div>
      </div>

      {/* Recent Events Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
          <ListChecks size={24} className="text-blue-600" /> {/* Changed icon */}
          Recent Events Stream
        </h2>
        {recentEvents.length > 0 ? (
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
            {recentEvents.map((event, index) => (
              <div key={index} className="bg-gray-800 text-gray-200 p-3 sm:p-4 rounded-md font-mono text-xs whitespace-pre-wrap overflow-x-auto">
                <p className="text-blue-400 font-semibold mb-1 text-sm">Event {recentEvents.length - index} ({event.summary || `${event.publisher}/${event.resource.type}`})</p>
                {JSON.stringify(event, null, 2)}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8 sm:py-12 text-base">No events processed yet in this session.</p>
        )}
      </div>

      {/* Matched Subscriptions for the latest event */}
      {matchedSubscriptions.length > 0 && (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
          <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
            <Bell size={24} className="text-blue-600" /> {/* Added Bell icon */}
            Notified Subscribers (for last event)
          </h2>
          <div className="space-y-3">
            {matchedSubscriptions.map((sub) => (
              <div key={sub.id} className="p-3 bg-green-100 border border-green-300 rounded-lg shadow">
                <div className="flex justify-between items-center">
                  <span className="text-green-700 font-medium text-sm">{sub.description}</span>
                  <code className="bg-green-200 text-green-800 px-2 py-1 rounded-md text-xs font-mono">{sub.pattern}</code>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Events;
