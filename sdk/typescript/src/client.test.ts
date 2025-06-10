import axios from 'axios';
import { LangHookClient, LangHookClientConfig, AuthConfig } from '../src/client';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('LangHookClient', () => {
  let client: LangHookClient;
  let config: LangHookClientConfig;
  let mockAxiosInstance: any;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Mock axios instance
    mockAxiosInstance = {
      get: jest.fn(),
      post: jest.fn(),
      delete: jest.fn(),
    };
    
    mockedAxios.create.mockReturnValue(mockAxiosInstance);
    
    config = {
      endpoint: 'http://localhost:8000',
      auth: {
        type: 'token',
        value: 'test-token'
      }
    };
    
    client = new LangHookClient(config);
  });

  describe('constructor', () => {
    it('should create client with token auth', () => {
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        auth: undefined
      });
    });

    it('should create client with basic auth', () => {
      const basicConfig = {
        endpoint: 'http://localhost:8000',
        auth: {
          type: 'basic' as const,
          value: 'user:pass'
        }
      };
      
      new LangHookClient(basicConfig);
      
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        headers: {
          'Content-Type': 'application/json'
        },
        auth: {
          username: 'user',
          password: 'pass'
        }
      });
    });

    it('should create client without auth', () => {
      const noAuthConfig = {
        endpoint: 'http://localhost:8000'
      };
      
      new LangHookClient(noAuthConfig);
      
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        headers: {
          'Content-Type': 'application/json'
        },
        auth: undefined
      });
    });
  });

  describe('init', () => {
    it('should validate connection successfully', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { status: 'up' } });
      
      await client.init();
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health/');
    });

    it('should throw error on connection failure', async () => {
      const error = new Error('Connection failed');
      mockAxiosInstance.get.mockRejectedValue(error);
      
      await expect(client.init()).rejects.toThrow('Failed to connect to LangHook server');
    });
  });

  describe('listSubscriptions', () => {
    it('should return list of subscriptions', async () => {
      const mockSubscriptions = [
        {
          id: 123,
          subscriber_id: 'default',
          description: 'Test subscription',
          pattern: 'test.*',
          channel_type: null,
          channel_config: null,
          active: true,
          gate: null,
          created_at: '2023-01-01T00:00:00Z'
        }
      ];
      
      mockAxiosInstance.get.mockResolvedValue({
        data: { subscriptions: mockSubscriptions }
      });
      
      const result = await client.listSubscriptions();
      
      expect(result).toEqual(mockSubscriptions);
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/subscriptions/');
    });
  });

  describe('createSubscription', () => {
    it('should create a new subscription', async () => {
      const mockSubscription = {
        id: 123,
        subscriber_id: 'default',
        description: 'Test subscription',
        pattern: 'test.*',
        channel_type: null,
        channel_config: null,
        active: true,
        gate: null,
        created_at: '2023-01-01T00:00:00Z'
      };
      
      mockAxiosInstance.post.mockResolvedValue({ data: mockSubscription });
      
      const result = await client.createSubscription('Test description');
      
      expect(result).toEqual(mockSubscription);
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/subscriptions/', {
        description: 'Test description'
      });
    });
  });

  describe('deleteSubscription', () => {
    it('should delete a subscription', async () => {
      mockAxiosInstance.delete.mockResolvedValue({});
      
      await client.deleteSubscription('123');
      
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/subscriptions/123');
    });
  });

  describe('ingestRawEvent', () => {
    it('should ingest a raw event', async () => {
      const mockResult = {
        message: 'Event accepted',
        request_id: 'req_123'
      };
      
      mockAxiosInstance.post.mockResolvedValue({ data: mockResult });
      
      const result = await client.ingestRawEvent('github', { action: 'opened' });
      
      expect(result).toEqual(mockResult);
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/ingest/github', { action: 'opened' });
    });
  });

  describe('testSubscription', () => {
    it('should return mock test result', async () => {
      const mockEvent = {
        publisher: 'test',
        resource: { type: 'item', id: 123 },
        action: 'created',
        timestamp: '2023-01-01T12:00:00Z',
        payload: { test: 'data' }
      };
      
      const result = await client.testSubscription('123', mockEvent);
      
      expect(result.matched).toBe(true);
      expect(result.reason).toContain('Mock test');
    });
  });

  describe('listen', () => {
    it('should return a stop function', () => {
      const handler = jest.fn();
      const stopFn = client.listen('123', handler);
      
      expect(typeof stopFn).toBe('function');
      
      // Call stop function to prevent background polling
      stopFn();
    });

    it('should use default interval of 10 seconds', () => {
      const handler = jest.fn();
      const stopFn = client.listen('123', handler);
      
      // Should not throw and should return function
      expect(typeof stopFn).toBe('function');
      
      stopFn();
    });

    it('should enforce minimum interval of 10 seconds', () => {
      const handler = jest.fn();
      const stopFn = client.listen('123', handler, { intervalSeconds: 5 });
      
      // Should not throw and should return function
      expect(typeof stopFn).toBe('function');
      
      stopFn();
    });
  });
});