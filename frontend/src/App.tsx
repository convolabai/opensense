import React, { useState, useEffect } from 'react';
import { LayoutDashboard, ListChecks, MailQuestion } from 'lucide-react'; // Minimal icons needed for App.tsx
import Dashboard from './Dashboard';
import Events from './Events';
import Subscriptions from './Subscriptions';

type TabName = 'Dashboard' | 'Events' | 'Subscriptions';

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

  const TabButton: React.FC<{ name: TabName; icon: React.ElementType }> = ({ name, icon: Icon }) => (
    <button
      onClick={() => setActiveTab(name)}
      className={`flex items-center gap-2 px-4 py-3 font-medium rounded-t-lg transition-all duration-200 ease-in-out
                  ${activeTab === name
                    ? 'bg-slate-800/95 text-indigo-400 border-b-2 border-indigo-500'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'}`}
    >
      <Icon size={18} />
      {name}
    </button>
  );

  return (
    // Main page container with Tailwind styling from the original App.tsx (bg-slate-900, etc.)
    <div className="bg-slate-900 text-slate-100 min-h-screen p-4 md:p-8">
      <div className="container mx-auto">
        {/* Header section from original App.tsx */}
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold mb-3" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            LangHook Demo
          </h1>
          <p className="text-lg md:text-xl text-slate-300 max-w-2xl mx-auto">
            Transform webhooks into canonical events with AI-powered mapping
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-700 mb-8">
          <TabButton name="Dashboard" icon={LayoutDashboard} />
          <TabButton name="Events" icon={ListChecks} />
          <TabButton name="Subscriptions" icon={MailQuestion} />
        </div>

        {/* Tab Content */}
        {activeTab === 'Dashboard' && (
          <>
            <Dashboard /> {/* Metrics are now exclusively in Dashboard.tsx */}

            {/* "How It Works" section - ensuring consistent card styling */}
            <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 sm:p-8 border border-slate-700 mt-8">
              <h2 className="text-2xl sm:text-3xl font-semibold mb-6 text-slate-100 relative pb-3 after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-16 after:h-1 after:bg-gradient-to-r after:from-purple-500 after:to-indigo-500 after:rounded-full">
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
                    <div className="mr-3 sm:mr-4 flex-shrink-0 h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white font-semibold text-base sm:text-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="text-lg sm:text-xl font-semibold text-slate-200 mb-1">{item.title}</h3>
                      <p className="text-slate-400 text-sm sm:text-base" dangerouslySetInnerHTML={{ __html: item.text }} />
                    </div>
                  </li>
                ))}
              </ol>
              <p className="mt-6 sm:mt-8 text-slate-300 text-sm sm:text-base leading-relaxed">
                The canonical event format ensures consistency across all webhook sources,
                making it easy to create powerful automation and monitoring rules.
              </p>
            </div>
          </>
        )}

        {activeTab === 'Events' && <Events subscriptions={subscriptions} />}
        {activeTab === 'Subscriptions' && <Subscriptions subscriptions={subscriptions} refreshSubscriptions={loadSubscriptions} />}

      </div>
    </div>
  );
}

export default App;