"""
Centralized logging configuration for the actuator-dispenser project.
Handles workflow-based file logging with virtual mode tagging and log rotation.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Global variable to store the current workflow name
current_workflow = None

def set_workflow_name(workflow_name):
    """
    Set the current workflow name for logging.
    This should be called at the beginning of each workflow.
    
    Args:
        workflow_name (str): Name of the workflow (e.g., "example_workflow", "gradient_workflow")
    """
    global current_workflow
    current_workflow = workflow_name

def setup_logger(module_name, virtual=False, log_level=logging.INFO):
    """
    Set up a logger with both file and console handlers.
    All modules will log to the same workflow-specific file.
    
    Args:
        module_name (str): Name of the module (e.g., "dispenser", "cnc_machine")
        virtual (bool): Whether running in virtual mode (adds _virtual tag to filename)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create logger name
    logger_name = f"actuator_dispenser.{module_name}"
    if virtual:
        logger_name += "_virtual"
    
    logger = logging.getLogger(logger_name)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    
    # Create formatter that includes module name in the message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler (for immediate feedback)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(levelname)-8s | %(name)s | %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    
    # Try to set UTF-8 encoding for console on Windows
    try:
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(encoding='utf-8')
    except Exception:
        pass  # Fall back to default encoding if UTF-8 fails
    
    logger.addHandler(console_handler)
    
    # File handler (workflow-specific log file)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    virtual_tag = "_virtual" if virtual else ""
    
    # Use workflow name if available, otherwise fall back to module name
    workflow_name = current_workflow if current_workflow else "general"
    log_filename = f"{workflow_name}{virtual_tag}_{timestamp}.log"
    log_filepath = os.path.join(logs_dir, log_filename)
    
    # Use RotatingFileHandler to manage log file size (max 10MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_filepath, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'  # Explicitly set UTF-8 encoding
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # File gets all messages, console filtered by log_level
    logger.addHandler(file_handler)
    
    # Log the initialization only once per workflow
    if module_name == "workflow_init":
        logger.info(f"=== Starting workflow: {workflow_name} ===")
        logger.info(f"Virtual mode: {virtual}")
        logger.info(f"Log file: {log_filepath}")
        logger.info("=" * 50)
    
    return logger

def log_method_entry(logger, method_name, **kwargs):
    """
    Helper function to log method entry with parameters.
    
    Args:
        logger: Logger instance
        method_name (str): Name of the method being called
        **kwargs: Method parameters to log
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"-> {method_name}({params})")

def log_method_exit(logger, method_name, result=None):
    """
    Helper function to log method exit with optional result.
    
    Args:
        logger: Logger instance
        method_name (str): Name of the method exiting
        result: Optional result to log
    """
    if result is not None:
        logger.info(f"<- {method_name} completed - Result: {result}")
    else:
        logger.info(f"<- {method_name} completed")

def log_virtual_action(logger, action_description):
    """
    Helper function to log virtual mode actions.
    
    Args:
        logger: Logger instance
        action_description (str): Description of what would happen in real mode
    """
    logger.info(f"[VIRTUAL] {action_description}")

def initialize_workflow_logging(workflow_name, virtual=False):
    """
    Initialize logging for a workflow. This should be called at the beginning of each workflow.
    
    Args:
        workflow_name (str): Name of the workflow file (without .py extension)
        virtual (bool): Whether running in virtual mode
    
    Returns:
        logging.Logger: Main workflow logger
    """
    set_workflow_name(workflow_name)
    
    # Create a main workflow logger
    workflow_logger = setup_logger("workflow_init", virtual=virtual)
    
    return workflow_logger
