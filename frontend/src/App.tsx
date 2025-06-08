import React, { useState, useEffect } from 'react';
import { Send, BarChart3, Zap, ArrowRight, RefreshCw, Bell, Eye, Plus } from 'lucide-react';

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

interface Metrics {
  events_processed: number;
  events_mapped: number;
  events_failed: number;
  llm_invocations: number;
  mapping_success_rate: number;
  llm_usage_rate: number;
}

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

interface SubscriptionCreate {
  description: string;
  channel_type: string;
  channel_config: any;
}

const samplePayloads = {
  github: {
    name: "GitHub PR Opened",
    payload: {
      action: "opened",
      pull_request: {
        number: 1374,
        title: "Add new feature",
        state: "open",
        user: {
          login: "alice"
        }
      },
      repository: {
        name: "test-repo",
        id: 12345
      }
    }
  },
  stripe: {
    name: "Stripe Payment Succeeded",
    payload: {
      type: "payment_intent.succeeded",
      data: {
        object: {
          id: "pi_3OrFAb47K1Z2xQ8C0123",
          amount: 2000,
          currency: "usd",
          status: "succeeded"
        }
      }
    }
  },
  slack: {
    name: "Slack File Shared",
    payload: {
      type: "file_shared",
      file: {
        id: "F06A2G45T",
        name: "design.png",
        channels: ["C123456"]
      },
      user_id: "U123456"
    }
  }
};

function App() {
  const [selectedSource, setSelectedSource] = useState<string>('github');
  const [inputPayload, setInputPayload] = useState<string>('');
  const [outputEvent, setOutputEvent] = useState<CanonicalEvent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  
  // Subscription state
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [subscriptionDescription, setSubscriptionDescription] = useState<string>('');
  const [webhookUrl, setWebhookUrl] = useState<string>('');
  const [isSubscriptionLoading, setIsSubscriptionLoading] = useState(false);
  const [subscriptionError, setSubscriptionError] = useState<string>('');
  const [subscriptionSuccess, setSubscriptionSuccess] = useState<string>('');
  const [matchedSubscriptions, setMatchedSubscriptions] = useState<Subscription[]>([]);

  // Load sample payload when source changes
  useEffect(() => {
    const sample = samplePayloads[selectedSource as keyof typeof samplePayloads];
    if (sample) {
      setInputPayload(JSON.stringify(sample.payload, null, 2));
    }
  }, [selectedSource]);

  // Load metrics on component mount
  useEffect(() => {
    loadMetrics();
    loadSubscriptions();
  }, []);

  const loadMetrics = async () => {
    try {
      const response = await fetch('/map/metrics/json');
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      }
    } catch (err) {
      // Silently fail for metrics
    }
  };

  const sendWebhook = async () => {
    setIsLoading(true);
    setError('');
    setSuccess('');
    setOutputEvent(null);

    try {
      // Parse the input JSON
      let payload;
      try {
        payload = JSON.parse(inputPayload);
      } catch (e) {
        throw new Error('Invalid JSON payload');
      }

      // Send to ingest endpoint
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (selectedSource === 'github') {
        headers['X-GitHub-Event'] = 'pull_request';
      }
      
      const response = await fetch(`/ingest/${selectedSource}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send webhook');
      }

      const result = await response.json();
      setSuccess(`Event accepted with ID: ${result.request_id}`);

      // Simulate the canonical event that would be produced
      // In a real system, this would come from a websocket or polling
      const canonicalEvent = createMockCanonicalEvent(selectedSource, payload);
      setTimeout(() => {
        setOutputEvent(canonicalEvent);
        checkSubscriptionMatches(canonicalEvent);
        loadMetrics(); // Refresh metrics
      }, 1000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const createMockCanonicalEvent = (source: string, payload: any): CanonicalEvent => {
    const timestamp = new Date().toISOString();
    
    switch (source) {
      case 'github':
        return {
          publisher: 'github',
          resource: {
            type: 'pull_request',
            id: payload.pull_request?.number || 1
          },
          action: payload.action === 'opened' ? 'create' : 'update',
          timestamp,
          summary: `PR ${payload.pull_request?.number} ${payload.action} by ${payload.pull_request?.user?.login || 'user'}`,
          raw: payload
        };
      
      case 'stripe':
        return {
          publisher: 'stripe',
          resource: {
            type: 'payment_intent',
            id: payload.data?.object?.id || 'pi_unknown'
          },
          action: 'create',
          timestamp,
          summary: `PaymentIntent ${payload.data?.object?.id} succeeded`,
          raw: payload
        };
      
      case 'slack':
        return {
          publisher: 'slack',
          resource: {
            type: 'file',
            id: payload.file?.id || 'F_unknown'
          },
          action: 'read',
          timestamp,
          summary: `File ${payload.file?.name} shared to channel`,
          raw: payload
        };
      
      default:
        return {
          publisher: source,
          resource: {
            type: 'unknown',
            id: 'unknown'
          },
          action: 'create',
          timestamp,
          raw: payload
        };
    }
  };

  const generateMapping = async () => {
    setIsLoading(true);
    setError('');

    try {
      const payload = JSON.parse(inputPayload);
      
      const response = await fetch('/map/suggest-map', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source: selectedSource,
          payload: payload
        })
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

  const loadSubscriptions = async () => {
    try {
      const response = await fetch('/subscriptions/');
      if (response.ok) {
        const data = await response.json();
        setSubscriptions(data.subscriptions || []);
      }
    } catch (err) {
      // Silently fail for subscriptions
    }
  };

  const createSubscription = async () => {
    if (!subscriptionDescription.trim() || !webhookUrl.trim()) {
      setSubscriptionError('Please provide both description and webhook URL');
      return;
    }

    setIsSubscriptionLoading(true);
    setSubscriptionError('');
    setSubscriptionSuccess('');

    try {
      const subscriptionData: SubscriptionCreate = {
        description: subscriptionDescription.trim(),
        channel_type: 'webhook',
        channel_config: {
          url: webhookUrl.trim(),
          method: 'POST'
        }
      };

      const response = await fetch('/subscriptions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscriptionData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create subscription');
      }

      const result = await response.json();
      setSubscriptionSuccess(`Subscription created! NATS pattern: ${result.pattern}`);
      setSubscriptionDescription('');
      setWebhookUrl('');
      
      // Reload subscriptions
      loadSubscriptions();

    } catch (err) {
      setSubscriptionError(err instanceof Error ? err.message : 'Failed to create subscription');
    } finally {
      setIsSubscriptionLoading(false);
    }
  };

  const checkSubscriptionMatches = (event: CanonicalEvent) => {
    // Mock subscription matching logic - in a real system this would be done by the backend
    const eventPattern = `langhook.events.${event.publisher}.${event.resource.type}.${event.resource.id}.${event.action}`;
    
    const matches = subscriptions.filter(sub => {
      if (!sub.active) return false;
      
      // Simple pattern matching - convert NATS wildcards to regex
      const regexPattern = sub.pattern
        .replace(/\*/g, '[^.]+')  // * matches one segment
        .replace(/>/g, '.*');     // > matches remaining segments
      
      try {
        const regex = new RegExp(`^${regexPattern}$`);
        return regex.test(eventPattern);
      } catch {
        return false;
      }
    });
    
    setMatchedSubscriptions(matches);
  };

  return (
    <div className="bg-slate-900 text-slate-100 min-h-screen p-4 md:p-8">
      <div className="container mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            LangHook Demo
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto">
            Transform webhooks into canonical events with AI-powered mapping
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Input Section */}
          <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700">
            <h2 className="flex items-center gap-3 text-2xl font-semibold mb-6 text-slate-100">
              <Send size={24} className="text-indigo-400" />
              Webhook Input
            </h2>

            <div className="mb-6">
              <label htmlFor="source" className="block text-sm font-medium text-slate-300 mb-2">Source:</label>
              <select
                id="source"
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg p-3 text-slate-100 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
              >
                <option value="github">GitHub</option>
                <option value="stripe">Stripe</option>
                <option value="slack">Slack</option>
              </select>
            </div>

            <textarea
              className="w-full min-h-[200px] bg-slate-900 text-slate-200 p-4 border border-slate-700 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm transition-colors"
              value={inputPayload}
              onChange={(e) => setInputPayload(e.target.value)}
              placeholder="Enter webhook payload JSON..."
            />

            <div className="flex flex-col sm:flex-row gap-4 mt-6">
              <button
                className="flex-1 py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-offset-slate-900 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={sendWebhook}
                disabled={isLoading || !inputPayload.trim()}
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </span>
                ) : (
                  <>
                    <Send size={18} />
                    Send Webhook
                  </>
                )}
              </button>

              <button
                className="flex-1 py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-offset-slate-900 bg-slate-600 hover:bg-slate-500 text-slate-100 border border-slate-500 hover:border-slate-400 shadow-md hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={generateMapping}
                disabled={isLoading || !inputPayload.trim()}
              >
                <Zap size={18} />
                Suggest Mapping
              </button>
            </div>

            {error && <div className="p-4 rounded-md mt-6 text-sm bg-red-700/30 border border-red-600 text-red-300 animate-pulse">{error}</div>}
            {success && <div className="p-4 rounded-md mt-6 text-sm bg-green-700/30 border border-green-600 text-green-300">{success}</div>}
          </div>

          {/* Output Section */}
          <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700">
            <h2 className="flex items-center gap-3 text-2xl font-semibold mb-6 text-slate-100">
              <ArrowRight size={24} className="text-indigo-400" />
              Canonical Event
            </h2>

            <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 min-h-[420px] font-mono text-sm text-slate-200 whitespace-pre-wrap overflow-x-auto">
              {outputEvent ? (
                JSON.stringify(outputEvent, null, 2)
              ) : (
                <span className="text-slate-400">Send a webhook to see the canonical event output...</span>
              )}
            </div>
          </div>
        </div>

        {/* Metrics Section */}
        <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700 mb-8">
          <h2 className="flex items-center gap-3 text-2xl font-semibold mb-6 text-slate-100">
            <BarChart3 size={24} className="text-indigo-400" />
          System Metrics
          <button 
              className="ml-auto py-1 px-2 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-slate-800 bg-slate-600 hover:bg-slate-500 text-slate-200 border border-slate-500 hover:border-slate-400 text-xs"
            onClick={loadMetrics}
          >
              <RefreshCw size={12} />
          </button>
        </h2>

          {metrics ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { label: "Events Processed", value: metrics.events_processed },
                { label: "Events Mapped", value: metrics.events_mapped },
                { label: "Events Failed", value: metrics.events_failed },
                { label: "Success Rate", value: `${(metrics.mapping_success_rate * 100).toFixed(1)}%` },
                { label: "LLM Invocations", value: metrics.llm_invocations },
                { label: "LLM Usage Rate", value: `${(metrics.llm_usage_rate * 100).toFixed(1)}%` },
              ].map(metric => (
                <div key={metric.label} className="bg-slate-800/70 p-5 rounded-lg shadow border border-slate-700/70 transition-all hover:shadow-lg hover:-translate-y-0.5">
                  <div className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400 mb-1">
                    {metric.value}
                  </div>
                  <div className="text-sm text-slate-400 uppercase tracking-wider">{metric.label}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-slate-400 py-8">Loading metrics...</div>
          )}
        </div>

        {/* Subscription Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
          {/* Create Subscription Section */}
          <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700">
            <h2 className="flex items-center gap-3 text-2xl font-semibold mb-6 text-slate-100">
              <Plus size={24} className="text-indigo-400" />
              Create Subscription
            </h2>

            <div className="mb-6">
              <label htmlFor="subDesc" className="block text-sm font-medium text-slate-300 mb-2">
                Natural Language Description:
              </label>
              <textarea
                id="subDesc"
                className="w-full min-h-[100px] bg-slate-900 text-slate-200 p-3 border border-slate-700 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm transition-colors"
                value={subscriptionDescription}
                onChange={(e) => setSubscriptionDescription(e.target.value)}
                placeholder="e.g., 'GitHub PR opened' or 'Stripe payment > $100 succeeded'"
              />
            </div>

            <div className="mb-6">
              <label htmlFor="webhookUrl" className="block text-sm font-medium text-slate-300 mb-2">
                Webhook URL:
              </label>
              <input
                id="webhookUrl"
                type="url"
                className="w-full bg-slate-900 text-slate-200 p-3 border border-slate-700 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm transition-colors"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-service.com/webhook"
            />
          </div>

          <button 
              className="w-full py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-offset-slate-800 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={createSubscription}
            disabled={isSubscriptionLoading || !subscriptionDescription.trim() || !webhookUrl.trim()}
          >
            {isSubscriptionLoading ? (
                <span className="flex items-center gap-2">
                  <div className="w-5 h-5 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />
                Creating...
              </span>
            ) : (
              <>
                  <Bell size={18} />
                Create Subscription
              </>
            )}
          </button>

            {subscriptionError && <div className="p-4 rounded-md mt-6 text-sm bg-red-700/30 border border-red-600 text-red-300 animate-pulse">{subscriptionError}</div>}
            {subscriptionSuccess && <div className="p-4 rounded-md mt-6 text-sm bg-green-700/30 border border-green-600 text-green-300">{subscriptionSuccess}</div>}
        </div>

          {/* Active Subscriptions Section */}
          <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700">
            <h2 className="flex items-center gap-3 text-2xl font-semibold mb-6 text-slate-100">
              <Eye size={24} className="text-indigo-400" />
            Active Subscriptions
            <button 
                className="ml-auto py-1 px-2 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-slate-800 bg-slate-600 hover:bg-slate-500 text-slate-200 border border-slate-500 hover:border-slate-400 text-xs"
              onClick={loadSubscriptions}
            >
                <RefreshCw size={12} />
            </button>
          </h2>

          {subscriptions.length > 0 ? (
              <div className="max-h-[400px] overflow-y-auto space-y-4 pr-2">
              {subscriptions.map((sub) => (
                  <div key={sub.id} className="p-4 bg-slate-800/70 border border-slate-700/70 rounded-lg shadow">
                    <div className="mb-2">
                      <strong className="text-slate-200">Description:</strong>
                      <span className="text-slate-300 ml-2">{sub.description}</span>
                  </div>
                    <div className="mb-3">
                      <strong className="text-slate-200">NATS Pattern:</strong>
                      <code className="ml-2 bg-slate-700 text-indigo-300 px-2 py-1 rounded-md text-xs font-mono">
                      {sub.pattern}
                    </code>
                  </div>
                    <div className="flex justify-between items-center text-xs text-slate-400">
                      <span>Status: {sub.active ?
                        <span className="text-green-400">🟢 Active</span> :
                        <span className="text-red-400">🔴 Inactive</span>}
                      </span>
                    <span>Created: {new Date(sub.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
              <div className="text-center text-slate-400 py-16">
                No subscriptions yet. Create your first subscription!
            </div>
          )}
        </div>
      </div>

        {/* Matched Subscriptions Section */}
        {matchedSubscriptions.length > 0 && (
          <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700 mb-8">
            <h2 className="flex items-center gap-3 text-2xl font-semibold mb-6 text-slate-100">
              <Bell size={24} className="text-indigo-400" />
              Notified Subscribers
            </h2>
            <p className="text-slate-300 mb-4 text-sm">
              The following subscriptions would be triggered by the current event:
            </p>
            <div className="space-y-3">
              {matchedSubscriptions.map((sub) => (
                <div key={sub.id} className="p-3 bg-green-800/30 border border-green-700/50 rounded-lg shadow">
                  <div className="flex justify-between items-center">
                    <span className="text-green-300 font-medium text-sm">{sub.description}</span>
                    <code className="bg-green-700/50 text-green-200 px-2 py-1 rounded-md text-xs font-mono">
                      {sub.pattern}
                    </code>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* How It Works Section */}
        <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 border border-slate-700">
          <h2 className="text-2xl font-semibold mb-6 text-slate-100 relative pb-3 after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-16 after:h-1 after:bg-gradient-to-r after:from-purple-500 after:to-indigo-500 after:rounded-full">
            How It Works
          </h2>
          <ol className="list-none space-y-6 pl-2">
            {[
              { title: "Webhook Ingestion", text: "Send any webhook to <code>/ingest/{source}</code>" },
              { title: "Event Transformation", text: "JSONata mappings convert raw payloads to canonical format" },
              { title: "CloudEvents Wrapper", text: "Events are wrapped in CNCF-compliant envelopes" },
              { title: "Intelligent Routing", text: "Natural language subscriptions match events to actions" },
            ].map((item, index) => (
              <li key={item.title} className="flex items-start group">
                <div className="mr-4 flex-shrink-0 h-10 w-10 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white font-semibold text-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg">
                  {index + 1}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-200 mb-1">{item.title}</h3>
                  <p className="text-slate-400 text-sm" dangerouslySetInnerHTML={{ __html: item.text }} />
                </div>
              </li>
            ))}
          </ol>

          <p className="mt-8 text-slate-300 text-sm leading-relaxed">
            The canonical event format ensures consistency across all webhook sources,
            making it easy to create powerful automation and monitoring rules.
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;