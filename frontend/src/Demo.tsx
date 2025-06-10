import React, { useState } from 'react';
import { PlayCircle, Check, X, AlertCircle, ArrowRight, Zap, Filter, Bot } from 'lucide-react';

// Demo-specific subscription sentences and their mock events
const demoSubscriptions = [
  {
    id: 'github_pr_approved',
    sentence: 'Notify me when PR 1374 is approved',
    source: 'GitHub',
    pattern: 'langhook.events.github.pull_request.1374.updated',
    mockEvents: [
      {
        id: 1,
        description: 'PR 1234 approved by Alice',
        outcome: 'no_match',
        reason: 'Different PR number (1234 vs 1374)',
        canonicalEvent: {
          publisher: 'github',
          resource: { type: 'pull_request', id: 1234 },
          action: 'updated',
          summary: 'PR 1234 approved by Alice'
        }
      },
      {
        id: 2,
        description: 'PR 1374 title changed',
        outcome: 'llm_rejected',
        reason: 'Title change is not an approval',
        canonicalEvent: {
          publisher: 'github',
          resource: { type: 'pull_request', id: 1374 },
          action: 'updated',
          summary: 'PR 1374 title changed'
        }
      },
      {
        id: 3,
        description: 'PR 1374 approved by Alice',
        outcome: 'approved',
        reason: 'Matches PR number and is an approval',
        canonicalEvent: {
          publisher: 'github',
          resource: { type: 'pull_request', id: 1374 },
          action: 'updated',
          summary: 'PR 1374 approved by Alice'
        }
      }
    ]
  },
  {
    id: 'stripe_high_value_refund',
    sentence: 'Alert me when a high-value Stripe refund is issued',
    source: 'Stripe',
    pattern: 'langhook.events.stripe.refund.*.created',
    mockEvents: [
      {
        id: 1,
        description: 'Refund of $100 issued',
        outcome: 'no_match',
        reason: 'Amount too low for high-value threshold',
        canonicalEvent: {
          publisher: 'stripe',
          resource: { type: 'refund', id: 're_1234' },
          action: 'created',
          summary: 'Refund of $100 issued'
        }
      },
      {
        id: 2,
        description: 'Refund of $800 issued for test customer',
        outcome: 'llm_rejected',
        reason: 'Test transactions are not important',
        canonicalEvent: {
          publisher: 'stripe',
          resource: { type: 'refund', id: 're_5678' },
          action: 'created',
          summary: 'Refund of $800 issued for test customer'
        }
      },
      {
        id: 3,
        description: 'Refund of $950 issued for real transaction',
        outcome: 'approved',
        reason: 'High-value refund for real customer',
        canonicalEvent: {
          publisher: 'stripe',
          resource: { type: 'refund', id: 're_9012' },
          action: 'created',
          summary: 'Refund of $950 issued for real transaction'
        }
      }
    ]
  },
  {
    id: 'jira_ticket_done',
    sentence: 'Tell me when a Jira ticket is moved to Done',
    source: 'Jira',
    pattern: 'langhook.events.jira.issue.*.updated',
    mockEvents: [
      {
        id: 1,
        description: 'Ticket moved to "In Progress"',
        outcome: 'no_match',
        reason: 'Status changed but not to Done',
        canonicalEvent: {
          publisher: 'jira',
          resource: { type: 'issue', id: 'PROJ-123' },
          action: 'updated',
          summary: 'Ticket moved to "In Progress"'
        }
      },
      {
        id: 2,
        description: 'Ticket moved to Done: unassigned',
        outcome: 'llm_rejected',
        reason: 'Unassigned tickets may not be truly complete',
        canonicalEvent: {
          publisher: 'jira',
          resource: { type: 'issue', id: 'PROJ-456' },
          action: 'updated',
          summary: 'Ticket moved to Done: unassigned'
        }
      },
      {
        id: 3,
        description: 'Ticket moved to Done by product owner',
        outcome: 'approved',
        reason: 'Properly completed by authorized person',
        canonicalEvent: {
          publisher: 'jira',
          resource: { type: 'issue', id: 'PROJ-789' },
          action: 'updated',
          summary: 'Ticket moved to Done by product owner'
        }
      }
    ]
  },
  {
    id: 'slack_file_upload',
    sentence: 'Ping me when someone uploads a file to Slack',
    source: 'Slack',
    pattern: 'langhook.events.slack.file.*.created',
    mockEvents: [
      {
        id: 1,
        description: 'Message posted (not a file)',
        outcome: 'no_match',
        reason: 'Not a file upload event',
        canonicalEvent: {
          publisher: 'slack',
          resource: { type: 'message', id: 'msg_123' },
          action: 'created',
          summary: 'Message posted (not a file)'
        }
      },
      {
        id: 2,
        description: 'File uploaded with no context',
        outcome: 'llm_rejected',
        reason: 'Random file uploads may not be important',
        canonicalEvent: {
          publisher: 'slack',
          resource: { type: 'file', id: 'file_456' },
          action: 'created',
          summary: 'File uploaded with no context'
        }
      },
      {
        id: 3,
        description: 'File uploaded titled "Quarterly Results.pdf"',
        outcome: 'approved',
        reason: 'Important business document',
        canonicalEvent: {
          publisher: 'slack',
          resource: { type: 'file', id: 'file_789' },
          action: 'created',
          summary: 'File uploaded titled "Quarterly Results.pdf"'
        }
      }
    ]
  },
  {
    id: 'important_email',
    sentence: 'Let me know if an important email arrives',
    source: 'Email',
    pattern: 'langhook.events.email.message.*.received',
    mockEvents: [
      {
        id: 1,
        description: 'Email from newsletter@example.com',
        outcome: 'no_match',
        reason: 'Marketing emails are filtered out',
        canonicalEvent: {
          publisher: 'email',
          resource: { type: 'message', id: 'email_123' },
          action: 'received',
          summary: 'Email from newsletter@example.com'
        }
      },
      {
        id: 2,
        description: 'Email from CEO: "FYI draft for later"',
        outcome: 'llm_rejected',
        reason: 'FYI emails are not urgent',
        canonicalEvent: {
          publisher: 'email',
          resource: { type: 'message', id: 'email_456' },
          action: 'received',
          summary: 'Email from CEO: "FYI draft for later"'
        }
      },
      {
        id: 3,
        description: 'Email from CEO: "Board slides for tomorrow"',
        outcome: 'approved',
        reason: 'Urgent request from leadership',
        canonicalEvent: {
          publisher: 'email',
          resource: { type: 'message', id: 'email_789' },
          action: 'received',
          summary: 'Email from CEO: "Board slides for tomorrow"'
        }
      }
    ]
  }
];

const Demo: React.FC = () => {
  const [selectedSubscription, setSelectedSubscription] = useState(demoSubscriptions[0]);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [showProcessing, setShowProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const handleEventProcess = async (event: any) => {
    setSelectedEvent(event);
    setShowProcessing(true);
    setCurrentStep(0);
    
    // Simulate processing steps with delays
    const steps = [
      { name: 'Natural Language → Subject Filter', delay: 1000 },
      { name: 'Ingested Payload → Canonical Format', delay: 1500 },
      { name: 'Pattern Matching', delay: 1000 },
      { name: 'LLM Gate Evaluation', delay: 2000 },
      { name: 'Final Decision', delay: 500 }
    ];
    
    for (let i = 0; i < steps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, steps[i].delay));
      setCurrentStep(i + 1);
    }
    
    // Keep final result visible
    setTimeout(() => {
      setShowProcessing(false);
      setCurrentStep(0);
    }, 3000);
  };

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'no_match': return 'text-red-600 bg-red-50 border-red-200';
      case 'llm_rejected': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'approved': return 'text-green-600 bg-green-50 border-green-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getOutcomeIcon = (outcome: string) => {
    switch (outcome) {
      case 'no_match': return <X size={16} className="text-red-600" />;
      case 'llm_rejected': return <AlertCircle size={16} className="text-yellow-600" />;
      case 'approved': return <Check size={16} className="text-green-600" />;
      default: return null;
    }
  };

  const getOutcomeLabel = (outcome: string) => {
    switch (outcome) {
      case 'no_match': return 'No Match';
      case 'llm_rejected': return 'Rejected by LLM Gate';
      case 'approved': return 'Approved';
      default: return 'Unknown';
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <PlayCircle size={32} className="text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">LangHook Demo Playground</h1>
        </div>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          Understand how LangHook transforms sentences into subscriptions, filters events, and applies intelligent LLM gating.
        </p>
      </div>

      {/* Step 1: Choose Subscription */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center gap-2">
          <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium">1</span>
          Choose a Subscription Sentence
        </h2>
        <p className="text-gray-600 mb-6">Select a natural-language subscription to monitor an event type.</p>
        
        <div className="grid gap-4">
          {demoSubscriptions.map((subscription) => (
            <button
              key={subscription.id}
              onClick={() => setSelectedSubscription(subscription)}
              className={`text-left p-4 rounded-lg border-2 transition-all ${
                selectedSubscription.id === subscription.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <Check size={20} className="text-green-600" />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{subscription.sentence}</div>
                  <div className="text-sm text-gray-500">{subscription.source}</div>
                </div>
                {selectedSubscription.id === subscription.id && (
                  <ArrowRight size={20} className="text-blue-600" />
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Show generated pattern */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Generated Subject Filter:</h3>
          <code className="text-sm font-mono text-blue-600">{selectedSubscription.pattern}</code>
        </div>
      </div>

      {/* Step 2: Send Sample Events */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center gap-2">
          <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium">2</span>
          Send a Sample Event
        </h2>
        <p className="text-gray-600 mb-6">
          Each subscription includes 3 mock events to demonstrate different outcomes:
        </p>
        
        <div className="grid gap-4">
          {selectedSubscription.mockEvents.map((event) => (
            <div
              key={event.id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="font-medium text-gray-900 mb-2">📦 {event.description}</div>
                  <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-medium ${getOutcomeColor(event.outcome)}`}>
                    {getOutcomeIcon(event.outcome)}
                    {getOutcomeLabel(event.outcome)}
                  </div>
                  <div className="text-sm text-gray-600 mt-2">{event.reason}</div>
                </div>
                <button
                  onClick={() => handleEventProcess(event)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
                  disabled={showProcessing}
                >
                  {showProcessing && selectedEvent?.id === event.id ? 'Processing...' : 'Process Event'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Processing Timeline */}
      {showProcessing && selectedEvent && (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
          <h2 className="text-xl font-semibold mb-6 text-gray-800 flex items-center gap-2">
            <Zap size={24} className="text-blue-600" />
            What Happens Inside LangHook
          </h2>
          
          <div className="space-y-6">
            {/* Step 1: Natural Language to Subject Filter */}
            <div className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
              currentStep >= 1 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                currentStep >= 1 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
              }`}>
                1
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-gray-900 flex items-center gap-2">
                  <Filter size={18} />
                  Natural Language → Subject Filter
                </h3>
                <div className="text-sm text-gray-600 mt-1">
                  "{selectedSubscription.sentence}" → <code className="font-mono">{selectedSubscription.pattern}</code>
                </div>
              </div>
              {currentStep >= 1 && <Check size={20} className="text-green-600" />}
            </div>

            {/* Step 2: Payload to Canonical */}
            <div className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
              currentStep >= 2 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                currentStep >= 2 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
              }`}>
                2
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">Ingested Payload → Canonical Format</h3>
                <div className="text-sm text-gray-600 mt-1">
                  Raw webhook data transformed to canonical event structure
                </div>
                {currentStep >= 2 && (
                  <div className="mt-2 p-3 bg-white rounded border text-sm">
                    <pre className="text-xs">{JSON.stringify(selectedEvent.canonicalEvent, null, 2)}</pre>
                  </div>
                )}
              </div>
              {currentStep >= 2 && <Check size={20} className="text-green-600" />}
            </div>

            {/* Step 3: Pattern Matching */}
            <div className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
              currentStep >= 3 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                currentStep >= 3 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
              }`}>
                3
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">Pattern Matching</h3>
                <div className="text-sm text-gray-600 mt-1">
                  Event subject matches subscription pattern: {selectedEvent.outcome !== 'no_match' ? '✅ Yes' : '❌ No'}
                </div>
              </div>
              {currentStep >= 3 && <Check size={20} className="text-green-600" />}
            </div>

            {/* Step 4: LLM Gate */}
            {selectedEvent.outcome !== 'no_match' && (
              <div className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
                currentStep >= 4 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
              }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                  currentStep >= 4 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  4
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 flex items-center gap-2">
                    <Bot size={18} />
                    LLM Gate Evaluation
                  </h3>
                  <div className="text-sm text-gray-600 mt-1">
                    AI evaluates event importance and relevance
                  </div>
                  {currentStep >= 4 && (
                    <div className="mt-2">
                      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${
                        selectedEvent.outcome === 'approved' 
                          ? 'bg-green-100 text-green-800 border border-green-200'
                          : 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                      }`}>
                        {selectedEvent.outcome === 'approved' ? '✅ Approved' : '🚫 Rejected'}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">{selectedEvent.reason}</div>
                    </div>
                  )}
                </div>
                {currentStep >= 4 && <Check size={20} className="text-green-600" />}
              </div>
            )}

            {/* Step 5: Final Decision */}
            <div className={`flex items-center gap-4 p-4 rounded-lg transition-all ${
              currentStep >= 5 ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                currentStep >= 5 ? 'bg-blue-500 text-white' : 'bg-gray-300 text-gray-600'
              }`}>
                5
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">Final Decision</h3>
                {currentStep >= 5 && (
                  <div className="mt-2">
                    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                      selectedEvent.outcome === 'approved'
                        ? 'bg-green-100 text-green-800 border border-green-200'
                        : selectedEvent.outcome === 'llm_rejected'
                        ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                        : 'bg-red-100 text-red-800 border border-red-200'
                    }`}>
                      {getOutcomeIcon(selectedEvent.outcome)}
                      {selectedEvent.outcome === 'approved' && '📬 Message sent to Slack/email'}
                      {selectedEvent.outcome === 'llm_rejected' && '🤖 LLM gate rejected: not significant'}
                      {selectedEvent.outcome === 'no_match' && '📭 Event discarded'}
                    </div>
                  </div>
                )}
              </div>
              {currentStep >= 5 && <Check size={20} className="text-blue-600" />}
            </div>
          </div>
        </div>
      )}

      {/* Bonus Interactions */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">🎛️ Bonus Interactions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="p-4 text-left border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all">
            <div className="font-medium text-gray-900 mb-2">🔁 Replay Events</div>
            <div className="text-sm text-gray-600">Try the same subscription with different events</div>
          </button>
          <button className="p-4 text-left border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all">
            <div className="font-medium text-gray-900 mb-2">🧪 Compare Logic</div>
            <div className="text-sm text-gray-600">See why different events have different outcomes</div>
          </button>
          <button className="p-4 text-left border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all">
            <div className="font-medium text-gray-900 mb-2">📜 Dev Breakdown</div>
            <div className="text-sm text-gray-600">Technical explanation of each processing stage</div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Demo;