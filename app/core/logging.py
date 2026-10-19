import logging


def configure_logging() -> None:
    """Configure the application-wide console logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )