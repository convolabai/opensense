/**
 * Utility functions for API calls that handle server path configuration
 */

// Get the base path from environment variable set during build
const basePath = process.env.REACT_APP_BASE_PATH || '';

/**
 * Get the correct API base URL that includes the server path if configured
 * @param path - The API path (e.g., '/subscriptions/', '/map/metrics/json')
 * @returns The full API path including server path prefix
 */
export function getApiPath(path: string): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  
  // If no base path is configured, return the path as-is
  if (!basePath) {
    return normalizedPath;
  }
  
  // Combine base path with API path
  return `${basePath}${normalizedPath}`;
}

/**
 * Wrapper around fetch that automatically applies the correct API path
 * @param path - The API path (e.g., '/subscriptions/', '/map/metrics/json')
 * @param options - Fetch options
 * @returns Promise<Response>
 */
export function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  return fetch(getApiPath(path), options);
}