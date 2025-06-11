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
    gate: null,
    created_at: '2023-01-02T00:00:00Z'
  }
];

const mockRefreshSubscriptions = jest.fn();

describe('Subscriptions Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders subscription table with compact columns', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Check that the main table headers are present
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('LLM Gate')).toBeInTheDocument();
    expect(screen.getByText('Notification Type')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();

    // Check that old headers are not present
    expect(screen.queryByText('Subject Filter')).not.toBeInTheDocument();
    expect(screen.queryByText('Status')).not.toBeInTheDocument();
    expect(screen.queryByText('Created')).not.toBeInTheDocument();
  });

  test('shows subscription data in compact format', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Check subscription descriptions are shown
    expect(screen.getByText('Test subscription for GitHub PRs')).toBeInTheDocument();
    expect(screen.getByText('Test subscription for deployments')).toBeInTheDocument();

    // Check LLM Gate status is shown
    expect(screen.getAllByText('Enabled')).toHaveLength(1);
    expect(screen.getAllByText('Disabled')).toHaveLength(1);

    // Check notification types are shown
    expect(screen.getByText('Webhook')).toBeInTheDocument();
    expect(screen.getByText('Polling')).toBeInTheDocument();
  });

  test('expand/collapse functionality works', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Initially, detailed info should not be visible
    expect(screen.queryByText('Topic Filter')).not.toBeInTheDocument();
    expect(screen.queryByText('LLM Gate Prompt')).not.toBeInTheDocument();

    // Find and click the first expand button (ChevronRight)
    const expandButtons = screen.getAllByTitle('Expand details');
    expect(expandButtons).toHaveLength(2);
    
    fireEvent.click(expandButtons[0]);

    // After expanding, detailed info should be visible
    expect(screen.getByText('Topic Filter')).toBeInTheDocument();
    expect(screen.getByText('LLM Gate Prompt')).toBeInTheDocument();
    expect(screen.getByText('github.pull_request.*')).toBeInTheDocument();
    expect(screen.getByText('Only critical PRs')).toBeInTheDocument();

    // Button should now be a collapse button
    expect(screen.getByTitle('Collapse details')).toBeInTheDocument();

    // Click to collapse
    const collapseButton = screen.getByTitle('Collapse details');
    fireEvent.click(collapseButton);

    // Detailed info should be hidden again
    expect(screen.queryByText('Topic Filter')).not.toBeInTheDocument();
    expect(screen.queryByText('LLM Gate Prompt')).not.toBeInTheDocument();
  });

  test('shows appropriate content in expanded view for subscription without gate', () => {
    render(<Subscriptions subscriptions={mockSubscriptions} refreshSubscriptions={mockRefreshSubscriptions} />);
    
    // Expand the second subscription (without gate)
    const expandButtons = screen.getAllByTitle('Expand details');
    fireEvent.click(expandButtons[1]);

    // Should show topic filter but not LLM gate prompt
    expect(screen.getByText('Topic Filter')).toBeInTheDocument();
    expect(screen.getByText('deploy.*')).toBeInTheDocument();
    expect(screen.queryByText('LLM Gate Prompt')).not.toBeInTheDocument();
  });
});