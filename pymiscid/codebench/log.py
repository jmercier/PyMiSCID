# This file introduce a unix color logger to add stop logging in black and
# white. Register the ColoredFormater as a standard python logging
# Formatter
#
import logging

class UnixColoredFormatter(logging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[01;%dm"

    COLORS = {
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': BLUE,
        'CRITICAL': RED,
        'ERROR': RED,
        'EXCEPTION' : CYAN }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = self.COLOR_SEQ % (30 + self.COLORS[levelname]) + levelname + self.RESET_SEQ
            record.msg = self.COLOR_SEQ % (30 + self.COLORS[levelname]) + record.msg + self.RESET_SEQ
        return logging.Formatter.format(self, record)





logging.UnixColoredFormatter = UnixColoredFormatter
logging.ColoredFormatter = UnixColoredFormatter # For the sake of backward compatibility

handler = logging.StreamHandler()
handler.formatter = UnixColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
logging.root.addHandler(handler)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger = logging.getLogger("TESTLOGGER")
    logger.debug("debug message")
    logger.info("info message")
    logger.warn("warn message")
    logger.critical("critical message")
    logger.error("error message")
    try:
        raise Exception()
    except:
        logger.exception("asdf")

