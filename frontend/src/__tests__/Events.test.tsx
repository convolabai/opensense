import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Events from '../Events';

// Mock the API fetch
jest.mock('../apiUtils', () => ({
  apiFetch: jest.fn()
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Send: () => <div data-testid="send-icon" />,
  ListChecks: () => <div data-testid="list-checks-icon" />,
  Eye: () => <div data-testid="eye-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />,
  X: () => <div data-testid="x-icon" />
}));

// Mock sample payloads
jest.mock('../sampleWebhookPayloads', () => ({
  samplePayloads: {
    github_pr_opened: {
      source: 'github',
      payload: { action: 'opened', pull_request: { number: 1 } }
    }
  },
  payloadCategories: {}
}));

import { apiFetch } from '../apiUtils';
const mockApiFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;

describe('Events Resource Type Filtering', () => {
  beforeEach(() => {
    mockApiFetch.mockClear();
  });

  test('loads and displays resource type filter', async () => {
    // Mock schema API response
    mockApiFetch.mockImplementation((url) => {
      if (url === '/schema/') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            resource_types: {
              'github': ['pull_request', 'issue'],
              'stripe': ['payment_intent', 'customer']
            }
          })
        });
      }
      // Mock event logs API response
      if (url.includes('/event-logs')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            event_logs: [],
            total: 0,
            page: 1,
            size: 20
          })
        });
      }
      return Promise.reject(new Error('Unknown API call'));
    });

    render(<Events subscriptions={[]} />);

    // Wait for resource types to load
    await waitFor(() => {
      expect(screen.getByText('Filter by Resource Type:')).toBeInTheDocument();
    });

    // Check that resource type buttons are displayed
    expect(screen.getByText('All Types')).toBeInTheDocument();
    expect(screen.getByText('pull_request')).toBeInTheDocument();
    expect(screen.getByText('issue')).toBeInTheDocument();
    expect(screen.getByText('payment_intent')).toBeInTheDocument();
    expect(screen.getByText('customer')).toBeInTheDocument();
  });

  test('filters events by resource type', async () => {
    // Mock schema API response
    mockApiFetch.mockImplementation((url) => {
      if (url === '/schema/') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            resource_types: {
              'github': ['pull_request', 'issue']
            }
          })
        });
      }
      // Mock event logs API response
      if (url.includes('/event-logs')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            event_logs: [],
            total: 0,
            page: 1,
            size: 20
          })
        });
      }
      return Promise.reject(new Error('Unknown API call'));
    });

    render(<Events subscriptions={[]} />);

    // Wait for resource types to load
    await waitFor(() => {
      expect(screen.getByText('pull_request')).toBeInTheDocument();
    });

    // Click on a resource type filter
    fireEvent.click(screen.getByText('pull_request'));

    // Wait for the API call with filter
    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        expect.stringContaining('resource_types=pull_request')
      );
    });

    // Check that the filter status is displayed
    expect(screen.getByText('Showing events for: pull_request')).toBeInTheDocument();
  });

  test('clears filter when "All Types" is clicked', async () => {
    // Mock schema API response
    mockApiFetch.mockImplementation((url) => {
      if (url === '/schema/') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            resource_types: {
              'github': ['pull_request']
            }
          })
        });
      }
      // Mock event logs API response
      if (url.includes('/event-logs')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            event_logs: [],
            total: 0,
            page: 1,
            size: 20
          })
        });
      }
      return Promise.reject(new Error('Unknown API call'));
    });

    render(<Events subscriptions={[]} />);

    // Wait for resource types to load
    await waitFor(() => {
      expect(screen.getByText('pull_request')).toBeInTheDocument();
    });

    // Click on a resource type filter first
    fireEvent.click(screen.getByText('pull_request'));

    // Wait for the filter to be applied
    await waitFor(() => {
      expect(screen.getByText('Showing events for: pull_request')).toBeInTheDocument();
    });

    // Click on "All Types" to clear filter
    fireEvent.click(screen.getByText('All Types'));

    // Wait for the API call without filter
    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/event-logs\?page=1&size=20$/)
      );
    });

    // Check that the filter status is not displayed
    expect(screen.queryByText('Showing events for:')).not.toBeInTheDocument();
  });
});