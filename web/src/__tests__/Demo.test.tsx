import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Demo from '../Demo';

describe('Demo Component', () => {
  beforeEach(() => {
    // Mock scrollIntoView since it's not available in test environment
    Element.prototype.scrollIntoView = jest.fn();
    Object.defineProperty(window, 'scrollTo', {
      value: jest.fn(),
      writable: true
    });
  });
  test('renders demo page with subscription options', () => {
    render(<Demo />);
    
    // Check main heading
    expect(screen.getByText('Subscribe using natural language')).toBeInTheDocument();
    
    // Check subscription options are present
    expect(screen.getByText(/Notify me when PR 1374 is approved/)).toBeInTheDocument();
    expect(screen.getByText(/Alert me when there is a Stripe with > \$500 value/)).toBeInTheDocument();
  });

  test('shows loading state when adding subscription', async () => {
    render(<Demo />);
    
    const addButton = screen.getByRole('button', { name: /Add Subscription/ });
    fireEvent.click(addButton);
    
    // Should show loading state
    expect(screen.getByText(/Adding Subscription.../)).toBeInTheDocument();
    expect(addButton).toBeDisabled();
    
    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByText('✓ Subscription Added')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  test('shows LLM gate prompt after subscription is added', async () => {
    render(<Demo />);
    
    const addButton = screen.getByRole('button', { name: /Add Subscription/ });
    fireEvent.click(addButton);
    
    // Wait for subscription to be added
    await waitFor(() => {
      expect(screen.getByText('✓ Subscription Added')).toBeInTheDocument();
    }, { timeout: 2000 });
    
    // Check LLM Gate prompt is displayed
    expect(screen.getByText('LLM Gate Prompt:')).toBeInTheDocument();
    expect(screen.getByText(/Evaluate if this GitHub pull request event/)).toBeInTheDocument();
  });

  test('shows ingest events section after subscription is added', async () => {
    render(<Demo />);
    
    const addButton = screen.getByRole('button', { name: /Add Subscription/ });
    fireEvent.click(addButton);
    
    // Wait for subscription to be added
    await waitFor(() => {
      expect(screen.getByText('✓ Subscription Added')).toBeInTheDocument();
    }, { timeout: 2000 });
    
    // Check step 2 is now visible
    expect(screen.getByText('Ingest new event')).toBeInTheDocument();
    expect(screen.getByText('Ingest Event')).toBeInTheDocument(); // Single ingest button
  });

  test('does not show Bonus Interactions section', () => {
    render(<Demo />);
    
    // Bonus interactions should not be present
    expect(screen.queryByText('🎛️ Bonus Interactions')).not.toBeInTheDocument();
    expect(screen.queryByText('🔁 Replay Events')).not.toBeInTheDocument();
  });

  test('processing section is shown when event is ingested', async () => {
    render(<Demo />);
    
    // Add subscription first
    const addButton = screen.getByRole('button', { name: /Add Subscription/ });
    fireEvent.click(addButton);
    
    // Wait for subscription to be added
    await waitFor(() => {
      expect(screen.getByText('✓ Subscription Added')).toBeInTheDocument();
    }, { timeout: 2000 });
    
    // Select an event first
    const eventDiv = screen.getByText(/PR 1234 approved by Alice/).closest('div');
    fireEvent.click(eventDiv);
    
    // Click on ingest event
    const ingestButton = screen.getByRole('button', { name: /Ingest Event/ });
    fireEvent.click(ingestButton);
    
    // Should show processing section
    expect(screen.getByText('What Happens Inside LangHook')).toBeInTheDocument();
    expect(screen.getByText('Ingestion')).toBeInTheDocument();
  });

  test('shows ingestion endpoint when event is selected', async () => {
    render(<Demo />);
    
    // Add subscription first
    const addButton = screen.getByRole('button', { name: /Add Subscription/ });
    fireEvent.click(addButton);
    
    // Wait for subscription to be added
    await waitFor(() => {
      expect(screen.getByText('✓ Subscription Added')).toBeInTheDocument();
    }, { timeout: 2000 });
    
    // Select an event
    const eventDiv = screen.getByText(/PR 1234 approved by Alice/).closest('div');
    fireEvent.click(eventDiv);
    
    // Should show ingestion endpoint
    expect(screen.getByText('Ingestion Endpoint:')).toBeInTheDocument();
    expect(screen.getByText('POST /ingest/github')).toBeInTheDocument();
  });

  test('shows raw payload during processing step 1', async () => {
    render(<Demo />);
    
    // Add subscription first
    const addButton = screen.getByRole('button', { name: /Add Subscription/ });
    fireEvent.click(addButton);
    
    // Wait for subscription to be added
    await waitFor(() => {
      expect(screen.getByText('✓ Subscription Added')).toBeInTheDocument();
    }, { timeout: 2000 });
    
    // Select an event first
    const eventDiv = screen.getByText(/PR 1234 approved by Alice/).closest('div');
    fireEvent.click(eventDiv);
    
    // Click on ingest event
    const ingestButton = screen.getByRole('button', { name: /Ingest Event/ });
    fireEvent.click(ingestButton);
    
    // During step 1 processing, should show both spinner and raw payload
    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeInTheDocument();
      expect(screen.getByText('Raw Payload:')).toBeInTheDocument();
    }, { timeout: 1000 });
  });
});