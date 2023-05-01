"""
"""
# FIXME: BSD license

import json
import os
import shutil
import logging
from threading import Semaphore
from .tester_tools import ResultHandler, create_logger


logger = logging.getLogger("TesterCore")
logger.handlers.clear()
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
logger.addHandler(stream)
logger.setLevel(logging.INFO)


class TesterCore:
    """
    This is to be considered as an abstract class.
    We should always inherit from it and complete your own Tester class
    that implement your own tests.
    """

    def __init__(self, config, logger_name, logdir="./logs"):
        """
        Loads a json config with list of hw modules and their dependencies
        ex:
        {
          "module1": {"depends": ["module2"] },
          "module2": {"depends": [] },
          "module3": {"depends": [] },
          ...
        }
        :warning --> Never put circular dependencies (module1 -> module2 -> module1)
        :param config       String path to the json config file
        :param logger_name  String logger name for ResultHandler.
                            Automatically prefixes with "log_" and suffix ".txt".
        :param logdir       String, location to store log files
        """
        with open(config, "r", encoding='utf-8') as file:
            self.modules = json.load(file)
        # add a semaphore to all modules
        for mod in self.modules.keys():
            self.modules[mod]["lock"] = Semaphore(1)
            if not self.modules[mod].get("depends"):
                self.modules[mod]["depends"] = []
        # create other required variables
        self.results = ResultHandler(create_logger(logger_name))
        self.cli = {}
        self.logdir = logdir
        if os.path.exists(logdir):
            shutil.rmtree(logdir)
        os.mkdir(logdir)

    def lock(self, module):
        """
        Locks the module, if part of the TesterCore loaded modules, and all of its dependent modules
        :param module  String, module name
        """
        if module not in self.modules.keys():
            logger.warning("Cannot lock %s, not part of the module list",module)
            return False
        # if any dependency, lock the module
        for submodule in self.modules[module].get("depends"):
            self.lock(submodule)
        # lock the module
        locked = self.modules[module]["lock"].acquire()
        logger.debug("locked: %s", module)
        return locked

    def unlock(self, module):
        """
        Unlocks the module, if part of the TesterCord loaded modules, and all of its
        dependent modules.
        :param module  String, module name
        """
        if module not in self.modules.keys():
            logger.warning("Cannot unlock %s, not part of the module list", module)
            return False
        # if any dependency, unlock them module
        for submodule in self.modules[module].get("depends"):
            self.unlock(submodule)
        # lock the module
        unlocked = self.modules[module]["lock"].release()
        logger.debug("unlocked: %s", module)
        return unlocked

    def set_cli(self, cli_func, *args, **kwargs):
        """
        Sets a function pointer to the cli we should later use in this TesterCore module
        :param cli_func     Pointer to a CliHandler like function (ex: SerialCli, TelnetCli, etc...)
        :param args, kwargs Initialization parameters of the cli function
        """
        self.cli = {"func": cli_func, "args": args, "kwargs": kwargs}

    def get_cli(self, logname, cli_func=None, *args, **kwargs):
        """
        Returns an initialized cli object from a previously set_cli() call
        :param logname  String, path to the log for the cli object
        :param cli_func     Pointer to a CliHandler like function (ex: SerialCli, TelnetCli, etc...).
                            **If not set, self.cli is used instead and args, kwargs are ignored.**
        :param args, kwargs Initialization parameters of the cli function
        """
        cli = self.cli if not cli_func else {"func": cli_func, "args": args, "kwargs": kwargs}
        logger.debug("get_cli: %s", cli)
        if not cli.get("func"):
            return None
        kwargs = cli["kwargs"].copy()
        if not kwargs.get("store_file"):
            kwargs["store_file"] = os.path.join(self.logdir, logname)
        return cli["func"](*cli["args"], **kwargs)

    def get_lockncli(self, module, logname=None):
        """
        Both locks the module and get the CLI.
        This is only a wrapper to speedup dev. and readability
        :param module   String, Module name
                        Auto generate sub directory (at logdir) with logfile name
                        if logname not provided.
        Returns a tuple with the lock state (True/False) and the CLI object
        """
        if not logname:
            logname = f"log_cli_{module.lower()}.txt"
        return self.lock(module), self.get_cli(logname=logname)

    def result(self):
        """
        Provides the global restults from ResultHandler
        Returns True if no error in any test, False otherwise
        """
        return self.results.get_global_result()

    def write_csv(self, *args, **kwargs):
        """
        Generates a csv file from ResultHandler
        """
        return self.results.write_csv(*args, **kwargs)
