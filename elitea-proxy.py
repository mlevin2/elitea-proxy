#!/usr/bin/env python3
"""
Simple proxy to translate Claude Code requests to ELITEA API.
Handles authentication header conversion and strips unsupported beta flags.
"""

from flask import Flask, request, Response
import requests
import json
import logging
import argparse
from config import config

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)  # Initialize colorama
    COLORAMA_AVAILABLE = True
except ImportError:
    # Fallback if colorama is not available
    COLORAMA_AVAILABLE = False
    class Fore:
        CYAN = MAGENTA = YELLOW = GREEN = BLUE = RED = RESET = ''
    class Style:
        BRIGHT = RESET_ALL = ''

app = Flask(__name__)

# Setup logging
logger = config.setup_logging()

def strip_unsupported_params(data):
    """Recursively strip unsupported parameters from the request body."""
    if isinstance(data, dict):
        # List of parameters to strip from any dictionary
        params_to_strip = config.UNSUPPORTED_PARAMS + ['cache_control']
        
        return {
            k: strip_unsupported_params(v) 
            for k, v in data.items() 
            if k not in params_to_strip
        }
    elif isinstance(data, list):
        return [strip_unsupported_params(item) for item in data]
    else:
        return data

@app.route('/v1/messages', methods=['POST'])
def proxy_messages():
    """Proxy /v1/messages requests to ELITEA"""

    try:
        # Get the request body
        body = request.get_json()
        if not body:
            logger.warning("Received request with no JSON body")
            return Response(
                json.dumps({'error': {'message': 'Request body must be valid JSON'}}),
                status=400,
                content_type='application/json'
            )

        logger.info(f"Proxying request for model: {body.get('model', 'unknown')}")

        # Map model name if needed
        if 'model' in body:
            original_model = body['model']
            body['model'] = config.get_mapped_model(original_model)
            if original_model != body['model']:
                logger.info(f"Mapped model {original_model} -> {body['model']}")

        # Ensure max_tokens is present (required by some ELITEA endpoints)
        if 'max_tokens' not in body:
            body['max_tokens'] = 4096
            logger.info("Added default max_tokens: 4096")

        # Recursively strip unsupported parameters (including cache_control)
        body = strip_unsupported_params(body)

        # Get headers for ELITEA
        headers = config.get_elitea_headers()

        logger.debug(f"Request body being sent to ELITEA: {json.dumps(body)}")

        # Forward the request to ELITEA
        response = requests.post(
            f'{config.ELITEA_BASE_URL}/messages',
            json=body,
            headers=headers,
            stream=True,  # Support streaming responses
            timeout=config.REQUEST_TIMEOUT
        )

        logger.info(f"ELITEA response status: {response.status_code}")

        # If it's an error status, log the body to help diagnose
        if response.status_code >= 400:
            try:
                error_body = response.json()
                logger.error(f"ELITEA error response: {json.dumps(error_body)}")
            except:
                logger.error(f"ELITEA error response (non-JSON): {response.text}")

        # Filter headers to avoid conflicts with Flask's automatic header handling
        filtered_headers = {}
        headers_to_exclude = {
            'transfer-encoding',  # Flask handles this for streaming
            'content-encoding',   # Can cause conflicts with streaming
            'connection',         # Flask manages connection headers
            'content-length',     # Flask calculates this for streaming
            'server',             # Flask adds its own Server header
            'date'                # Flask adds its own Date header
        }

        excluded_headers = []
        for key, value in response.headers.items():
            if key.lower() not in headers_to_exclude:
                filtered_headers[key] = value
            else:
                excluded_headers.append(key)

        if excluded_headers:
            logger.debug(f"Excluded headers to prevent conflicts: {excluded_headers}")

        # Return ELITEA's response with properly filtered headers
        return Response(
            response.iter_content(chunk_size=config.STREAM_CHUNK_SIZE),
            status=response.status_code,
            headers=filtered_headers
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Request to ELITEA failed: {e}")
        return Response(
            json.dumps({'error': {'message': 'Failed to connect to ELITEA API'}}),
            status=502,
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return Response(
            json.dumps({'error': {'message': 'Internal server error'}}),
            status=500,
            content_type='application/json'
        )

@app.route('/v1/messages/count_tokens', methods=['POST'])
def count_tokens():
    """Handle token counting requests - use local estimation"""

    try:
        body = request.get_json()
        if not body:
            logger.warning("Token count request with no JSON body")
            return Response(
                json.dumps({'error': {'message': 'Request body must be valid JSON'}}),
                status=400,
                content_type='application/json'
            )

        # Token estimation based on character count
        text = ""
        if 'messages' in body:
            for msg in body['messages']:
                if isinstance(msg.get('content'), str):
                    text += msg['content']
                elif isinstance(msg.get('content'), list):
                    for item in msg['content']:
                        if item.get('type') == 'text':
                            text += item.get('text', '')

        estimated_tokens = max(1, len(text) // config.TOKEN_ESTIMATION_RATIO)
        logger.info(f"Estimated tokens: {estimated_tokens} (from {len(text)} chars)")

        return Response(
            json.dumps({'input_tokens': estimated_tokens}),
            status=200,
            content_type='application/json'
        )

    except Exception as e:
        logger.error(f"Token counting error: {e}")
        return Response(
            json.dumps({'error': {'message': 'Token counting failed'}}),
            status=500,
            content_type='application/json'
        )

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint with ELITEA connectivity test"""
    health_data = {
        'status': 'ok',
        'elitea_base_url': config.ELITEA_BASE_URL,
        'server_port': config.SERVER_PORT
    }

    try:
        # Test ELITEA API connectivity
        response = requests.get(
            f"{config.ELITEA_BASE_URL.rstrip('/v1')}/health",
            headers=config.get_elitea_headers(),
            timeout=5
        )
        if response.status_code == 200:
            health_data['elitea_status'] = 'connected'
        else:
            health_data['elitea_status'] = f'error_{response.status_code}'
    except requests.exceptions.RequestException:
        health_data['elitea_status'] = 'connection_failed'
    except Exception as e:
        logger.warning(f"Health check error: {e}")
        health_data['elitea_status'] = 'unknown'

    status_code = 200 if health_data.get('elitea_status') == 'connected' else 503
    return Response(
        json.dumps(health_data),
        status=status_code,
        content_type='application/json'
    )

def display_startup_banner():
    """Display colorful ASCII art banner on startup."""
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
 ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║     ██║     ███████║██║   ██║██║  ██║█████╗
██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
{Style.RESET_ALL}
{Fore.MAGENTA}{Style.BRIGHT}
███████╗██╗     ██╗████████╗███████╗ █████╗
██╔════╝██║     ██║╚══██╔══╝██╔════╝██╔══██╗
█████╗  ██║     ██║   ██║   █████╗  ███████║
██╔══╝  ██║     ██║   ██║   ██╔══╝  ██╔══██║
███████╗███████╗██║   ██║   ███████╗██║  ██║
╚══════╝╚══════╝╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
{Style.RESET_ALL}
{Fore.YELLOW}{Style.BRIGHT}
██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗
██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝
██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝
██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝
██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝
{Style.RESET_ALL}
{Fore.GREEN}┌─────────────────────────────────────────────────┐
│  {Fore.BLUE}{Style.BRIGHT}Secure proxy bridging Claude Code ↔ ELITEA{Style.RESET_ALL}{Fore.GREEN}     │
│ {Fore.BLUE}Model mapping • Parameter filtering • Stream{Style.RESET_ALL}{Fore.GREEN}    │
└─────────────────────────────────────────────────┘{Style.RESET_ALL}
"""

    # Print the banner
    print(banner)

def list_models():
    """Display available models from ELITEA API."""
    print(f"{Fore.GREEN}{Style.BRIGHT}Available Models from ELITEA:{Style.RESET_ALL}")
    print()

    try:
        # Query ELITEA API for available models
        headers = config.get_elitea_headers()

        # Try the standard /v1/models endpoint
        models_url = f"{config.ELITEA_BASE_URL}/models"
        response = requests.get(models_url, headers=headers, timeout=10)

        if response.status_code == 200:
            models_data = response.json()

            # Handle different response formats
            models = []
            if isinstance(models_data, dict) and 'data' in models_data:
                # OpenAI-style format: {"data": [{"id": "model-name", ...}, ...]}
                models = [model.get('id', 'unknown') for model in models_data['data']]
            elif isinstance(models_data, list):
                # Simple list format: ["model1", "model2", ...]
                models = models_data
            elif isinstance(models_data, dict) and 'models' in models_data:
                # Alternative format: {"models": [...]}
                models = models_data['models']

            if models:
                # Remove duplicates and sort
                unique_models = sorted(set(models))

                # Group models by type for better organization
                claude_models = [m for m in unique_models if 'claude' in m.lower()]
                gpt_models = [m for m in unique_models if 'gpt' in m.lower()]
                o_models = [m for m in unique_models if m.startswith('o') and 'gpt' not in m.lower()]
                embedding_models = [m for m in unique_models if 'embedding' in m.lower()]
                other_models = [m for m in unique_models if m not in claude_models + gpt_models + o_models + embedding_models]

                # Display models by category
                categories = [
                    ("Claude Models", claude_models, Fore.MAGENTA),
                    ("GPT Models", gpt_models, Fore.GREEN),
                    ("OpenAI O-Series Models", o_models, Fore.BLUE),
                    ("Embedding Models", embedding_models, Fore.YELLOW),
                    ("Other Models", other_models, Fore.CYAN)
                ]

                total_models = len(unique_models)
                for category_name, category_models, color in categories:
                    if category_models:
                        print(f"  {Style.BRIGHT}{category_name}:{Style.RESET_ALL}")
                        for model in category_models:
                            print(f"    {color}• {model}{Style.RESET_ALL}")
                        print()

                print(f"  {Fore.GREEN}Total: {total_models} unique models available{Style.RESET_ALL}")
            else:
                print(f"  {Fore.YELLOW}No models found in API response{Style.RESET_ALL}")

        else:
            print(f"  {Fore.RED}Error: API returned status {response.status_code}{Style.RESET_ALL}")
            if response.text:
                print(f"  {Fore.RED}Response: {response.text[:200]}{Style.RESET_ALL}")

    except requests.exceptions.RequestException as e:
        print(f"  {Fore.RED}Error connecting to ELITEA API: {e}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Falling back to configured model mappings:{Style.RESET_ALL}")
        print()

        # Fallback to showing local mappings
        for original, mapped in config.MODEL_MAPPINGS.items():
            if original == mapped:
                print(f"  {Fore.CYAN}• {original}{Style.RESET_ALL}")
            else:
                print(f"  {Fore.CYAN}• {original}{Style.RESET_ALL} {Fore.YELLOW}→{Style.RESET_ALL} {Fore.MAGENTA}{mapped}{Style.RESET_ALL}")

    except Exception as e:
        print(f"  {Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")

    print()
    print(f"{Fore.BLUE}Note:{Style.RESET_ALL} Claude Code model names are automatically mapped to ELITEA-compatible models")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ELITEA proxy server for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start the proxy server
  %(prog)s --list-models      # Show available models
        """
    )

    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List available models and exit (does not start server)'
    )

    return parser.parse_args()

if __name__ == '__main__':
    try:
        # Parse command line arguments
        args = parse_args()

        # Handle --list-models flag
        if args.list_models:
            list_models()
            exit(0)

        # Display startup banner
        display_startup_banner()

        # Validate configuration on startup
        logger.info(f"Starting ELITEA proxy server on http://{config.SERVER_HOST}:{config.SERVER_PORT}")
        logger.info(f"Forwarding requests to: {config.ELITEA_BASE_URL}")
        logger.info(f"Configuration: {config}")

        # Start the Flask application
        app.run(
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.SERVER_DEBUG
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set the required environment variables. See .env.example for reference.")
        exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        exit(1)
