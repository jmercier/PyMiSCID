__all__ = ['gtkreactor']

from codebench.decorators import singleton
import gtkreactor
Reactor = singleton(gtkreactor.GTKReactor)
