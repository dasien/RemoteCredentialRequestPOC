#!/usr/bin/env python3
"""
AI Agent Credential Request POC - Main Entry Point

This POC demonstrates secure credential management for AI agents
using Bitwarden with human-in-the-loop approval.
"""
import argparse
import asyncio
import logging
import sys
from typing import Optional

from src.agents.bitwarden_agent import BitwardenAgent
from src.agents.flight_booking_agent import FlightBookingAgent
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Agent Credential Request POC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with visible browser (default)
  python -m src.main

  # Run in headless mode
  python -m src.main --headless

  # Enable debug logging
  python -m src.main --log-level DEBUG
        """
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='User approval timeout in seconds (default: 300)'
    )

    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )

    return parser.parse_args()


async def run_poc(args: argparse.Namespace) -> bool:
    """
    Run the credential request POC.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if successful, False otherwise
    """
    bitwarden_agent: Optional[BitwardenAgent] = None
    flight_agent: Optional[FlightBookingAgent] = None

    try:
        logger.info("=== AI Agent Credential Request POC ===")
        logger.info("Initializing agents...")

        # Initialize agents
        bitwarden_agent = BitwardenAgent()
        flight_agent = FlightBookingAgent(
            bitwarden_agent=bitwarden_agent,
            headless=args.headless
        )

        # Run flight booking task
        logger.info("Starting flight booking agent...")
        success = await flight_agent.run()

        if success:
            logger.info("✓ POC completed successfully")
            return True
        else:
            logger.warning("✗ POC completed with errors")
            return False

    except KeyboardInterrupt:
        logger.info("User cancelled operation (Ctrl+C)")
        return False

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return False

    finally:
        # Cleanup
        logger.info("Cleaning up...")
        if bitwarden_agent:
            bitwarden_agent.ensure_locked()
        logger.info("Cleanup complete")


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    args = parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Run POC
    success = asyncio.run(run_poc(args))

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
