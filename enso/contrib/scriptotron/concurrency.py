import logging
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron.events import EventResponderList


class GeneratorManager(object):
    """
    Responsible for managing generators in a way similar to tasklets
    in Stackless Python by iterating the state of all registered
    generators on every timer tick.
    """

    def __init__(self, eventManager):
        self.__generators = EventResponderList(
            eventManager,
            "timer",
            self.__onTimer
        )

    @staticmethod
    @safetyNetted
    def __callGenerator(generator, keepAlives):
        try:
            generator.next()
        except StopIteration:
            pass
        except Exception, e:
            logging.error("Exception in generator: %s", e)
        else:
            keepAlives.append(generator)

    def __onTimer(self, msPassed):
        keepAlives = []
        for _, generator in self.__generators:
            GeneratorManager.__callGenerator(generator, keepAlives)
        self.__generators.fromlist(keepAlives)

    def reset(self):
        self.__generators.clear()

    def add(self, generator):
        self.__generators[id(generator)] = generator
