import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Subscriptions from '../Subscriptions';

const mockSubscriptions = [
  {
    id: 1,
    subscriber_id: 'test-user',
    description: 'Test subscription for GitHub PRs',
    pattern: 'github.pull_request.*',
    channel_type: 'webhook',
    channel_config: { url: 'https://example.com/webhook' },
    active: true,
    disposable: false,
    used: false,
    gate: {
      enabled: true,
      prompt: 'Only critical PRs'
    },
    created_at: '2023-01-01T00:00:00Z'
  },
  {
    id: 2,
    subscriber_id: 'test-user',
    description: 'Test subscription for deployments',
    pattern: 'deploy.*',
    channel_type: null,
    channel_config: null,
    active: true,
    disposable: false,
    used: false,
    gate: null,
    created_at: '2023-01-02T00:00:00Z'
  }
];

const mockRefreshSubscriptions = jest.fn();

describe('Subscriptions Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders subscription table with new columns', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Check that the new table headers are present
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Topic Filter')).toBeInTheDocument();
    expect(screen.getByText('Create Time')).toBeInTheDocument();
    expect(screen.getByText('LLM Gate')).toBeInTheDocument();
    expect(screen.getByText('Notification Type')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();

    // Check that old headers are not present
    expect(screen.queryByText('Subject Filter')).not.toBeInTheDocument();
    expect(screen.queryByText('Status')).not.toBeInTheDocument();
    expect(screen.queryByText('Created')).not.toBeInTheDocument();
  });

  test('shows subscription data with topic filter and timestamp', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Check subscription descriptions are shown
    expect(screen.getByText('Test subscription for GitHub PRs')).toBeInTheDocument();
    expect(screen.getByText('Test subscription for deployments')).toBeInTheDocument();

    // Check topic filters are shown in table
    expect(screen.getByText('github.pull_request.*')).toBeInTheDocument();
    expect(screen.getByText('deploy.*')).toBeInTheDocument();

    // Check LLM Gate status is shown
    expect(screen.getAllByText('Enabled')).toHaveLength(1);
    expect(screen.getAllByText('Disabled')).toHaveLength(1);

    // Check notification types are shown
    expect(screen.getByText('Webhook')).toBeInTheDocument();
    expect(screen.getByText('Polling')).toBeInTheDocument();

    // Check that timestamps are shown (dates should be converted to local format)
    expect(screen.getByText(/1\/1\/2023/)).toBeInTheDocument(); // 2023-01-01 should show as some date format
    expect(screen.getByText(/1\/2\/2023/)).toBeInTheDocument(); // 2023-01-02 should show as some date format
  });

  test('expand/collapse functionality works', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Topic Filter is now always visible in the main table
    expect(screen.getByText('Topic Filter')).toBeInTheDocument();
    
    // Initially, LLM Gate Prompt should not be visible (it's only in expanded view for enabled gates)
    expect(screen.queryByText('LLM Gate Prompt')).not.toBeInTheDocument();

    // Find and click the second expand button (the subscription with gate enabled, which is now sorted second due to older date)
    const expandButtons = screen.getAllByTitle('Expand details');
    expect(expandButtons).toHaveLength(2);
    
    fireEvent.click(expandButtons[1]); // Click second button since sorting changed order

    // After expanding, LLM Gate Prompt should be visible for the subscription with gate enabled
    expect(screen.getByText('LLM Gate Prompt')).toBeInTheDocument();
    expect(screen.getByText('Only critical PRs')).toBeInTheDocument();

    // Button should now be a collapse button
    expect(screen.getByTitle('Collapse details')).toBeInTheDocument();

    // Click to collapse
    const collapseButton = screen.getByTitle('Collapse details');
    fireEvent.click(collapseButton);

    // LLM Gate Prompt should be hidden again
    expect(screen.queryByText('LLM Gate Prompt')).not.toBeInTheDocument();
  });

  test('shows appropriate content in expanded view for subscription without gate', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Expand the first subscription (without gate - due to sorting, the newer one without gate is first)
    const expandButtons = screen.getAllByTitle('Expand details');
    fireEvent.click(expandButtons[0]);

    // Topic filter is always visible in main table now
    expect(screen.getByText('Topic Filter')).toBeInTheDocument();
    expect(screen.getByText('deploy.*')).toBeInTheDocument();
    
    // LLM Gate Prompt should not be visible for subscription without gate
    expect(screen.queryByText('LLM Gate Prompt')).not.toBeInTheDocument();
  });
});