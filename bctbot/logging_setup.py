import logging.config
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'normal': {
            'format': '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s >>  %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'debug_log': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'normal',
            'filename': 'log/debug.log',
            'when': 'H',
            'interval': 1,
            'backupCount': 0,
            'encoding': 'utf-8'
        },
        'info_log': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'normal',
            'filename': 'log/info.log',
            'when': 'H',
            'interval': 1,
            'backupCount': 0,
            'encoding': 'utf-8'
        },
        'error_log': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'normal',
            'filename': 'log/error.log',
            'maxBytes': 5000,
            'backupCount': 0,
            'encoding': 'utf-8'
        },
        'log_console': {
            'level': 'DEBUG',
            'formatter': 'normal',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '__main__': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'tradingbot': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'exchange': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'market': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'strategies': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'order': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'transitions': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        },
        'ccxt': {
            'handlers': ['debug_log', 'info_log', 'error_log', 'log_console'],
            'level': 'DEBUG',
        }
    }
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

