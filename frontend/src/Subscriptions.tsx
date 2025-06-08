import React, { useState } from 'react'; // useEffect might not be needed if no initial data fetch is done here
import { Plus, Eye, RefreshCw, Bell } from 'lucide-react';

// Interfaces (copied from App.tsx, ensure they are consistent)
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

interface SubscriptionsProps {
  subscriptions: Subscription[];
  refreshSubscriptions: () => Promise<void>;
}

const Subscriptions: React.FC<SubscriptionsProps> = ({ subscriptions, refreshSubscriptions }) => {
  const [subscriptionDescription, setSubscriptionDescription] = useState<string>('');
  const [webhookUrl, setWebhookUrl] = useState<string>('');
  const [isSubscriptionLoading, setIsSubscriptionLoading] = useState(false);
  const [subscriptionError, setSubscriptionError] = useState<string>('');
  const [subscriptionSuccess, setSubscriptionSuccess] = useState<string>('');

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
        channel_config: { url: webhookUrl.trim(), method: 'POST' }
      };

      const response = await fetch('/subscriptions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

      await refreshSubscriptions(); // Call the refresh function passed as a prop

    } catch (err) {
      setSubscriptionError(err instanceof Error ? err.message : 'Failed to create subscription');
    } finally {
      setIsSubscriptionLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* Create Subscription Section */}
      <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 sm:p-8 border border-slate-700">
        <h2 className="flex items-center gap-3 text-2xl sm:text-3xl font-semibold mb-6 text-slate-100">
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
            <> <Bell size={18} /> Create Subscription </>
          )}
        </button>

        {subscriptionError && <div className="p-4 rounded-md mt-6 text-sm bg-red-700/30 border border-red-600 text-red-300 animate-pulse">{subscriptionError}</div>}
        {subscriptionSuccess && <div className="p-4 rounded-md mt-6 text-sm bg-green-700/30 border border-green-600 text-green-300">{subscriptionSuccess}</div>}
      </div>

      {/* Active Subscriptions Section */}
      <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 sm:p-8 border border-slate-700">
        <h2 className="flex items-center gap-3 text-2xl sm:text-3xl font-semibold mb-6 text-slate-100">
          <Eye size={24} className="text-indigo-400" />
          Active Subscriptions
          <button
            className="ml-auto py-1 px-2 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-slate-800 bg-slate-600 hover:bg-slate-500 text-slate-200 border border-slate-500 hover:border-slate-400 text-xs"
            onClick={refreshSubscriptions}
            aria-label="Refresh subscriptions"
          >
            <RefreshCw size={12} />
          </button>
        </h2>

        {subscriptions.length > 0 ? (
            <div className="max-h-[400px] overflow-y-auto space-y-4 pr-2"> {/* Keep max-h or adjust as needed */}
            {subscriptions.map((sub) => (
                <div key={sub.id} className="p-3 sm:p-4 bg-slate-800/70 border border-slate-700/70 rounded-lg shadow">
                <div className="mb-2">
                    <strong className="text-slate-200 text-sm sm:text-base">Description:</strong>
                    <span className="text-slate-300 ml-2 text-sm sm:text-base">{sub.description}</span>
                </div>
                <div className="mb-3">
                    <strong className="text-slate-200 text-sm sm:text-base">NATS Pattern:</strong>
                    <code className="ml-2 bg-slate-700 text-indigo-300 px-2 py-1 rounded-md text-xs sm:text-sm font-mono">
                    {sub.pattern}
                  </code>
                </div>
                  <div className="flex justify-between items-center text-xs sm:text-sm text-slate-400">
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
            <div className="text-center text-slate-400 py-16 sm:py-20 text-lg">
            No subscriptions yet. Create your first subscription!
          </div>
        )}
      </div>
    </div>
  );
};

export default Subscriptions;
