# AI

AI enrichment is optional. `AI_PROVIDER=none` is the default and the product remains fully functional through deterministic analysis.

Provider interface:

- `analyze_impact(payload)`
- `healthcheck()`

Supported provider stubs:

- `none`
- `openai`
- `ollama`

Production AI output must be validated with Pydantic before it can affect findings. AI may enrich reasons and severity, but deterministic change detection remains the source of truth.
