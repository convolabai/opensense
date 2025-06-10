import React from 'react';
import { LayoutDashboard, ListChecks, MailQuestion, BookOpen, GitMerge } from 'lucide-react';

type TabName = 'Dashboard' | 'Events' | 'Subscriptions' | 'Schema' | 'Ingest Mapping';

interface SidebarProps {
  activeTab: TabName;
  setActiveTab: (tab: TabName) => void;
}

const navItems = [
  { name: 'Dashboard', icon: LayoutDashboard },
  { name: 'Events', icon: ListChecks },
  { name: 'Subscriptions', icon: MailQuestion },
  { name: 'Schema', icon: BookOpen },
  { name: 'Ingest Mapping', icon: GitMerge },
];

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  return (
    <div className="w-64 h-screen bg-gray-100 text-gray-800 p-4 space-y-2 border-r border-gray-200">
      {/* Potentially a logo/header area */}
      <h2 className="text-xl font-semibold text-gray-800 mb-6">LangHook</h2>
      <nav>
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.name}>
              <button
                onClick={() => setActiveTab(item.name as TabName)}
                className={`flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out
                            ${activeTab === item.name
                              ? 'bg-blue-600 text-white'
                              : 'text-gray-600 hover:bg-gray-200 hover:text-gray-900'}`}
              >
                <item.icon size={20} />
                {item.name}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;
