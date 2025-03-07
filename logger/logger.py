import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import colorlog

class CustomLogger:
    """
    Custom logger class that creates a logger instance with a file handler and a console handler.
    """

    logger_dir = "logs"

    def __init__(self, logger_name="logger"):
        # Create logs directory if it doesn't exist
        os.makedirs(self.logger_dir, exist_ok=True)

        # Create logger instance
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers = []

        # Create formatters with optional url and data fields
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            '%(if_url)s%(if_data)s',
            defaults={'if_url': '', 'if_data': ''}
        )
        
        # Add custom filter to handle optional fields
        class ContextFilter(logging.Filter):
            def filter(self, record):
                record.if_url = f" - url: {record.url}" if hasattr(record, 'url') else ''
                record.if_data = f" - data: {record.data}" if hasattr(record, 'data') else ''
                return True

        # Color formatter for console
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING': 'yellow',
                'ERROR':   'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        
        # File handler (with rotation)
        log_file = f'{self.logger_dir}/scrapper_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(ContextFilter())
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(color_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        return self.logger
