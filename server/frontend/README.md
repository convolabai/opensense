# Frontend Demo

This directory contains the React-based interactive demo for LangHook.

## Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server (with proxy to backend):
   ```bash
   npm start
   ```

3. Build for production:
   ```bash
   npm run build
   ```

The demo will be available at `/demo` when the LangHook server is running.

## Features

- **Interactive webhook testing**: Send sample payloads from GitHub, Stripe, Slack
- **Real-time transformation**: See raw webhooks converted to canonical events
- **Mapping generation**: Use LLM to generate JSONata mappings
- **Live metrics**: Monitor system performance and event processing stats
- **Educational content**: Learn how LangHook transforms event data

## Architecture

The frontend is a single-page React application that communicates with the LangHook FastAPI backend through a proxy during development and is served as static files in production.