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
    <div className="bg-slate-800/95 backdrop-blur-md rounded-xl shadow-2xl p-6 sm:p-8 border border-slate-700 mb-8">
      <h2 className="flex items-center gap-3 text-2xl sm:text-3xl font-semibold mb-6 text-slate-100">
        <BarChart3 size={24} sm:size={28} className="text-indigo-400" />
        System Metrics
        <button
          className="ml-auto py-1 px-2 rounded-md font-semibold flex items-center justify-center gap-1 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-slate-800 bg-slate-600 hover:bg-slate-500 text-slate-200 border border-slate-500 hover:border-slate-400 text-xs"
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
            <div key={metric.label} className="bg-slate-800/70 p-4 sm:p-5 rounded-lg shadow border border-slate-700/70 transition-all hover:shadow-lg hover:-translate-y-0.5">
              <div className="text-3xl sm:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-400 mb-1">
                {metric.value}
              </div>
              <div className="text-sm sm:text-base text-slate-400 uppercase tracking-wider">{metric.label}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-slate-400 py-8 sm:py-12 text-lg">Loading metrics...</div>
      )}
    </div>
  );
};

export default Dashboard;
