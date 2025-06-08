"""
E2E OpenAI Tests for LangHook
=============================

This module contains end-to-end tests for OpenAI LLM transformations.

## Running the Tests

### Prerequisites

1. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="sk-your-actual-openai-api-key"
   ```

### Test Execution

Run all OpenAI E2E tests:
```bash
pytest tests/e2e/test_openai_e2e.py -v
```

Run only the flexible tests (less strict validation):
```bash
pytest tests/e2e/test_openai_e2e.py -k "flexible" -v
```

Run only the strict tests (exact validation against expected outputs):
```bash
pytest tests/e2e/test_openai_e2e.py -k "strict" -v
```

Run a specific webhook test:
```bash
pytest tests/e2e/test_openai_e2e.py -k "GitHub" -v
```

### Without API Key

If you don't have an OpenAI API key, the tests will be skipped:
```bash
pytest tests/e2e/test_openai_e2e.py -v
# Output: SKIPPED (OpenAI API key not available)
```

## Test Structure

### Strict Tests (`test_webhook_transformation_strict`)
- Validates exact match against expected canonical outputs
- Tests all 14 webhook scenarios from the issue
- Ensures the LLM produces the correct publisher, resource type/id, and action

### Flexible Tests (`test_webhook_transformation_flexible`) 
- Validates structure and reasonableness only
- More forgiving of slight variations in LLM responses
- Useful for testing when prompt tuning is in progress

### Test Cases

The tests cover 14 different webhook transformation scenarios:
1. GitHub push events
2. Stripe payment_intent.succeeded events
3. Slack message events
4. Twilio SMS events
5. Shopify order events
6. AWS SNS notifications
7. GitLab push events
8. Bitbucket repository push events
9. Jira issue creation events
10. Trello card creation events
11. Notion page update events
12. Zoom meeting creation events
13. PayPal payment completion events
14. Calendly booking events

## Troubleshooting

### Common Issues

1. **API Key Issues**: Make sure your OpenAI API key is valid and has sufficient credits
2. **Model Errors**: The tests use `gpt-4o-mini` - ensure this model is available to your account
3. **Rate Limiting**: Add delays between tests if you hit OpenAI rate limits
4. **Prompt Tuning**: If tests fail due to wrong canonical outputs, tune the prompt in `langhook/map/llm.py`

### Debugging Failed Tests

1. Check the test output for specific assertion failures
2. Look at the LLM response in the logs to see what was generated vs expected
3. Use the flexible tests to validate structure before fixing exact values
4. Run the simulation script to validate test expectations: `python /tmp/test_simulation.py`

## Development Notes

- Tests use real OpenAI API calls and consume credits
- The prompt can be tuned in `LLMSuggestionService._create_system_prompt()`
- Expected outputs can be adjusted in the `WEBHOOK_TEST_CASES` constant
- The CloudEvent wrapper adds timestamp and payload fields to the LLM output
"""