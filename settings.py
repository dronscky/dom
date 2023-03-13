logger_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'std_format': {
                        'format': '{name} - {asctime} - {levelname} - {module}:{funcName}:{lineno} - {message}',
                        'style': '{'
                        }
                   },
    'handlers': {'file': {
                        'class': 'logging.handlers.RotatingFileHandler',
                        'level': 'ERROR',
                        'filename': 'error.log',
                        'formatter': 'std_format',
                        'maxBytes': 1024,
                        'backupCount': 3
                }
    },
    'loggers': {
        'esia': {
            'level': 'ERROR',
            'handlers': ['file']
        }
    },
    # 'filters': {}
}