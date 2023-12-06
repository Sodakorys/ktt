from myclass import SimpleClass
from ktt import RunnerCore
from time import sleep
from logging import getLogger, DEBUG

logger = getLogger("TesterCore")
logger.setLevel(DEBUG)

test_lst = [
    {"func": "sleep", "args": [1]},
    {"func": "print_sleep", "args": [3]},
    {"func": "print", "args": ["this is defined after a print_sleep, but I will run first if jobs > 2"]},
    {"func": "sleep", "args": [3]},
    {"func": "sleep", "args": [3]},
    {"func": "print", "args": ["this can be run while a sleep is run"]},
]

tester = SimpleClass("config.json", "mytest")

job_cnt = 3
runner = RunnerCore(tester, job_cnt)
runner.run(test_lst)
runner.wait()

print("ALL DONE")
quit(0)
