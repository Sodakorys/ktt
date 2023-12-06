from ktt import TesterCore
from time import sleep


class SimpleClass(TesterCore):
    def test_sleep(self, time):
        self.lock("SLEEP")
        print("sleep: started")
        sleep(time)
        print("sleep: done")
        self.unlock("SLEEP")

    def test_print_sleep(self, time):
        self.lock("PRINT_SLEEP")
        print("print_sleep: I'll sleep for %d s" % time)
        sleep(time)
        print("print_sleep: done")
        self.unlock("PRINT_SLEEP")

    def test_print(self, msg):
        self.lock("PRINT")
        print("test_print:" + msg)
        self.unlock("PRINT")

