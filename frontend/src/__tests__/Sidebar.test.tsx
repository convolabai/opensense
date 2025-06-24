import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Sidebar from '../Sidebar';

const mockProps = {
  activeTab: 'Dashboard' as const,
  setActiveTab: jest.fn(),
  isMobileMenuOpen: false,
  setIsMobileMenuOpen: jest.fn(),
  isCollapsed: false,
  setIsCollapsed: jest.fn(),
};

describe('Sidebar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders sidebar with all navigation items', () => {
    render(<Sidebar {...mockProps} />);
    
    expect(screen.getByText('LangHook')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
    expect(screen.getByText('Subscriptions')).toBeInTheDocument();
    expect(screen.getByText('Schema')).toBeInTheDocument();
    expect(screen.getByText('Ingest Mapping')).toBeInTheDocument();
  });

  test('shows collapse button and handles collapse toggle', () => {
    render(<Sidebar {...mockProps} />);
    
    // Find the collapse button
    const collapseButton = screen.getByTitle('Collapse sidebar');
    expect(collapseButton).toBeInTheDocument();
    
    // Click the collapse button
    fireEvent.click(collapseButton);
    
    // Verify setIsCollapsed was called with true
    expect(mockProps.setIsCollapsed).toHaveBeenCalledWith(true);
  });

  test('renders collapsed state correctly', () => {
    const collapsedProps = { ...mockProps, isCollapsed: true };
    render(<Sidebar {...collapsedProps} />);
    
    // LangHook title should have 'hidden' class when collapsed
    const title = screen.getByText('LangHook');
    expect(title).toHaveClass('hidden');
    
    // Expand button should be shown
    expect(screen.getByTitle('Expand sidebar')).toBeInTheDocument();
    
    // Navigation items should still be in DOM but icons only (no text visible based on CSS)
    // The items are still present but styled differently when collapsed
    const dashboardButton = screen.getByTitle('Dashboard');
    expect(dashboardButton).toBeInTheDocument();
  });

  test('handles tab click correctly', () => {
    render(<Sidebar {...mockProps} />);
    
    // Click on Subscriptions tab
    const subscriptionsButton = screen.getByText('Subscriptions');
    fireEvent.click(subscriptionsButton);
    
    // Verify setActiveTab was called with 'Subscriptions'
    expect(mockProps.setActiveTab).toHaveBeenCalledWith('Subscriptions');
  });
});