import React from 'react';
import { LayoutDashboard, ListChecks, MailQuestion, BookOpen, GitMerge, X, ChevronLeft, ChevronRight } from 'lucide-react';

type TabName = 'Dashboard' | 'Events' | 'Subscriptions' | 'Schema' | 'Ingest Mapping';

interface SidebarProps {
  activeTab: TabName;
  setActiveTab: (tab: TabName) => void;
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (isOpen: boolean) => void;
  isCollapsed: boolean;
  setIsCollapsed: (isCollapsed: boolean) => void;
}

const navItems = [
  { name: 'Dashboard', icon: LayoutDashboard },
  { name: 'Events', icon: ListChecks },
  { name: 'Subscriptions', icon: MailQuestion },
  { name: 'Schema', icon: BookOpen },
  { name: 'Ingest Mapping', icon: GitMerge },
];

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, isMobileMenuOpen, setIsMobileMenuOpen, isCollapsed, setIsCollapsed }) => {
  const handleTabClick = (tabName: TabName) => {
    setActiveTab(tabName);
    // Close mobile menu when a tab is selected
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed md:static inset-y-0 left-0 z-50 
        ${isCollapsed ? 'w-16' : 'w-64'} h-screen bg-gray-100 text-gray-800 p-4 space-y-2 border-r border-gray-200
        transform transition-all duration-300 ease-in-out md:transform-none
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Mobile close button and header */}
        <div className="flex items-center justify-between mb-6 md:block">
          <h2 className={`text-xl font-semibold text-gray-800 ${isCollapsed ? 'hidden' : ''}`}>
            LangHook
          </h2>
          <button
            onClick={() => setIsMobileMenuOpen(false)}
            className="md:hidden p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-md"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Desktop collapse button */}
        <div className="hidden md:flex justify-end mb-4">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-md transition-colors"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
        
        <nav>
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.name}>
                <button
                  onClick={() => handleTabClick(item.name as TabName)}
                  className={`flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ease-in-out
                              ${activeTab === item.name
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-600 hover:bg-gray-200 hover:text-gray-900'}
                              ${isCollapsed ? 'justify-center' : ''}`}
                  title={isCollapsed ? item.name : undefined}
                >
                  <item.icon size={20} />
                  {!isCollapsed && item.name}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </>
  );
};

export default Sidebar;
