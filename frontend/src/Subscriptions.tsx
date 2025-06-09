import React, { useState } from 'react'; // useEffect might not be needed if no initial data fetch is done here
import { Plus, Eye, RefreshCw, Bell, Trash2 } from 'lucide-react';

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
  const [deletingSubscriptionId, setDeletingSubscriptionId] = useState<number | null>(null);

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

  const deleteSubscription = async (subscriptionId: number) => {
    if (!window.confirm('Are you sure you want to delete this subscription? This action cannot be undone.')) {
      return;
    }

    setDeletingSubscriptionId(subscriptionId);
    setSubscriptionError('');
    setSubscriptionSuccess('');

    try {
      const response = await fetch(`/subscriptions/${subscriptionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete subscription' }));
        throw new Error(errorData.detail || 'Failed to delete subscription');
      }

      setSubscriptionSuccess('Subscription deleted successfully');
      await refreshSubscriptions();

    } catch (err) {
      setSubscriptionError(err instanceof Error ? err.message : 'Failed to delete subscription');
    } finally {
      setDeletingSubscriptionId(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Create Subscription Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <h2 className="flex items-center gap-3 text-xl font-semibold mb-6 text-gray-800 tracking-tight">
          <Plus size={24} className="text-blue-600" />
          Create New Subscription
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
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

          <div>
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
        </div>

        <div className="mt-6">
          <button
            className="w-full sm:w-auto py-2 px-6 rounded-md font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
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
        </div>

        {subscriptionError && <div className="p-4 rounded-md mt-6 text-sm bg-red-100 border-red-400 text-red-700">{subscriptionError}</div>}
        {subscriptionSuccess && <div className="p-4 rounded-md mt-6 text-sm bg-green-100 border-green-400 text-green-700">{subscriptionSuccess}</div>}
      </div>

      {/* Active Subscriptions Table Section */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="flex items-center gap-3 text-xl font-semibold text-gray-800 tracking-tight">
            <Eye size={24} className="text-blue-600" />
            Active Subscriptions
          </h2>
          <button
            className="py-1 px-3 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm text-xs"
            onClick={refreshSubscriptions}
            aria-label="Refresh subscriptions"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        </div>

        {subscriptions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    NATS Pattern
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {subscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div className="max-w-xs truncate" title={sub.description}>
                        {sub.description}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-700">
                      <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                        {sub.pattern}
                      </code>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {sub.active ? (
                        <span className="text-green-600 flex items-center gap-1">
                          <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                          Active
                        </span>
                      ) : (
                        <span className="text-red-600 flex items-center gap-1">
                          <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <button
                        className="text-red-600 hover:text-red-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => deleteSubscription(sub.id)}
                        disabled={deletingSubscriptionId === sub.id}
                        title="Delete subscription"
                      >
                        {deletingSubscriptionId === sub.id ? (
                          <div className="w-4 h-4 border-2 border-red-600/50 border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <Trash2 size={16} />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-500 py-16 sm:py-20 text-base">
            No subscriptions yet. Create your first subscription above!
          </div>
        )}
      </div>
    </div>
  );
};

export default Subscriptions;
