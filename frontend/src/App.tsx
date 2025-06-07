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
    <div className="container">
      <div className="header">
        <h1>LangHook Demo</h1>
        <p>Transform webhooks into canonical events with AI-powered mapping</p>
      </div>

      <div className="demo-section">
        <div className="card input-section">
          <h2 className="section-title">
            <Send size={20} />
            Webhook Input
          </h2>
          
          <div className="source-selector">
            <label htmlFor="source">Source: </label>
            <select 
              id="source"
              value={selectedSource} 
              onChange={(e) => setSelectedSource(e.target.value)}
            >
              <option value="github">GitHub</option>
              <option value="stripe">Stripe</option>
              <option value="slack">Slack</option>
            </select>
          </div>

          <textarea
            className="json-editor"
            value={inputPayload}
            onChange={(e) => setInputPayload(e.target.value)}
            placeholder="Enter webhook payload JSON..."
          />

          <div className="button-group">
            <button 
              className="btn btn-primary" 
              onClick={sendWebhook}
              disabled={isLoading || !inputPayload.trim()}
            >
              {isLoading ? (
                <span className="loading">
                  <div className="spinner" />
                  Processing...
                </span>
              ) : (
                <>
                  <Send size={16} />
                  Send Webhook
                </>
              )}
            </button>
            
            <button 
              className="btn btn-secondary" 
              onClick={generateMapping}
              disabled={isLoading || !inputPayload.trim()}
            >
              <Zap size={16} />
              Generate Mapping
            </button>
          </div>

          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}
        </div>

        <div className="card output-section">
          <h2 className="section-title">
            <ArrowRight size={20} />
            Canonical Event
          </h2>

          <div className="json-display">
            {outputEvent ? (
              JSON.stringify(outputEvent, null, 2)
            ) : (
              'Send a webhook to see the canonical event output...'
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="section-title">
          <BarChart3 size={20} />
          System Metrics
          <button 
            className="btn btn-secondary" 
            onClick={loadMetrics}
            style={{ marginLeft: 'auto', padding: '4px 8px' }}
          >
            <RefreshCw size={14} />
          </button>
        </h2>

        {metrics ? (
          <div className="metrics-section">
            <div className="metric-card">
              <div className="metric-value">{metrics.events_processed}</div>
              <div className="metric-label">Events Processed</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.events_mapped}</div>
              <div className="metric-label">Events Mapped</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.events_failed}</div>
              <div className="metric-label">Events Failed</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{(metrics.mapping_success_rate * 100).toFixed(1)}%</div>
              <div className="metric-label">Success Rate</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.llm_invocations}</div>
              <div className="metric-label">LLM Invocations</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{(metrics.llm_usage_rate * 100).toFixed(1)}%</div>
              <div className="metric-label">LLM Usage Rate</div>
            </div>
          </div>
        ) : (
          <div>Loading metrics...</div>
        )}
      </div>

      <div className="demo-section">
        <div className="card">
          <h2 className="section-title">
            <Plus size={20} />
            Create Subscription
          </h2>
          
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#cbd5e1' }}>
              Natural Language Description:
            </label>
            <textarea
              className="json-editor"
              style={{ minHeight: '120px' }}
              value={subscriptionDescription}
              onChange={(e) => setSubscriptionDescription(e.target.value)}
              placeholder="Describe what events you want to be notified about, e.g., 'Notify me when a GitHub pull request is opened' or 'Alert me when Stripe payment over $100 succeeds'"
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#cbd5e1' }}>
              Webhook URL:
            </label>
            <input
              type="url"
              className="json-editor"
              style={{ minHeight: 'auto', height: '48px' }}
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-service.com/webhook"
            />
          </div>

          <button 
            className="btn btn-primary" 
            onClick={createSubscription}
            disabled={isSubscriptionLoading || !subscriptionDescription.trim() || !webhookUrl.trim()}
          >
            {isSubscriptionLoading ? (
              <span className="loading">
                <div className="spinner" />
                Creating...
              </span>
            ) : (
              <>
                <Bell size={16} />
                Create Subscription
              </>
            )}
          </button>

          {subscriptionError && <div className="error">{subscriptionError}</div>}
          {subscriptionSuccess && <div className="success">{subscriptionSuccess}</div>}
        </div>

        <div className="card">
          <h2 className="section-title">
            <Eye size={20} />
            Active Subscriptions
            <button 
              className="btn btn-secondary" 
              onClick={loadSubscriptions}
              style={{ marginLeft: 'auto', padding: '4px 8px' }}
            >
              <RefreshCw size={14} />
            </button>
          </h2>

          {subscriptions.length > 0 ? (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {subscriptions.map((sub) => (
                <div key={sub.id} style={{ 
                  marginBottom: '16px', 
                  padding: '16px', 
                  background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
                  border: '1px solid #475569',
                  borderRadius: '8px'
                }}>
                  <div style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#f1f5f9' }}>Description:</strong>
                    <span style={{ color: '#cbd5e1', marginLeft: '8px' }}>{sub.description}</span>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#f1f5f9' }}>NATS Pattern:</strong>
                    <code style={{ 
                      marginLeft: '8px',
                      background: 'linear-gradient(135deg, #334155 0%, #475569 100%)',
                      color: '#e2e8f0',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '13px'
                    }}>
                      {sub.pattern}
                    </code>
                  </div>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '12px',
                    color: '#94a3b8'
                  }}>
                    <span>Status: {sub.active ? '🟢 Active' : '🔴 Inactive'}</span>
                    <span>Created: {new Date(sub.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: '#94a3b8', textAlign: 'center', padding: '40px' }}>
              No subscriptions yet. Create your first subscription above!
            </div>
          )}
        </div>
      </div>

      {matchedSubscriptions.length > 0 && (
        <div className="card">
          <h2 className="section-title">
            <Bell size={20} />
            Notified Subscribers
          </h2>
          <p style={{ color: '#cbd5e1', marginBottom: '20px' }}>
            The following subscriptions would be triggered by the current event:
          </p>
          {matchedSubscriptions.map((sub) => (
            <div key={sub.id} style={{ 
              marginBottom: '12px', 
              padding: '12px', 
              background: 'linear-gradient(135deg, #052e16 0%, #166534 100%)',
              border: '1px solid #16a34a',
              borderRadius: '8px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#86efac', fontWeight: '500' }}>{sub.description}</span>
                <code style={{ 
                  background: 'rgba(134, 239, 172, 0.2)',
                  color: '#86efac',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  {sub.pattern}
                </code>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2>How It Works</h2>
        <ol>
          <li><strong>Webhook Ingestion:</strong> Send any webhook to <code>/ingest/&#123;source&#125;</code></li>
          <li><strong>Event Transformation:</strong> JSONata mappings convert raw payloads to canonical format</li>
          <li><strong>CloudEvents Wrapper:</strong> Events are wrapped in CNCF-compliant envelopes</li>
          <li><strong>Intelligent Routing:</strong> Natural language subscriptions match events to actions</li>
        </ol>
        
        <p>
          The canonical event format ensures consistency across all webhook sources, 
          making it easy to create powerful automation and monitoring rules.
        </p>
      </div>
    </div>
  );
}

export default App;