import React, { useState, useEffect } from 'react';
// Lucide icons for Sidebar will be managed within Sidebar.tsx
import Dashboard from './Dashboard';
import Events from './Events';
import Subscriptions from './Subscriptions';
import Schema from './Schema';
import Sidebar from './Sidebar'; // Import the new Sidebar component

type TabName = 'Dashboard' | 'Events' | 'Subscriptions' | 'Schema';

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

function App() {
  const [activeTab, setActiveTab] = useState<TabName>('Dashboard');
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);

  useEffect(() => {
    loadSubscriptions();
  }, []);

  const loadSubscriptions = async () => {
    try {
      const response = await fetch('/subscriptions/');
      if (response.ok) {
        const data = await response.json();
        setSubscriptions(data.subscriptions || []);
      } else {
        console.error("Failed to load subscriptions");
      }
    } catch (err) {
      console.error("Error loading subscriptions:", err);
    }
  };

  // TabButton component is removed

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        <div className="container mx-auto">
          {/* Header section - moved inside main content area */}
          <div className="text-center mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-3 text-gray-900 tracking-tight">
              LangHook Demo
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
              Transform webhooks into canonical events with AI-powered mapping
            </p>
          </div>

          {/* Tab Content */}
          {activeTab === 'Dashboard' && (
            <>
              <Dashboard /> {/* Metrics are now exclusively in Dashboard.tsx */}

              {/* "How It Works" section - ensuring consistent card styling */}
              <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8 mt-8">
                <h2 className="text-2xl font-semibold mb-6 text-gray-800 relative pb-3 after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-16 after:h-1 after:bg-blue-600 after:rounded-full tracking-tight">
                  How It Works
                </h2>
                <ol className="list-none space-y-6 sm:space-y-8 pl-1">
                  {[
                    { title: "Webhook Ingestion", text: "Send any webhook to <code>/ingest/{source}</code>" },
                    { title: "Event Transformation", text: "JSONata mappings convert raw payloads to canonical format" },
                    { title: "CloudEvents Wrapper", text: "Events are wrapped in CNCF-compliant envelopes" },
                    { title: "Intelligent Routing", text: "Natural language subscriptions match events to actions" },
                  ].map((item, index) => (
                    <li key={item.title} className="flex items-start group">
                      <div className="mr-3 sm:mr-4 flex-shrink-0 h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-semibold text-base sm:text-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-md">
                        {index + 1}
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-gray-800 mb-1">{item.title}</h3>
                        <p className="text-sm text-gray-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: item.text }} />
                      </div>
                    </li>
                  ))}
                </ol>
                <p className="mt-6 sm:mt-8 text-sm text-gray-700 leading-relaxed">
                  The canonical event format ensures consistency across all webhook sources,
                  making it easy to create powerful automation and monitoring rules.
                </p>
              </div>
            </>
          )}

          {activeTab === 'Events' && <Events subscriptions={subscriptions} />}
          {activeTab === 'Subscriptions' && <Subscriptions subscriptions={subscriptions} refreshSubscriptions={loadSubscriptions} />}
          {activeTab === 'Schema' && <Schema />}
        </div>
      </main>
    </div>
  );
}

export default App;