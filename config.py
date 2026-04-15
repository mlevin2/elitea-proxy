#!/usr/bin/env python3
"""
Configuration management for ELITEA proxy service.
Handles environment variable loading, validation, and provides structured configuration.
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if available
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass


class Config:
    """Configuration management for ELITEA proxy service."""

    def __init__(self):
        """Initialize configuration with environment variables and validation."""
        self._load_config()
        self._validate_required_config()

    def _load_config(self):
        """Load configuration from environment variables with defaults."""

        # Required secrets - no defaults
        self.ELITEA_TOKEN = os.getenv('ELITEA_TOKEN')

        # App configuration with defaults
        self.ELITEA_BASE_URL = os.getenv('ELITEA_BASE_URL', 'https://next.elitea.ai/llm/v1')
        self.SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
        self.SERVER_PORT = int(os.getenv('SERVER_PORT', '4000'))
        self.SERVER_DEBUG = os.getenv('SERVER_DEBUG', 'false').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()

        # Logging configuration
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/elitea-proxy.log')
        self.LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB default
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))  # Keep 5 backup files

        # Performance settings
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.STREAM_CHUNK_SIZE = int(os.getenv('STREAM_CHUNK_SIZE', '1024'))
        self.TOKEN_ESTIMATION_RATIO = int(os.getenv('TOKEN_ESTIMATION_RATIO', '4'))

        # Model mappings - Updated based on available ELITEA models (use --list-models to verify)
        # Strategy: Map Claude Code model names to the best available ELITEA equivalents
        self.MODEL_MAPPINGS = {
            # Exact matches - pass through unchanged
            "eu.anthropic.claude-sonnet-4-6": "eu.anthropic.claude-sonnet-4-6",
            "eu.anthropic.claude-sonnet-4-20250514-v1:0": "eu.anthropic.claude-sonnet-4-20250514-v1:0",
            "eu.anthropic.claude-haiku-4-5-20251001-v1:0": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "eu.anthropic.claude-3-7-sonnet-20250219-v1:0": "eu.anthropic.claude-3-7-sonnet-20250219-v1:0",

            # Claude Code standard model names -> Best available ELITEA models
            "claude-sonnet-4-6": "eu.anthropic.claude-sonnet-4-6",
            "claude-opus-4-6": "eu.anthropic.claude-sonnet-4-6",  # Map Opus to best Sonnet (no Opus available)
            "claude-haiku-4-5-20251001": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-sonnet-4-5-20250929": "eu.anthropic.claude-sonnet-4-20250514-v1:0",

            # Generic model names -> Latest models
            "claude-3-5-sonnet": "eu.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "claude-3-haiku": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-sonnet": "eu.anthropic.claude-sonnet-4-6",
            "claude-haiku": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-opus": "eu.anthropic.claude-sonnet-4-6",  # No Opus available, use best Sonnet
        }

        # Parameters to strip from requests
        self.UNSUPPORTED_PARAMS = ['anthropic_beta', 'context_management']
        
        # Load additional parameters to strip from environment
        # Example: STRIP_PARAMS=thinking,some_other_param
        extra_strip = os.getenv('STRIP_PARAMS', '')
        if extra_strip:
            extra_params = [p.strip() for p in extra_strip.split(',') if p.strip()]
            for param in extra_params:
                if param not in self.UNSUPPORTED_PARAMS:
                    self.UNSUPPORTED_PARAMS.append(param)

        # Headers for ELITEA API
        self.ELITEA_HEADERS = {
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
        }

    def _validate_required_config(self):
        """Validate that required configuration is present."""
        missing_vars = []

        if not self.ELITEA_TOKEN:
            missing_vars.append('ELITEA_TOKEN')

        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            raise ValueError(error_msg)

    def get_elitea_headers(self) -> Dict[str, str]:
        """Get headers for ELITEA API requests."""
        headers = self.ELITEA_HEADERS.copy()
        headers['Authorization'] = f'Bearer {self.ELITEA_TOKEN}'
        return headers

    def get_mapped_model(self, model: str) -> str:
        """Get the mapped model name for ELITEA API."""
        return self.MODEL_MAPPINGS.get(model, model)

    def setup_logging(self):
        """Setup logging configuration with both console and file output."""
        # Create logs directory if it doesn't exist
        log_path = Path(self.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create logger
        logger = logging.getLogger('elitea-proxy')
        logger.setLevel(getattr(logging, self.LOG_LEVEL))

        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler (stdout/stderr)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.LOG_LEVEL))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.LOG_FILE,
            maxBytes=self.LOG_MAX_BYTES,
            backupCount=self.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(getattr(logging, self.LOG_LEVEL))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def __repr__(self) -> str:
        """String representation of config (without sensitive data)."""
        return (
            f"Config(ELITEA_BASE_URL={self.ELITEA_BASE_URL}, "
            f"SERVER_HOST={self.SERVER_HOST}, "
            f"SERVER_PORT={self.SERVER_PORT}, "
            f"LOG_LEVEL={self.LOG_LEVEL}, "
            f"LOG_FILE={self.LOG_FILE})"
        )


# Global config instance
config = Config()
