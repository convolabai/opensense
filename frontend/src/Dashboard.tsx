import React, { useState, useEffect } from 'react';
import { BarChart3, RefreshCw } from 'lucide-react';

interface Metrics {
  events_processed: number;
  events_mapped: number;
  events_failed: number;
  llm_invocations: number;
  mapping_success_rate: number;
  llm_usage_rate: number;
}

const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  const loadMetrics = async () => {
    try {
      const response = await fetch('/map/metrics/json');
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      } else {
        console.error("Failed to load metrics:", response.status);
        // Optionally set an error state here to display in the UI
      }
    } catch (err) {
      console.error("Error loading metrics:", err);
      // Optionally set an error state here
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 sm:p-8 mb-8">
      <h2 className="flex items-center gap-3 text-xl sm:text-2xl font-semibold mb-6 text-gray-800 tracking-tight">
        <BarChart3 size={24} className="text-blue-600" />
        System Metrics
        <button
          className="ml-auto py-1 px-3 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 active:scale-95 text-white shadow-sm text-xs"
          onClick={loadMetrics}
          aria-label="Refresh metrics"
        >
          <RefreshCw size={12} />
        </button>
      </h2>

      {metrics ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { label: "Events Processed", value: metrics.events_processed },
            { label: "Events Mapped", value: metrics.events_mapped },
            { label: "Events Failed", value: metrics.events_failed },
            { label: "Success Rate", value: `${(metrics.mapping_success_rate * 100).toFixed(1)}%` },
            { label: "LLM Invocations", value: metrics.llm_invocations },
            { label: "LLM Usage Rate", value: `${(metrics.llm_usage_rate * 100).toFixed(1)}%` },
          ].map(metric => (
            <div key={metric.label} className="bg-white p-4 sm:p-5 rounded-lg shadow border border-gray-200 transition-all hover:shadow-sm hover:-translate-y-px">
              <div className="text-3xl sm:text-4xl font-bold text-blue-600 mb-1">
                {metric.value}
              </div>
              <div className="text-sm text-gray-500 uppercase tracking-wider">{metric.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-gray-500 py-8 sm:py-12 text-lg">Loading metrics...</div>
      )}
    </div>
  );
};

export default Dashboard;
