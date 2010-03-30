#
#
# vim: ts=4 sw=4 sts=0 noexpandtab:
import logging

class ColoredFormatter(logging.Formatter):

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



logging.ColoredFormatter = ColoredFormatter


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
    logger.exception("asdf")



