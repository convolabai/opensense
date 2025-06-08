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
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
          <Plus size={24} className="text-blue-600" />
          Create Subscription
        </h2>

        <div className="mb-6">
          <label htmlFor="subDesc" className="block text-sm font-medium text-gray-500 mb-2">
            Natural Language Description:
          </label>
          <textarea
            id="subDesc"
            className="w-full min-h-[100px] bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm transition-colors"
            value={subscriptionDescription}
            onChange={(e) => setSubscriptionDescription(e.target.value)}
            placeholder="e.g., 'GitHub PR opened' or 'Stripe payment > $100 succeeded'"
          />
        </div>

        <div className="mb-6">
          <label htmlFor="webhookUrl" className="block text-sm font-medium text-gray-500 mb-2">
            Webhook URL:
          </label>
          <input
            id="webhookUrl"
            type="url"
            className="w-full bg-gray-50 border-gray-300 text-gray-900 rounded-md p-2.5 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm transition-colors"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://your-service.com/webhook"
          />
        </div>

        <button
          className="w-full py-2 px-4 rounded-md font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={createSubscription}
          disabled={isSubscriptionLoading || !subscriptionDescription.trim() || !webhookUrl.trim()}
        >
          {isSubscriptionLoading ? (
            <span className="flex items-center gap-2">
              <div className="w-5 h-5 border-2 border-white/50 border-t-transparent rounded-full animate-spin" />
              Creating...
            </span>
          ) : (
            <> <Bell size={16} /> Create Subscription </>
          )}
        </button>

        {subscriptionError && <div className="p-4 rounded-md mt-6 text-sm bg-red-100 border-red-400 text-red-700">{subscriptionError}</div>}
        {subscriptionSuccess && <div className="p-4 rounded-md mt-6 text-sm bg-green-100 border-green-400 text-green-700">{subscriptionSuccess}</div>}
      </div>

      {/* Active Subscriptions Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
          <Eye size={24} className="text-blue-600" />
          Active Subscriptions
          <button
            className="ml-auto py-1 px-3 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm text-xs"
            onClick={refreshSubscriptions}
            aria-label="Refresh subscriptions"
          >
            <RefreshCw size={12} />
          </button>
        </h2>

        {subscriptions.length > 0 ? (
            <div className="max-h-[400px] overflow-y-auto space-y-4 pr-2"> {/* Keep max-h or adjust as needed */}
            {subscriptions.map((sub) => (
                <div key={sub.id} className="bg-white rounded-lg shadow border border-gray-200 p-3 sm:p-4 hover:shadow-sm transition-shadow">
                <div className="mb-2">
                    <strong className="text-gray-500 font-semibold text-sm">Description:</strong>
                    <span className="text-gray-800 ml-2 text-sm">{sub.description}</span>
                </div>
                <div className="mb-3">
                    <strong className="text-gray-500 font-semibold text-sm">NATS Pattern:</strong>
                    <code className="ml-2 bg-gray-100 text-gray-700 px-2 py-1 rounded-md text-xs font-mono">
                    {sub.pattern}
                  </code>
                </div>
                  <div className="flex justify-between items-center text-xs text-gray-500">
                  <span>Status: {sub.active ?
                    <span className="text-green-500">🟢 Active</span> :
                    <span className="text-red-500">🔴 Inactive</span>}
                  </span>
                  <span>Created: {new Date(sub.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
            <div className="text-center text-gray-500 py-16 sm:py-20 text-base">
            No subscriptions yet. Create your first subscription!
          </div>
        )}
      </div>
    </div>
  );
};

export default Subscriptions;
