import React, { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import Dashboard from './Dashboard';
import Events from './Events';
import Subscriptions from './Subscriptions';
import Schema from './Schema';
import IngestMapping from './IngestMapping';
import Sidebar from './Sidebar';

type TabName = 'Dashboard' | 'Events' | 'Subscriptions' | 'Schema' | 'Ingest Mapping';

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

function ConsoleApp() {
  const [activeTab, setActiveTab] = useState<TabName>('Dashboard');
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile header with hamburger menu */}
        <div className="md:hidden bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <h1 className="text-lg font-semibold text-gray-800">LangHook Console</h1>
            <div className="w-10"></div> {/* Spacer for center alignment */}
          </div>
        </div>

        {/* Main content area */}
        <div className="flex-1 p-6 md:p-8 overflow-y-auto">
          <div className="container mx-auto">
            {/* Header section - moved inside main content area */}
            <div className="text-center mb-8 hidden md:block">
              <h1 className="text-3xl md:text-4xl font-bold mb-3 text-gray-900 tracking-tight">
                LangHook Console
              </h1>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
                Transform webhooks into canonical events with AI-powered mapping
              </p>
            </div>

          {activeTab === 'Dashboard' && (
            <>
              <Dashboard />

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
          {activeTab === 'Ingest Mapping' && <IngestMapping />}
        </div>
      </div>
    </main>
    </div>
  );
}

export default ConsoleApp;