from myclass import SimpleClass
from ktt import RunnerCore
from time import sleep

test_lst = [
    {"func": "sleep", "args": [0.5]},
    {"func": "print_sleep", "args": [3]},
    {"func": "print", "args": ["this is after a print_sleep"]},
    {"func": "sleep", "args": [3]},
    {"func": "print", "args": ["this can be run while a sleep is run"]},
]

tester = SimpleClass("config.json", "mytest")

runner = RunnerCore(tester)
runner.run(test_lst)
runner.wait()

print("ALL DONE")
quit(0)
