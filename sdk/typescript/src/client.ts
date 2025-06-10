import axios, { AxiosInstance } from 'axios';

export interface AuthConfig {
  type: 'basic' | 'token';
  value: string;
}

export interface LangHookClientConfig {
  endpoint: string;
  auth?: AuthConfig;
}

export interface CanonicalEvent {
  publisher: string;
  resource: {
    type: string;
    id: string | number;
  };
  action: string;
  timestamp: string;
  payload: Record<string, any>;
}

export interface Subscription {
  id: number;
  subscriber_id: string;
  description: string;
  pattern: string;
  channel_type: string | null;
  channel_config: Record<string, any> | null;
  active: boolean;
  gate: Record<string, any> | null;
  created_at: string;
  updated_at?: string;
}

export interface IngestResult {
  message: string;
  request_id: string;
}

export interface MatchResult {
  matched: boolean;
  reason?: string;
}

export interface ListenOptions {
  intervalSeconds?: number;
}

export class LangHookClient {
  private config: LangHookClientConfig;
  private client: AxiosInstance;

  constructor(config: LangHookClientConfig) {
    this.config = config;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Set up authentication
    let auth;
    if (config.auth) {
      if (config.auth.type === 'basic') {
        const [username, password] = config.auth.value.split(':', 2);
        auth = { username, password };
      } else if (config.auth.type === 'token') {
        headers['Authorization'] = `Bearer ${config.auth.value}`;
      }
    }

    this.client = axios.create({
      baseURL: config.endpoint,
      headers,
      auth,
    });
  }

  async init(): Promise<void> {
    try {
      await this.client.get('/health/');
    } catch (error) {
      throw new Error(`Failed to connect to LangHook server: ${error}`);
    }
  }

  async listSubscriptions(): Promise<Subscription[]> {
    const response = await this.client.get('/subscriptions/');
    return response.data.subscriptions;
  }

  async createSubscription(nlSentence: string): Promise<Subscription> {
    const response = await this.client.post('/subscriptions/', {
      description: nlSentence,
    });
    return response.data;
  }

  async deleteSubscription(subscriptionId: string): Promise<void> {
    await this.client.delete(`/subscriptions/${subscriptionId}`);
  }

  listen(
    subscriptionId: string,
    handler: (event: CanonicalEvent) => void,
    options: ListenOptions = {}
  ): () => void {
    const intervalSeconds = Math.max(options.intervalSeconds || 10, 10);
    let lastSeenTimestamp: string | null = null;
    let stopFlag = false;

    const pollEvents = async () => {
      while (!stopFlag) {
        try {
          const response = await this.client.get(
            `/subscriptions/${subscriptionId}/events`,
            {
              params: { page: 1, size: 50 },
            }
          );

          const events = response.data.event_logs || [];

          // Process new events (newer than last seen)
          const newEvents = events.filter((event: any) => {
            return lastSeenTimestamp === null || event.timestamp > lastSeenTimestamp;
          });

          // Update last seen timestamp
          if (events.length > 0) {
            const timestamps = events.map((event: any) => event.timestamp);
            lastSeenTimestamp = timestamps.reduce((latest: string, current: string) => 
              current > latest ? current : latest
            );
          }

          // Call handler for each new event
          for (const eventData of newEvents) {
            const canonicalEvent: CanonicalEvent = {
              publisher: eventData.publisher,
              resource: {
                type: eventData.resource_type,
                id: eventData.resource_id,
              },
              action: eventData.action,
              timestamp: eventData.timestamp,
              payload: eventData.canonical_data || {},
            };
            handler(canonicalEvent);
          }
        } catch (error) {
          // Log error but continue polling
          console.error('Error polling events:', error);
        }

        await new Promise((resolve) => setTimeout(resolve, intervalSeconds * 1000));
      }
    };

    // Start polling
    pollEvents();

    // Return stop function
    return () => {
      stopFlag = true;
    };
  }

  async testSubscription(
    subscriptionId: string,
    mockCanonicalEvent: CanonicalEvent
  ): Promise<MatchResult> {
    // For now, return a simple mock result since the API doesn't have a test endpoint
    // In a real implementation, this would call a /subscriptions/{id}/test endpoint
    return { matched: true, reason: 'Mock test - always matches' };
  }

  async ingestRawEvent(
    publisher: string,
    payload: Record<string, any>
  ): Promise<IngestResult> {
    const response = await this.client.post(`/ingest/${publisher}`, payload);
    return response.data;
  }
}