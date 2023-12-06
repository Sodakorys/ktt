"""
Copyright 2023 Korys technologies

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

    (1) Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

    (2) Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.

    (3)The name of the author may not be used to
    endorse or promote products derived from this software without
    specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

import json
import os
import shutil
import logging
from threading import Semaphore, Thread
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
        ```
        ex:
        {
          "module1": {"depends": ["module2"] },
          "module2": {"depends": [] },
          "module3": {"depends": [] },
          ...
        }
        ```
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
        # TODO: implement it to be usable as a "with" for more security (will unlock when exits)
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

    def get_cli(self, logname, *args, cli_func=None, **kwargs):
        """
        Returns an initialized cli object from a previously set_cli() call
        :param logname  String, path to the log for the cli object
        :param cli_func     Pointer to a CliHandler like function (ex: SerialCli,
                            TelnetCli, etc...).
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


class RunnerCore:
    """
    The Runner class permits to automate running functions defined
    in a TesterCore class with parallel execution.
    """
    def __init__(self, tester_core, jobs=1):
        """
        @param tester_core  A TesterCore object
        @param jobs         number of parallel jobs available (default = 1)
        """
        self.tester = tester_core
        self.jobs = Semaphore(0)
        self.th_list = []
        self.max_jobs = jobs

    def _run_test(self, test):
        """
        Runs a single test if present in the TesterCore object
        @param test     A dict, representing the function name from the TesterCore object
                        Ex: `{"func": "function name", "args": ["arg1", "arg2"]}`
        """
        if not hasattr(self.tester, "test_" + test.get("func")):
            logger.warning("Function %s not found", test.get("func"))
            return
        self.th_list.append(Thread(target=self._job_run, args=[test]))
        self.th_list[-1].start()

    def _job_run(self, test):
        """
        Wait for job to be available and run the function
        @param test     A dict, representing the function name from the TesterCore object
                        Ex: `{"func": "function name", "args": ["arg1", "arg2"]}`
        """
        func = getattr(self.tester, "test_" + test.get("func"))
        with self.jobs:
            logger.debug("Start %s", test.get("func"))
            func(*test.get("args"))

    def run(self, test_list, cnt=1):
        """
        Run all tests from a test_list once or more
        @param test_list    A list of dict containing the functions to be called
                            Ex: `{"func": "function name", "args": ["arg1", "arg2"]}`
        @param cnt          The number of executions of the test list
        """
        self.jobs = Semaphore(len(test_list) if not self.max_jobs else self.max_jobs)
        for i in range(cnt):
            logger.debug("--- iteration %d ---", i)
            for test in test_list:
                self._run_test(test)

    def _clean_dead_job(self, job):
        if job.is_alive():
            return False
        self.th_list.remove(job)
        self.jobs.release()
        return True

    def wait(self, blocking=True):
        """
        Wait for jobs to complete.
        Returns True if at least a job has been freed.
        Returns False if no job has completed.
        @param blocking     Wait for one job to complete if False, wait for all jobs otherwise
        """
        logger.debug("wait for job to complete")
        completed = False
        t_out = None if blocking else 0.5
        # if no completed jobs, wait for one to complete
        for job in self.th_list:
            job.join(timeout=t_out)
            completed |= self._clean_dead_job(job)
        return completed
