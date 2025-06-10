import React, { useState } from 'react';
import { Check, X, ArrowRight, Zap, Bot, Smartphone, BellRing } from 'lucide-react';
import { samplePayloads } from './sampleWebhookPayloads';

// Mapping from display source names to API endpoint source names
const sourceMapping: { [key: string]: string } = {
  'GitHub': 'github',
  'Stripe': 'stripe', 
  'Jira': 'jira',
  'Slack': 'slack',
  'Email': 'email'
};

// Demo-specific subscription sentences and their mock events
const demoSubscriptions = [
  {
    id: 'github_pr_approved',
    sentence: 'Notify me when PR 1374 is approved',
    source: 'GitHub',
    pattern: 'langhook.events.github.pull_request.1374.updated',
    llmGatePrompt: 'Approve if this GitHub pull request event represents an approval for PR #1374 specifically',
    mockEvents: [
      {
        id: 1,
        description: 'PR 1234 approved by Alice',
        outcome: 'no_match',
        reason: 'Different PR number (1234 vs 1374)',
        rawPayloadKey: 'github_pr_review_1234_approved',
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
        rawPayloadKey: 'github_pr_review_1374_title_change',
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
        rawPayloadKey: 'github_pr_review_1374_approved',
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
    sentence: 'Alert me when there is a Stripe refund with > $500 value',
    source: 'Stripe',
    pattern: 'langhook.events.stripe.refund.*.created',
    llmGatePrompt: 'Approve if this Stripe refund is more than $500 in value for a real customer transaction, not test data',
    mockEvents: [
      {
        id: 1,
        description: 'Refund of $100 issued',
        outcome: 'no_match',
        reason: 'Amount too low for high-value threshold',
        rawPayloadKey: 'stripe_refund_low_value',
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
        reason: 'Test transactions are not relevant',
        rawPayloadKey: 'stripe_refund_high_value_test',
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
        rawPayloadKey: 'stripe_refund_high_value_real',
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
    llmGatePrompt: 'Assess if this Jira issue update represents a ticket being properly moved to "Done" status by an authorized team member.',
    mockEvents: [
      {
        id: 1,
        description: 'Ticket moved to "In Progress"',
        outcome: 'no_match',
        reason: 'Status changed but not to Done',
        rawPayloadKey: 'jira_issue_to_in_progress',
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
        rawPayloadKey: 'jira_issue_done_unassigned',
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
        rawPayloadKey: 'jira_issue_done_by_owner',
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
    llmGatePrompt: 'Evaluate if this Slack file upload event contains an important business document rather than casual or irrelevant files.',
    mockEvents: [
      {
        id: 1,
        description: 'Message posted (not a file)',
        outcome: 'no_match',
        reason: 'Not a file upload event',
        rawPayloadKey: 'slack_message_not_file',
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
        rawPayloadKey: 'slack_file_upload_no_context',
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
        rawPayloadKey: 'slack_file_upload_important',
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
    llmGatePrompt: 'Determine if this email event represents an important message that requires immediate attention, rather than routine or marketing emails.',
    mockEvents: [
      {
        id: 1,
        description: 'Email from newsletter@example.com',
        outcome: 'no_match',
        reason: 'Marketing emails are filtered out',
        rawPayloadKey: 'email_newsletter',
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
        rawPayloadKey: 'email_fyi_from_ceo',
        canonicalEvent: {
          publisher: 'email',
          resource: { type: 'message', id: 'email_456' },
          action: 'received',
          summary: 'Email from CEO: "FYI draft for later"'
        }
      },
      {
        id: 3,
        description: 'Email from important client: "URGENT: System down"',
        outcome: 'approved',
        reason: 'Urgent request from important client',
        rawPayloadKey: 'email_urgent_from_client',
        canonicalEvent: {
          publisher: 'email',
          resource: { type: 'message', id: 'email_789' },
          action: 'received',
          summary: 'Email from important client: "URGENT: System down"'
        }
      }
    ]
  }
];

const Demo: React.FC = () => {
  const [selectedSubscription, setSelectedSubscription] = useState(demoSubscriptions[0]);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [selectedEventForIngest, setSelectedEventForIngest] = useState<any>(null);
  const [showProcessing, setShowProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [hasAddedSubscription, setHasAddedSubscription] = useState(false);
  const [isAddingSubscription, setIsAddingSubscription] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [loadingSteps, setLoadingSteps] = useState<Set<number>>(new Set());

  const handleAddSubscription = async () => {
    setIsAddingSubscription(true);
    
    // Show loading for 1 second
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setIsAddingSubscription(false);
    setHasAddedSubscription(true);
  };

  const handleStartOver = () => {
    setSelectedSubscription(demoSubscriptions[0]);
    setSelectedEvent(null);
    setSelectedEventForIngest(null);
    setShowProcessing(false);
    setCurrentStep(0);
    setHasAddedSubscription(false);
    setIsAddingSubscription(false);
    setProcessingComplete(false);
    setIsIngesting(false);
    setLoadingSteps(new Set());
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleIngestEvent = async () => {
    if (!selectedEventForIngest) return;
    
    setIsIngesting(true);
    setSelectedEvent(selectedEventForIngest);
    setShowProcessing(true);
    setCurrentStep(0);
    setProcessingComplete(false);
    setLoadingSteps(new Set([1])); // Set stage 1 to loading immediately
    
    // Scroll to the processing section
    setTimeout(() => {
      const processingSection = document.querySelector('[data-processing-section]');
      if (processingSection) {
        processingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
    
    // Simulate processing steps with delays, starting from ingestion
    const steps = [
      { name: 'Ingested Payload → Canonical Format', delay: 1500 },
      { name: 'Pattern Matching', delay: 1000 },
      { name: 'LLM Gate Evaluation', delay: 2000 },
      { name: 'Final Decision', delay: 500 }
    ];
    
    for (let i = 0; i < steps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, steps[i].delay));
      setCurrentStep(i + 1);
      // Clear loading state for this step and set loading for next step (if any)
      setLoadingSteps(prev => {
        const newSet = new Set(prev);
        newSet.delete(i + 1);
        if (i + 1 < steps.length) {
          newSet.add(i + 2);
        }
        return newSet;
      });
    }
    
    // Keep final result visible and show completion
    setProcessingComplete(true);
    setIsIngesting(false);
    setLoadingSteps(new Set()); // Clear all loading states
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">

      {/* Steps 1 and 2 in same row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Step 1: Choose Subscription */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 md:p-6">
          <h2 className="text-lg md:text-xl font-semibold mb-2 text-gray-800 flex items-center gap-2">
            <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium">1</span>
            Subscribe using natural language
          </h2>
          <p className="text-sm md:text-base text-gray-600 mb-6">Enter a natural language query to create an event subscription.</p>
          
          <div className="grid gap-3 md:gap-4">
            {(!hasAddedSubscription && !isAddingSubscription ? demoSubscriptions : [selectedSubscription]).map((subscription) => (
              <button
                key={subscription.id}
                onClick={() => !isAddingSubscription && !hasAddedSubscription && setSelectedSubscription(subscription)}
                disabled={isAddingSubscription || hasAddedSubscription}
                className={`text-left p-3 md:p-4 rounded-lg border-2 transition-all ${
                  selectedSubscription.id === subscription.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                } ${isAddingSubscription || hasAddedSubscription ? 'opacity-75 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-center gap-3">
                  <Check size={18} className="text-green-600 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 text-sm md:text-base">"{subscription.sentence}"</div>
                    <div className="text-xs md:text-sm text-gray-500">{subscription.source}</div>
                  </div>
                  {selectedSubscription.id === subscription.id && (
                    <ArrowRight size={18} className="text-blue-600 flex-shrink-0" />
                  )}
                </div>
              </button>
            ))}
          </div>

          {/* Add subscription button */}
          <div className="mt-6">
            <button
              onClick={handleAddSubscription}
              className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-75 disabled:cursor-not-allowed"
              disabled={hasAddedSubscription || isAddingSubscription}
            >
              {hasAddedSubscription ? '✓ Subscription Added' : 
               isAddingSubscription ? (
                 <span className="flex items-center justify-center gap-2">
                   <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" />
                   Adding Subscription...
                 </span>
               ) : 'Add Subscription'}
            </button>
          </div>

          {/* Show combined generated pattern and LLM Gate prompt */}
          {hasAddedSubscription && (
            <div className="mt-4">
              <div className="p-4 bg-gray-50 rounded-lg border">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Generated Subject Filter:</h3>
                <code className="text-sm font-mono text-blue-600 mb-4 block">{selectedSubscription.pattern}</code>
                
                <h3 className="text-sm font-medium text-gray-700 mb-1">LLM Gate Prompt:</h3>
                <p className="text-xs text-gray-500 mb-2">Evaluate all matching events using this prompt</p>
                <blockquote className="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50 rounded-r-lg">
                  <p className="text-sm text-gray-700 italic">"{selectedSubscription.llmGatePrompt}"</p>
                </blockquote>
              </div>
            </div>
          )}
        </div>

        {/* Step 2: Ingest new event (only show after subscription added) */}
        {hasAddedSubscription && (
          <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 md:p-6">
            <h2 className="text-lg md:text-xl font-semibold mb-2 text-gray-800 flex items-center gap-2">
              <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium">2</span>
              Ingest new event
            </h2>
            <p className="text-sm md:text-base text-gray-600 mb-6">
              Source systems send webhook events to LangHook's /ingest/ endpoint. Select an event to see its raw JSON payload, then ingest it:
            </p>
            
            <div className="grid gap-3 md:gap-4 mb-6">
              {selectedSubscription.mockEvents.map((event) => (
                <div
                  key={event.id}
                  className={`border rounded-lg p-3 md:p-4 transition-all cursor-pointer ${
                    selectedEventForIngest?.id === event.id 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                  onClick={() => setSelectedEventForIngest(event)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 mb-2 text-sm md:text-base flex items-center gap-2">
                        <span className={`w-4 h-4 rounded-full border-2 ${
                          selectedEventForIngest?.id === event.id 
                            ? 'border-blue-500 bg-blue-500' 
                            : 'border-gray-300'
                        }`}>
                          {selectedEventForIngest?.id === event.id && (
                            <Check size={12} className="text-white" />
                          )}
                        </span>
                        📦 {event.description}
                      </div>
                      
                      {selectedEventForIngest?.id === event.id && (
                        <div className="mt-3">
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Ingestion Endpoint:</h4>
                          <div className="bg-blue-50 border border-blue-200 p-3 rounded-md mb-4">
                            <code className="text-sm font-mono text-blue-700">POST /ingest/{sourceMapping[selectedSubscription.source] || selectedSubscription.source.toLowerCase()}</code>
                          </div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Raw JSON Event:</h4>
                          <div className="bg-gray-800 text-gray-200 p-3 rounded-md font-mono text-xs overflow-x-auto max-h-40">
                            <pre>{JSON.stringify(event.rawPayloadKey ? samplePayloads[event.rawPayloadKey]?.payload : event.canonicalEvent, null, 2)}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Single Ingest Event button at bottom */}
            <div className="text-center">
              <button
                onClick={handleIngestEvent}
                disabled={!selectedEventForIngest || isIngesting}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isIngesting ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" />
                    Processing Event...
                  </span>
                ) : (
                  'Ingest Event'
                )}
              </button>
              {!selectedEventForIngest && (
                <p className="text-sm text-gray-500 mt-2">Select an event above to ingest</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Step 3: Processing Timeline - Full width, horizontal layout */}
      {showProcessing && selectedEvent && (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6" data-processing-section>
          <h2 className="text-xl font-semibold mb-6 text-gray-800 flex items-center gap-2">
            <Zap size={24} className="text-blue-600" />
            What Happens Inside LangHook
          </h2>
          
          {/* Horizontal steps layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Step 1: Payload to Canonical */}
            <div className={`p-4 rounded-lg transition-all ${
              currentStep >= 1 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep >= 1 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  1
                </div>
                <h3 className="font-medium text-gray-900 text-sm">Ingestion</h3>
              </div>
              <div className="text-xs text-gray-600 mb-2">
                Raw webhook → Canonical format
              </div>
              {(currentStep >= 1 || loadingSteps.has(1)) && (
                <div className="text-xs bg-white rounded border p-2 min-h-[4rem]">
                  {loadingSteps.has(1) ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-center gap-2 py-2">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                        <span className="text-gray-600">Processing...</span>
                      </div>
                      <div className="border-t pt-2">
                        <div className="text-xs font-medium text-gray-700 mb-1">Raw Payload:</div>
                        <pre className="text-xs break-words whitespace-pre-wrap text-gray-600 max-h-20 overflow-y-auto">{JSON.stringify(selectedEventForIngest?.rawPayloadKey ? samplePayloads[selectedEventForIngest.rawPayloadKey]?.payload : selectedEventForIngest?.canonicalEvent, null, 1)}</pre>
                      </div>
                    </div>
                  ) : (
                    <pre className="text-xs break-words whitespace-pre-wrap">{JSON.stringify(selectedEvent.canonicalEvent, null, 1)}</pre>
                  )}
                </div>
              )}
              {currentStep >= 1 && <Check size={16} className="text-green-600 mt-2" />}
            </div>

            {/* Step 2: Pattern Matching */}
            <div className={`p-4 rounded-lg transition-all ${
              currentStep >= 2 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep >= 2 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  2
                </div>
                <h3 className="font-medium text-gray-900 text-sm">Pattern Match</h3>
              </div>
              <div className="text-xs text-gray-600 mb-2">
                Subject vs subscription filter
              </div>
              {(currentStep >= 2 || loadingSteps.has(2)) && (
                <div className="text-xs space-y-2">
                  {loadingSteps.has(2) ? (
                    <div className="flex items-center justify-center gap-2 py-4">
                      <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      <span className="text-gray-600">Matching patterns...</span>
                    </div>
                  ) : (
                    <>
                      <div className="bg-white rounded border p-2">
                        <div className="font-medium text-gray-700 mb-1">Canonical Event Subject:</div>
                        <code className="text-xs text-blue-600 block break-words whitespace-normal">langhook.events.{selectedEvent.canonicalEvent.publisher}.{selectedEvent.canonicalEvent.resource.type}.{selectedEvent.canonicalEvent.resource.id}.{selectedEvent.canonicalEvent.action}</code>
                      </div>
                      <div className="bg-white rounded border p-2">
                        <div className="font-medium text-gray-700 mb-1">Subscription Filter:</div>
                        <code className="text-xs text-purple-600 block break-words whitespace-normal">{selectedSubscription.pattern}</code>
                      </div>
                      <div className={`px-2 py-1 rounded ${selectedEvent.outcome !== 'no_match' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {selectedEvent.outcome !== 'no_match' ? '✅ Match' : '❌ No match'}
                      </div>
                    </>
                  )}
                </div>
              )}
              {currentStep >= 2 && <Check size={16} className="text-green-600 mt-2" />}
            </div>

            {/* Step 3: LLM Gate (conditional) */}
            {selectedEvent.outcome !== 'no_match' && (
              <div className={`p-4 rounded-lg transition-all ${
                currentStep >= 3 ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
              }`}>
                <div className="flex items-center gap-2 mb-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                    currentStep >= 3 ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                  }`}>
                    3
                  </div>
                  <div className="flex items-center gap-1">
                    <Bot size={14} />
                    <h3 className="font-medium text-gray-900 text-sm">LLM Gate</h3>
                  </div>
                </div>
                <div className="text-xs text-gray-600 mb-2">
                  AI relevance evaluation
                </div>
                {(currentStep >= 3 || loadingSteps.has(3)) && (
                  <div className="text-xs space-y-2">
                    {loadingSteps.has(3) ? (
                      <div className="flex items-center justify-center gap-2 py-4">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                        <span className="text-gray-600">AI evaluating...</span>
                      </div>
                    ) : (
                      <>
                        <div className="bg-white rounded border p-2">
                          <div className="font-medium text-gray-700 mb-1">LLM Gate Prompt:</div>
                          <blockquote className="border-l-2 border-blue-400 pl-2 text-gray-600 italic text-xs">
                            "{selectedSubscription.llmGatePrompt}"
                          </blockquote>
                        </div>
                        <div className={`px-2 py-1 rounded text-xs ${
                          selectedEvent.outcome === 'approved' 
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {selectedEvent.outcome === 'approved' ? '✅ Approved' : '🚫 Rejected'}
                        </div>
                        <div className="text-xs text-gray-600">{selectedEvent.reason}</div>
                      </>
                    )}
                  </div>
                )}
                {currentStep >= 3 && <Check size={16} className="text-green-600 mt-2" />}
              </div>
            )}

            {/* Step 4: Final Decision */}
            <div className={`p-4 rounded-lg transition-all ${
              currentStep >= 4 ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep >= 4 ? 'bg-blue-500 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  4
                </div>
                <h3 className="font-medium text-gray-900 text-sm">Final Action</h3>
              </div>
              <div className="text-xs text-gray-600 mb-2">
                Notification decision
              </div>
              {(currentStep >= 4 || loadingSteps.has(4)) && (
                <div className="text-xs space-y-2">
                  {loadingSteps.has(4) ? (
                    <div className="flex items-center justify-center gap-2 py-4">
                      <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      <span className="text-gray-600">Finalizing...</span>
                    </div>
                  ) : (
                    <>
                      {selectedEvent.outcome === 'approved' && (
                        <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                          <div className="flex items-center gap-2 mb-2">
                            <Smartphone size={16} className="text-green-600" />
                            <span className="font-medium text-green-800">Notification Sent</span>
                          </div>
                          <div className="bg-white rounded border p-2 shadow-sm">
                            <div className="flex items-start gap-2">
                              <BellRing size={12} className="text-blue-500 mt-0.5" />
                              <div>
                                <div className="font-medium text-xs text-gray-900">LangHook Alert</div>
                                <div className="text-xs text-gray-600">{selectedEvent.canonicalEvent.summary}</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      {selectedEvent.outcome === 'llm_rejected' && (
                        <div className="bg-yellow-50 rounded-lg p-3 border border-yellow-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Bot size={16} className="text-yellow-600" />
                            <span className="font-medium text-yellow-800">AI Filtered</span>
                          </div>
                          <div className="text-xs text-yellow-700">Event matched pattern but was deemed not relevant by LLM</div>
                        </div>
                      )}
                      {selectedEvent.outcome === 'no_match' && (
                        <div className="bg-red-50 rounded-lg p-3 border border-red-200">
                          <div className="flex items-center gap-2 mb-1">
                            <X size={16} className="text-red-600" />
                            <span className="font-medium text-red-800">Discarded</span>
                          </div>
                          <div className="text-xs text-red-700">Event did not match subscription pattern</div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
              {currentStep >= 4 && <Check size={16} className="text-blue-600 mt-2" />}
            </div>
          </div>
          
          {/* Start Over button when processing is complete */}
          {processingComplete && (
            <div className="mt-6 text-center">
              <button
                onClick={handleStartOver}
                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                🔄 Start Over
              </button>
              <p className="text-sm text-gray-600 mt-2">
                Try again or choose different events to ingest
              </p>
            </div>
          )}
        </div>
      )}

    </div>
  );
};

export default Demo;