import logging

logger = logging.getLogger("gym_journal")

def log_event(event, level=logging.INFO, **attrs):
    logger.log(level, event, extra={"event": event, **attrs})
