import json
from ktt import TestStep, ResultHandler, create_logger


if __name__ == '__main__':
    logger = create_logger("my_fake_test")
    # create result handler
    rh = ResultHandler(logger)

    # Start Testing
    step = TestStep("Test name", "my module", test_logger=logger)
    step.set_result(False, "My test comment")
    rh.append_test(step)

    # another way of making tests
    rh.set_step('test name', "my module")
    rh.set_result(True, "my test comment from rh")

    # make a test with a custom field
    step = TestStep("my custom field test", "my module", my_new_field="field value")
    step.set_result(False, "My custom test comment")
    rh.append_test(step)

    rh.write_csv("my_fake_test.csv")

    quit(0 if rh.get_global_result() else 1)
