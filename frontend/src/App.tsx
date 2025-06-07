import React, { useState, useEffect } from 'react';
import { Send, BarChart3, Zap, ArrowRight, RefreshCw } from 'lucide-react';

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