# ELITEA Proxy Service

A secure Flask-based proxy service that translates Claude Code requests to the ELITEA API. This proxy handles authentication header conversion, strips unsupported parameters, maps model names, and provides token counting functionality.

## Features

- **Secure Configuration**: Environment-based configuration with no hardcoded secrets
- **Model Discovery**: Query available models from ELITEA API with `--list-models`
- **Model Mapping**: Automatic mapping between Claude Code and ELITEA model names
- **Parameter Filtering**: Strips unsupported parameters like `anthropic_beta` and `context_management`
- **Token Estimation**: Local token counting to avoid unnecessary API calls
- **Health Monitoring**: Health check endpoint with ELITEA connectivity testing
- **Comprehensive Logging**: Structured logging with configurable levels
- **Streaming Support**: Full support for streaming responses

## Shell completions

`elitea-proxy.py` supports fish and zsh completions:

- `elitea-proxy.py --print-completion fish|zsh`
- `elitea-proxy.py install-completion fish|zsh`

Implementation: this repo vendors a tiny helper at `tools/cli_completion.py` (not a standalone project). Completions are derived from `--help` output.

## Quick Start

### 1. Set Up with uv (Recommended)

This project uses [uv](https://github.com/astral-sh/uv) for fast dependency management.

```bash
# Install dependencies and create a virtual environment
uv sync
```

### 2. Configure Environment

#### Get Your ELITEA Token

To use this proxy, you need an ELITEA API token. Follow these steps to generate one:

1. **Visit the ELITEA Dashboard**: Go to https://next.elitea.ai
2. **Sign in or Create an Account**: If you don't have an account, you'll need to register first
3. **Navigate to API Keys**: Look for an "API Keys", "Tokens", or "Authentication" section in your dashboard
4. **Generate New Token**: Create a new JWT authentication token for API access
5. **Copy the Token**: Save the generated token securely - you'll need it for the configuration below

**Note**: Keep your token secure and never share it publicly. The token provides access to your ELITEA account and API usage.

#### Set Up Environment File
Copy the example environment file and add your ELITEA token:

```bash
cp .env.example .env
```

Edit the `.env` file with your preferred text editor:

```bash
nano .env  # or vim .env, or code .env
```

Replace `your_elitea_jwt_token_here` with your actual ELITEA token:

```
ELITEA_TOKEN=your_actual_elitea_jwt_token_here
```

**Example `.env` file:**
```
# Required
ELITEA_TOKEN=eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9...

# Optional (shown with defaults)
SERVER_PORT=4000
LOG_LEVEL=INFO
```

### 4. Start the Server

```bash
uv run python elitea-proxy.py
```

You can also check available models before starting:

```bash
uv run python elitea-proxy.py --list-models
```

The server will start on `http://localhost:4000` by default. You'll first see a colorful ASCII art banner for "Claude-Elitea Proxy", followed by startup information like:

```
2024-XX-XX XX:XX:XX,XXX - elitea-proxy - INFO - Starting ELITEA proxy server on http://0.0.0.0:4000
2024-XX-XX XX:XX:XX,XXX - elitea-proxy - INFO - Forwarding requests to: https://next.elitea.ai/llm/v1
```

## Docker Quick Start

### Prerequisites
- Docker and Docker Compose installed

### Run with Docker Compose (Recommended)

1. **Set up your environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set your ELITEA_TOKEN
   ```

2. **Start the service:**
   ```bash
   docker-compose up -d
   ```

3. **Check status:**
   ```bash
   docker-compose ps
   curl http://localhost:4000/health
   ```

4. **Check available models:**
   ```bash
   docker-compose exec elitea-proxy uv run python elitea-proxy.py --list-models
   ```

5. **Stop the service:**
   ```bash
   docker-compose down
   ```

### Run with Docker directly

```bash
# Build the image
docker build -t elitea-proxy .

# Run the container
docker run -d \
  --name elitea-proxy \
  -p 4000:4000 \
  -e ELITEA_TOKEN=your_elitea_token_here \
  elitea-proxy

# Check available models
docker exec elitea-proxy uv run python elitea-proxy.py --list-models

# Check logs
docker logs elitea-proxy

# Stop and remove
docker stop elitea-proxy && docker rm elitea-proxy
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### Required Configuration

| Variable | Description |
|----------|-------------|
| `ELITEA_TOKEN` | JWT token for ELITEA API authentication |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ELITEA_BASE_URL` | `https://next.elitea.ai/llm/v1` | ELITEA API base URL |
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `4000` | Server port |
| `SERVER_DEBUG` | `false` | Flask debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `REQUEST_TIMEOUT` | `30` | ELITEA API request timeout (seconds) |
| `STREAM_CHUNK_SIZE` | `1024` | Streaming response chunk size |
| `TOKEN_ESTIMATION_RATIO` | `4` | Characters per token for estimation |
| `STRIP_PARAMS` | (empty) | Comma-separated list of additional parameters to strip from requests |

## Claude Code Integration

Three environment variables tell Claude Code to use the proxy:

| Variable | Value | Notes |
|----------|-------|-------|
| `ANTHROPIC_BASE_URL` | `http://localhost:4000` | Points Claude at the proxy |
| `ANTHROPIC_AUTH_TOKEN` | anything | Proxy ignores it; just needs to be set |
| `ANTHROPIC_MODEL` | e.g. `eu.anthropic.claude-sonnet-4-6` | Use a model from `--list-models` |

There are three ways to set them, from easiest to most manual.

### Option 1 — All-in-one launch (host/direct only)

```bash
uv run python elitea-proxy.py --launch
# Pass extra Claude Code args after --
uv run python elitea-proxy.py --launch -- --resume
```

Starts the proxy in a background thread and immediately runs `claude` with the correct environment variables already injected. When you quit Claude, the proxy shuts down too.

When launched through the `elitea-proxy` wrapper script, Claude starts in the directory where you ran the command, not the proxy project's directory.

In this mode, the proxy runs silently in the terminal so its output does not mix with Claude's interactive output. You will not see proxy startup, request, or error logs in the terminal; they continue to be written to `logs/elitea-proxy.log`.

> **Note**: `--launch` only works when running the proxy directly on the host. It cannot be used with the Docker deployment because the `claude` binary is not available inside the container. Use Option 2 or 3 with Docker instead.

### Option 2 — Source the env vars into your shell

Start the proxy first (directly or via Docker), then source the env vars:

```fish
# fish — direct
source (uv run python elitea-proxy.py --print-env fish | psub)

# fish — Docker
source (docker-compose exec elitea-proxy python elitea-proxy.py --print-env fish | psub)
```

```bash
# zsh / bash — direct
source <(uv run python elitea-proxy.py --print-env)

# zsh / bash — Docker
source <(docker-compose exec elitea-proxy python elitea-proxy.py --print-env)
```

`--print-env` auto-detects your shell when no argument is given. After sourcing, start `claude` normally in the same shell session.

### Option 3 — Set variables manually

When the proxy starts it prints a panel with the exact commands for your shell. You can also set them yourself:

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_AUTH_TOKEN=elitea-proxy  # can be anything — the proxy ignores it
export ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-6  # use a model from --list-models
```

Override the default model by setting `ANTHROPIC_MODEL` in `.env`:

```
ANTHROPIC_MODEL=eu.anthropic.claude-haiku-4-5-20251001-v1:0
```

> **Important — model identity and the Opus illusion**: Because of the proxy's model mappings, Claude Code will *genuinely believe* it is running on Claude Opus. If you ask it which model it is using, it will say Opus. This is expected and by design: the proxy intercepts requests that ask for Opus, and since no Opus model is available through ELITEA, it silently routes those requests to the best available Sonnet model. The client never sees the substitution.

Use a fully-qualified ELITEA model name (from `--list-models`) as the value of `ANTHROPIC_MODEL` and the proxy will pass it through with no additional mapping.

## Usage

### Command Line Options

```bash
# Start the proxy server (default behavior)
uv run python elitea-proxy.py

# List available models from ELITEA API and exit
uv run python elitea-proxy.py --list-models

# Print shell export commands for Claude Code integration (host/direct only)
uv run python elitea-proxy.py --print-env         # auto-detect shell
uv run python elitea-proxy.py --print-env fish    # fish: set -x ...
uv run python elitea-proxy.py --print-env zsh     # zsh/bash: export ...

# Start proxy and launch claude in one command (host/direct only — not Docker)
uv run python elitea-proxy.py --launch
uv run python elitea-proxy.py --launch -- --resume   # pass args to claude

# Show help
uv run python elitea-proxy.py --help
```

### Making the Script Executable

```bash
chmod +x elitea-proxy.py

# Then you can run it directly:
./elitea-proxy.py --list-models
./elitea-proxy.py
```

## API Endpoints

### POST /v1/messages

Proxy endpoint for Claude API messages. Automatically:
- Maps model names to ELITEA equivalents
- Strips unsupported parameters
- Forwards requests to ELITEA API
- Returns streaming responses

### POST /v1/messages/count_tokens

Token counting endpoint that provides local estimation without calling ELITEA API.

### GET /health

Health check endpoint that returns:
- Service status
- ELITEA API connectivity status
- Configuration information

## Model Mappings

The proxy automatically maps Claude Code model names to the best available ELITEA models. Run `python elitea-proxy.py --list-models` to see currently available models from ELITEA.

### Key Model Mappings

| Claude Code Model | ELITEA Model | Notes |
|------------------|--------------|-------|
| `claude-sonnet-4-6` | `eu.anthropic.claude-sonnet-4-6` | Latest Sonnet 4.6 |
| `claude-sonnet` | `eu.anthropic.claude-sonnet-4-6` | Generic → Latest |
| `claude-haiku-4-5-20251001` | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | Proper Haiku model |
| `claude-haiku` | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | Generic → Latest Haiku |
| `claude-3-5-sonnet` | `eu.anthropic.claude-3-7-sonnet-20250219-v1:0` | Upgraded to 3.7 |
| `claude-opus-4-6` | `eu.anthropic.claude-sonnet-4-6` | No Opus available, uses best Sonnet |

### Discovering Available Models

```bash
# List all models available from ELITEA API
python elitea-proxy.py --list-models

# Get help for command options
python elitea-proxy.py --help
```

The `--list-models` command queries the ELITEA API in real-time to show:
- All available Claude models (by version)
- Available GPT models
- OpenAI O-series models
- Embedding models
- Total model count

If the ELITEA API is unreachable, it falls back to showing the configured local mappings.

## Security Features

- **No Hardcoded Secrets**: All sensitive data loaded from environment variables
- **Input Validation**: JSON request validation with error handling
- **Safe Error Messages**: Error responses don't expose sensitive information
- **Request Logging**: Comprehensive request/response logging for debugging
- **Timeout Protection**: Configurable timeouts prevent hanging requests

## Development

### Running in Development Mode

```bash
# Method 1: Environment variables
export SERVER_DEBUG=true
export LOG_LEVEL=DEBUG
uv run python elitea-proxy.py

# Method 2: Add to your .env file
echo "SERVER_DEBUG=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env
uv run python elitea-proxy.py
```

### Testing the Service

```bash
# Check available models (requires ELITEA_TOKEN, shows available models)
uv run python elitea-proxy.py --list-models

# Health check
curl http://localhost:4000/health

# Test message endpoint (requires valid ELITEA_TOKEN)
curl -X POST http://localhost:4000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-sonnet-4-6", "messages": [{"role": "user", "content": "Hello"}]}'

# Test token counting
curl -X POST http://localhost:4000/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello world"}]}'
```

## Logging

The service provides structured logging with configurable levels:

- **INFO**: Request/response information, model mappings, configuration
- **WARNING**: Invalid requests, connectivity issues
- **ERROR**: API failures, unexpected errors
- **DEBUG**: Detailed request/response data, parameter stripping

## Error Handling

The proxy provides appropriate HTTP status codes and error messages:

- **400**: Invalid JSON or malformed requests
- **500**: Internal server errors
- **502**: ELITEA API connectivity issues
- **503**: Health check failures

## Files

- `elitea-proxy.py` - Main application with CLI interface
- `config.py` - Configuration management
- `pyproject.toml` - Project configuration and dependencies
- `uv.lock` - Locked dependency versions
- `.env.example` - Environment configuration template
- `Dockerfile` - Docker container configuration
- `docker-compose.yml` - Docker Compose service definition
- `.dockerignore` - Files excluded from Docker build
- `README.md` - This documentation

## Troubleshooting

### Common Issues

#### "Missing required environment variables: ELITEA_TOKEN"
- **Cause**: No ELITEA_TOKEN set in environment variables
- **Solution**: Create a `.env` file with your ELITEA token as shown in the setup steps
- **Verify**: Check that `.env` file exists and contains `ELITEA_TOKEN=your_token_here`

#### "Address already in use" / Port 4000 in use
- **Cause**: Another service is running on port 4000
- **Solution**: Either stop the other service or change the port:
  ```bash
  echo "SERVER_PORT=4001" >> .env
  ```

#### "ModuleNotFoundError: No module named 'flask'"
- **Cause**: Dependencies not installed or wrong Python environment
- **Solution**:
  ```bash
  uv sync
  # Then run with:
  uv run python elitea-proxy.py
  ```

#### Server starts but health check shows "elitea_status": "connection_failed"
- **Cause**: Invalid ELITEA token or network connectivity issues
- **Solution**:
  - Verify your ELITEA_TOKEN is correct and not expired
  - Check network connectivity to `https://next.elitea.ai`
  - Verify your token has proper permissions

#### "externally-managed-environment" error when installing dependencies
- **Cause**: System Python environment protection (common on Ubuntu 23.04+)
- **Solution**: Use `uv` or Docker:
  ```bash
  # Option 1: Use uv (recommended)
  uv sync
  uv run python elitea-proxy.py

  # Option 2: Use Docker
  docker-compose up -d
  ```

### Debug Mode

For detailed debugging information:

```bash
# In your .env file, add:
SERVER_DEBUG=true
LOG_LEVEL=DEBUG

# Or set temporarily:
SERVER_DEBUG=true LOG_LEVEL=DEBUG uv run python elitea-proxy.py
```

### Verify Setup

Test your installation with these commands:

```bash
# 1. List models (requires ELITEA_TOKEN, shows available models)
uv run python elitea-proxy.py --list-models

# 2. Health check (should return status info)
curl http://localhost:4000/health

# 3. Token counting (should work without ELITEA API)
curl -X POST http://localhost:4000/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'
```

## Support

For issues or questions:

1. **Check the application logs** - The service provides detailed logging
2. **Verify your ELITEA_TOKEN** - Ensure it's valid and not expired
3. **Test network connectivity** - Ensure you can reach the ELITEA API endpoint
4. **Review this troubleshooting section** - Most common issues are covered above

If problems persist, check that all files are present and your environment matches the requirements in this documentation.
