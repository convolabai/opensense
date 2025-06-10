import React from 'react';
import Demo from './Demo';

function DemoApp() {
  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 md:p-8">
        <div className="container mx-auto">
          {/* Header section for demo */}
          <div className="text-center mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-3 text-gray-900 tracking-tight">
              LangHook Interactive Demo
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
              Interactive demonstration of how LangHook transforms natural language into event subscriptions and applies intelligent LLM gating
            </p>
          </div>

          <Demo />
        </div>
      </main>
    </div>
  );
}

export default DemoApp;