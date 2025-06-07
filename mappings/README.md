# Mappings Directory

This directory contains JSONata mapping files that define how to transform incoming webhook payloads into canonical event formats.

## Usage

Place `.jsonata` files in this directory. Each file should be named after the event source (e.g., `github.jsonata`, `stripe.jsonata`) and contain a JSONata expression for transforming that source's payloads.

## Example

```jsonata
{
  "event_type": "pull_request." & action,
  "source": "github",
  "timestamp": updated_at,
  "data": {
    "pr_number": pull_request.number,
    "title": pull_request.title,
    "repository": repository.name
  }
}
```

The mapping engine will automatically load all `.jsonata` files from this directory on startup.