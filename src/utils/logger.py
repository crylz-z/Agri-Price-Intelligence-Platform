import logging
import os
import sys

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File Handler (Optional, keeps logs in 'logs' dir)
        os.makedirs('logs', exist_ok=True)
        fh = logging.FileHandler(f'logs/{name}.log')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger
