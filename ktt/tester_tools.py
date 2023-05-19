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

import os
import csv
import logging
from threading import Timer
from time import time


logger = logging.getLogger("TesterTools")
logger.handlers.clear()
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
logger.addHandler(stream)
logger.setLevel(logging.INFO)


def create_logger(name, path=""):
    """
    Creates a logger with both stream and file recording
    Stream has INFO log level
    File   has DEBUG log level
    :param name:  name of the logger (will be used for file naming)
    :param path:  path to store the logfile
    :return:      a ready to use logger object
    """
    # Create a logger with info level in stream and debug level in the file
    new_logger = logging.getLogger(name)
    new_logger.handlers.clear()
    filename = "log_" + name + ".txt"
    if path:
        filename = os.path.join(path, filename)
    if path and not os.path.exists(path):
        os.mkdir(path)
    file_debug = logging.FileHandler(filename, mode='w')
    file_debug.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_debug.setFormatter(formatter)

    new_stream = logging.StreamHandler()
    new_stream.setLevel(logging.INFO)

    new_logger.addHandler(file_debug)
    new_logger.addHandler(new_stream)
    new_logger.setLevel(logging.DEBUG)
    return new_logger


class Timeout:
    """
    Timeout class
    Creates a Threaded Timer with a time limit to check if timeout occured without blocking
    Example: wait for 10s
    >>> tout = Timeout(10)
    >>> tout.start()
    >>> while not tout.has_timeout_occurred():
    >>>     # do some stuff
    """

    def __init__(self, time_s, log=None):
        """
        Initialize a timeout Timer()
        :param time_s: timeout time in seconds
        """
        self.log = log
        self.time = time_s
        self.tmr = None
        self._is_out = False

    def __del__(self):
        self.stop()

    def start(self, time_s=None):
        """
        Start a new timeout, stopping any existing one
        :param time_s: time in seconds
        """
        if not time_s:
            time_s = self.time
        self.stop()
        # start a new timer
        self._is_out = False
        self.tmr = Timer(time_s, self._timeout)
        self.tmr.start()

    def stop(self):
        """
        Stop the timeout
        """
        if self.tmr and self.tmr.is_alive():
            self.tmr.cancel()

    def has_timeout_occurred(self):
        """
        Check if the timeout has occured
        :return  True if timed out, False otherwiss
        """
        return self._is_out

    def _timeout(self):
        self._is_out = True
        if self.log:
            self.log.debug("Timeout")


class TestStep:
    """
    Simple object to define your Test and store its results
    """

    def __init__(self, name, module, test_logger=None, index=None, **kwargs):
        """
        Simple TestStep object to construct a dict with Test type, result, etc...
        :param name:         Test name
        :param module:       Module name corresponding to the test
        :param test_logger:  logging logger to be used for debug/logging
        :param index:        index of the test
        """
        self.log = test_logger if test_logger else create_logger("test_step")
        # FIXME: replace ',' by '|' should be done for all keys only when generating csv
        self.step = {'module': module}
        self.header = "[{:.8}".format(module)
        self.header += "]"
        self.step["index"] = index if index else "-"
        if kwargs:
            self.append(**kwargs)
        self.step.update({'test': name.replace(",", "|"), 'duration': time()})

        self.log.info("%s start %s", self.header, name)
        self.result = None

    def append(self, **kwargs):
        """
        Add complementary element to the test step
        ex: step.append(section="mysection", component="my component")
        """
        for key, val in kwargs.items():
            self.step[key] = val

    def set_result(self, result, comments=""):
        """
        Finalize current test step with its result and a comment
        :param result:    True/False to indicate if passes or fails
        :param comments:  A comment about this test
        """
        self.step['result'] = result
        self.step['Comments'] = comments
        self.step['duration'] = round(time() - self.step['duration'], 3)
        self.log.info("%s %s", self.header, "FAILED" if not result else "PASSED")
        self.result = result


class DescrStep(TestStep):
    """
    Simple object to handle a TestStep as a description, not a test result.
    This is used for latex generation in the #Transcriptor class.
    """
    def __init__(self, *argv, **kwargs):
        # ensure no log is visible for description steps
        self.log = logging.getLogger("DescrStep")
        self.log.handlers.clear()
        kwargs["test_logger"] = self.log
        # call Parent class init
        super().__init__(*argv, **kwargs)
        # Add description boolean to recognize which type of Step it is
        self.step['is_description'] = True


class ResultHandler:
    """
    Handles a list of TestStep objects, using the same logger
    """

    def __init__(self, result_logger):
        """
        Handles a list of TestStep to generate a report
        :param result_logger: logging logger to be used for debug/logging
        """
        self.test = None
        self.log = result_logger
        self.global_res = True
        self.steps = []
        self.idx = 0

    def set_step(self, name, module, **kwargs):
        """
        Wrapper to create a TestStep
        :param name:         Test name
        :param module:       Module name corresponding to the test
        """
        self.idx += 1
        self.test = TestStep(name, module, test_logger=self.log, index=self.idx)
        if kwargs:
            self.test.append(**kwargs)

    def set_result(self, result, comments=""):
        """
        Wrapper to TestStep.set_result
        :param result:    True/False to indicate if passes or fails
        :param comments:  A comment about this test
        """
        self.test.set_result(result, comments)
        self.append_test(self.test)

    def append_test(self, test):
        """
        Append a completed TestStep to the list of test
        :param test: A TestStep object
        """
        self.steps.append(test.step)
        self.global_res &= test.step.get('result') if test.step.get('result') is not None else True

    def gen_dict(self):
        """
        Generates a dict from the TestStep list
        :return: A structured dict that represents the Test hierarchy
        """
        base_dict = {'result': self.global_res}
        for step in self.steps:
            new_dict = base_dict
            field_list = list(step.keys())
            for rm_elem in ['index', 'test', 'duration', 'result', 'Comments']:
                field_list.remove(rm_elem)
            for field in field_list:
                elem = step.get(field)
                if not elem:
                    break
                if not new_dict.get(elem):
                    new_dict[elem] = {"result": True}
                new_dict = new_dict[elem]
                # apply unitary result at higher level
                # module = True if all sub steps are True
                new_dict["result"] &= step['result'] if step['result'] is not None else True
            if not new_dict.get("steps"):
                new_dict["steps"] = []
            steps = new_dict["steps"]
            steps.append(step)
            # if the first step is a DescrStep, we inew_dicticate this module or component
            # or section has description steps
            if len(steps) and steps[0].get('is_description') is True:
                new_dict["is_description"] = True

        return base_dict

    def get_global_result(self):
        """
        Returns a global result which is a logical AND of all TestStep results
        :return: True if all Tests were passed, False otherwise
        """
        return self.global_res

    def write_csv(self, filename, hierarchy_order=True):
        """
        Write the tests results as CSV file.
        Ordering by module/component/test by default
        :param filename:        Filename for the CSV file
        :param hierarchy_order: Indicates if we write csv in the order of the tests,
                                or by module/components (default)
        """
        # generate the header
        header = []
        for step in self.steps:
            for k in step.keys():
                header.append(k)
        header = list(dict.fromkeys(header))
        self.log.debug("CSV Header: %s", header)
        with open(filename, 'w') as file:
            csv_w = csv.DictWriter(file, fieldnames=header)
            csv_w.writeheader()
            if hierarchy_order:
                modules = self.gen_dict()
                for module in modules:
                    if module == "result":
                        continue
                    if modules[module].get("steps"):
                        csv_w.writerows(modules[module]['steps'])
                        continue
                    for comp in modules[module]:
                        if comp == "result":
                            continue
                        self.log.debug("comp: %s ==> %s", comp, modules[module][comp])
                        if modules[module][comp].get("steps"):
                            csv_w.writerows(modules[module][comp]['steps'])
                            continue
                        for section in modules[module][comp]:
                            if section == "result":
                                continue
                            csv_w.writerows(modules[module][comp][section]['steps'])
            else:
                csv_w.writerows(self.steps)

        self.log.info("Writing results to: %s",  filename)


class Transcriptor:
    """
    Generates Tex files.
    A Tex header file should be provided to get the structure.
    The header must contains at least the following packages:
     \\usepackage[utf8]{inputenc} % Unicode support (Umlauts etc.)
     \\usepackage{multirow} % mutiple raw in single column for tables
     \\usepackage{ltablex}

    Also, the following commands must be defined:
     * kresTrue
     * kresFalse
     * kresNone
     * ktestsend
     * ktestcheck
     * ktestcheckfail

    Here is a suggestion of definition:
     \\newcommand\\kresTrue{\\textbf{\\colorbox{green}{\\textcolor{ForestGreen}{PASSED}}}}
     \\newcommand\\kresFalse{\\textbf{\\colorbox{red}{\\textcolor{BrickRed}{FAILED}}}}
     \\newcommand\\kresNone{\\-}
     \\newcommand\\ktestsend[1]{\\textbf{\\textcolor{NavyBlue}{#1}}}
     \\newcommand\\ktestcheck[1]{\\textbf{\\colorbox{ForestGreen}{#1}}}
     \\newcommand\\ktestcheckfail[1]{\\textbf{\\colorbox{red}{#1}}}

    The header must contain the title
    """
    def __init__(self, tex_header):
        self.tex = ""
        with open(tex_header, 'r') as file:
            self.tex = file.read()
        self.desc = []
        self.desc_auth_keys = ['module', 'component', 'section']
        self.log = logging.getLogger("Transcriptor")

    def gen_tex(self, modules, filename):
        """
        Generate a Tex file from the Test dict hierarchy
        :param modules:    The dict hierarchy
        :param filename:   Location of the new Tex file to be generated
        """
        # FIXME: needs to be more generic
        # --> handle cases where no section or no components
        self._gen_recap("overall", modules, "chapter")
        for module in modules:
            if module == 'result':
                continue
            self.tex += "\\chapter{{{}}}\n\n".format(module)
            self._gen_recap(module, modules[module], "section")
            self._gen_reports(modules[module])
        self.tex += "\\end{document}"
        with open(filename, "w") as file:
            file.write(self.tex.replace("_", "\\_"))

    def _get_ratio(self, elements, sub_elements=True):
        total_elems = 0
        total_pass = 0
        for element in elements:
            if element == 'result':
                continue
            if not sub_elements:
                total_elems += 1
                total_pass += 1 if elements[element]['result'] else 0
                continue
            for sub_element in elements[element]:
                if sub_element == 'result':
                    continue
                total_elems += 1
                total_pass += 1 if elements[element][sub_element]['result'] else 0
        return {'passed': total_pass, 'total': total_elems}

    def _gen_recap(self, name, module, section="section"):
        self.tex += "\\{}{{summary}}\n\n".format(section)
        self.tex += "The {} status is \\kres{}\n\n".format(name, module['result'])
        # Calculate pass/fail count give detailed values
        ratio = self._get_ratio(module, section != "section")
        self.tex += "There are {}/{} tests passed.\n\n".format(ratio['passed'], ratio['total'])
        # Generate table of components and their PASS/FAIL status
        self.tex += "\\begin{tabular} {|l|l|l|r|}\n"
        for comp in module:
            if comp == 'result':
                continue
            self.tex += "  \\hline\n"
            self.tex += "  \\begin{minipage}{8cm}\n"
            self.tex += "  {} \\end{{minipage}} & \\kres{} \\\\\n".format(comp,
                            module[comp]['result'])
        self.tex += "  \\hline\n"
        self.tex += "\\end{tabular}\n\n"

    def _gen_reports(self, comps):
        for comp in comps:
            if comp == "result":
                continue
            self.tex += "\\section{{{}}}\n\n".format(comp)
            self.tex += "The test {} status is \\kres{}\n\n".format(comp, comps[comp]['result'])
            # if no steps, there are section inside the component
            if not comps[comp].get("steps"):
                self._gen_sub_report(comps[comp])
                continue
            # if no section, we have steps
            self._gen_steps_table(comps[comp]["steps"])

    def _gen_sub_report(self, sections):
        for sect in sections:
            if sect == 'result':
                continue
            self.tex += "\\subsection{{{}}}\n\n".format(sect)
            if sections[sect].get("is_description"):
                self._gen_steps_description(sections[sect]["steps"])
                continue
            self._gen_steps_table(sections[sect]["steps"])

    def _gen_steps_description(self, steps):
        for step in steps:
            self.tex += "\\paragraph{{{}}}\n".format(step["Comments"])

    def _gen_steps_table(self, steps):
        self.tex += "\\begin{tabularx} {\\textwidth} {|X|c|}\n"
        self.tex += "  \\hline\n"
        for step in steps:
            # FIXME: replace with callback to predefined translation function
            self.tex += " \\begin{{minipage}}{{8cm}} {} \\end{{minipage}} & \\kres{} \\\\\n" \
                       .format(self._get_step_text(step), step['result'])
            if step['result'] is not None:
                self.tex += "  \\hline\n"
        self.tex += "  \\hline\n"
        self.tex += "\\end{tabularx}\n\n"

    def _get_step_text(self, step):
        func = '_' + step['test'].split(':')[0]
        if not hasattr(self, func):
            return "ERROR: FUNCTION NOT FOUND"
        function = getattr(self, func)
        return function(len(func) + 1, step)
