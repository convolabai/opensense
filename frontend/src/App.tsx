import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Webhook,
  Bell,
  TrendingUp,
  CheckCircle,
  Plus,
  RefreshCw,
  Send,
  Zap,
  Menu,
  X,
} from 'lucide-react';

type NavItem = {
  id: string;
  label: string;
  icon: React.ComponentType<any>;
};

const navItems: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  { id: "events", label: "Events", icon: Webhook },
  { id: "subscriptions", label: "Subscriptions", icon: Bell },
];

// Mock data
const mockMetrics = {
  eventsProcessed: 15247,
  eventsPerSecond: 127,
  activeSubscriptions: 23,
  systemHealth: "healthy",
  uptime: "7d 12h 34m",
  errorRate: 0.2,
};

const mockEvents = [
  {
    id: "1",
    publisher: "github",
    resource: { type: "pull_request", id: 1374 },
    action: "created",
    timestamp: "2025-06-07T10:30:00Z",
    topic: "github.pull_request.created",
    status: "processed",
    rawPayload: {
      action: "created",
      number: 1374,
      pull_request: {
        id: 1374,
        title: "Add webhook validation",
        user: { login: "developer" },
      },
    },
  },
  {
    id: "2",
    publisher: "stripe",
    resource: { type: "payment_intent", id: "pi_123" },
    action: "succeeded",
    timestamp: "2025-06-07T10:25:00Z",
    topic: "stripe.payment_intent.succeeded",
    status: "processed",
    rawPayload: {
      type: "payment_intent.succeeded",
      data: {
        object: {
          id: "pi_123",
          amount: 5000,
          currency: "usd",
        },
      },
    },
  },
  {
    id: "3",
    publisher: "slack",
    resource: { type: "message", id: "msg_456" },
    action: "posted",
    timestamp: "2025-06-07T10:20:00Z",
    topic: "slack.message.posted",
    status: "failed",
    rawPayload: {
      type: "message",
      text: "Hello team!",
      user: "U123456",
    },
  },
];

const mockSubscriptions = [
  {
    id: 1,
    description: "Notify on GitHub PR creation",
    pattern: "github.pull_request.created",
    webhook: "https://api.example.com/webhooks/pr",
    status: "active",
    created: "2025-06-01T10:00:00Z",
  },
  {
    id: 2,
    description: "Alert on high-value payments",
    pattern: "stripe.payment_intent.succeeded",
    webhook: "https://api.example.com/webhooks/payment",
    status: "active",
    created: "2025-06-01T11:00:00Z",
  },
];

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
  const [activeTab, setActiveTab] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
      // Silently fail for metrics - use mock data
      setMetrics({
        events_processed: mockMetrics.eventsProcessed,
        events_mapped: Math.floor(mockMetrics.eventsProcessed * 0.85),
        events_failed: Math.floor(mockMetrics.eventsProcessed * 0.15),
        llm_invocations: Math.floor(mockMetrics.eventsProcessed * 0.3),
        mapping_success_rate: 0.85,
        llm_usage_rate: 0.3
      });
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
      const canonicalEvent = createMockCanonicalEvent(selectedSource, payload);
      setTimeout(() => {
        setOutputEvent(canonicalEvent);
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

  const Sidebar = () => (
    <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 border-r border-gray-800 transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0`}>
      <div className="flex items-center justify-between h-16 px-6 border-b border-gray-800">
        <h1 className="text-xl font-bold text-white">LangHook</h1>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden text-gray-400 hover:text-white"
        >
          <X size={24} />
        </button>
      </div>
      <nav className="mt-8">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id);
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center px-6 py-3 text-left transition-colors ${
                activeTab === item.id
                  ? 'bg-blue-600 text-white border-r-2 border-blue-400'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon size={20} className="mr-3" />
              {item.label}
            </button>
          );
        })}
      </nav>
    </div>
  );

  const DashboardView = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Events Processed</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {metrics?.events_processed || mockMetrics.eventsProcessed}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Zap className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Events/sec</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {mockMetrics.eventsPerSecond}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Bell className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Active Subscriptions</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {mockMetrics.activeSubscriptions}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Success Rate</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {((metrics?.mapping_success_rate || 0.85) * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Send Test Event</h3>
            <button
              onClick={() => setActiveTab('events')}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              View All Events →
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Source:
              </label>
              <select 
                value={selectedSource} 
                onChange={(e) => setSelectedSource(e.target.value)}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="github">GitHub</option>
                <option value="stripe">Stripe</option>
                <option value="slack">Slack</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Payload:
              </label>
              <textarea
                value={inputPayload}
                onChange={(e) => setInputPayload(e.target.value)}
                rows={8}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter webhook payload JSON..."
              />
            </div>

            <div className="flex space-x-3">
              <button 
                onClick={sendWebhook}
                disabled={isLoading || !inputPayload.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center justify-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    <span>Send Event</span>
                  </>
                )}
              </button>
              
              <button 
                onClick={generateMapping}
                disabled={isLoading || !inputPayload.trim()}
                className="flex-1 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center justify-center space-x-2"
              >
                <Zap size={16} />
                <span>Generate Mapping</span>
              </button>
            </div>

            {error && (
              <div className="p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 rounded-md">
                {error}
              </div>
            )}
            {success && (
              <div className="p-3 bg-green-100 dark:bg-green-900 border border-green-400 dark:border-green-600 text-green-700 dark:text-green-200 rounded-md">
                {success}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Canonical Event Output</h3>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md border">
            <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono">
              {outputEvent ? JSON.stringify(outputEvent, null, 2) : 'Send a webhook to see the canonical event output...'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );

  const EventsView = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Recent Events</h2>
        <button
          onClick={loadMetrics}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center space-x-2"
        >
          <RefreshCw size={16} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Publisher
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Resource
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Action
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Timestamp
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {mockEvents.map((event) => (
              <tr key={event.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                  {event.publisher}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {event.resource.type}.{event.resource.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {event.action}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      event.status === 'processed'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}
                  >
                    {event.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {new Date(event.timestamp).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const SubscriptionsView = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Subscriptions</h2>
        <button
          onClick={loadSubscriptions}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center space-x-2"
        >
          <RefreshCw size={16} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Create New Subscription</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Natural Language Description:
              </label>
              <textarea
                value={subscriptionDescription}
                onChange={(e) => setSubscriptionDescription(e.target.value)}
                rows={4}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Describe what events you want to be notified about, e.g., 'Notify me when a GitHub pull request is opened'"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Webhook URL:
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="https://your-service.com/webhook"
              />
            </div>

            <button 
              onClick={createSubscription}
              disabled={isSubscriptionLoading || !subscriptionDescription.trim() || !webhookUrl.trim()}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center justify-center space-x-2"
            >
              {isSubscriptionLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Creating...</span>
                </>
              ) : (
                <>
                  <Plus size={16} />
                  <span>Create Subscription</span>
                </>
              )}
            </button>

            {subscriptionError && (
              <div className="p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 rounded-md">
                {subscriptionError}
              </div>
            )}
            {subscriptionSuccess && (
              <div className="p-3 bg-green-100 dark:bg-green-900 border border-green-400 dark:border-green-600 text-green-700 dark:text-green-200 rounded-md">
                {subscriptionSuccess}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Active Subscriptions</h3>
          
          <div className="space-y-4">
            {mockSubscriptions.map((sub) => (
              <div key={sub.id} className="p-4 border border-gray-200 dark:border-gray-700 rounded-md">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-white">{sub.description}</h4>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    sub.status === 'active'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                  }`}>
                    {sub.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  Pattern: <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs">{sub.pattern}</code>
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Created: {new Date(sub.created).toLocaleDateString()}
                </p>
              </div>
            ))}
            
            {subscriptions.length === 0 && mockSubscriptions.length === 0 && (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                No subscriptions yet. Create your first subscription above!
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const renderActiveTab = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardView />;
      case "events":
        return <EventsView />;
      case "subscriptions":
        return <SubscriptionsView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex">
      <Sidebar />
      
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top navigation */}
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            >
              <Menu size={24} />
            </button>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white capitalize">
              {activeTab}
            </h1>
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>System Healthy</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          {renderActiveTab()}
        </main>
      </div>
    </div>
  );
}

export default App;