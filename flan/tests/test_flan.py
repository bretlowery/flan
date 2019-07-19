import os
from flan.tests.utils import Utils
from unittest import TestCase, skip
import inspect
from dateutil import parser as dtparser

testreplay = os.path.join(os.path.dirname(__file__), 'flan.replay')
testtemplate1 = os.path.join(os.path.dirname(__file__), '100testrecords.access.log')
testtemplate2 = os.path.join(os.path.dirname(__file__), 'test*.access.log')
testtemplate3 = os.path.join(os.path.dirname(__file__), 'test*.access.log*')
testout = os.path.join(os.path.dirname(__file__), '/testresults')
utils = Utils()


class FlanTestCases(TestCase):

    #
    # CUSTOM ASSERTS
    #

    def assertIsDatetime(self, value):
        strvalue = value if isinstance(value, str) else str(value)
        try:
            dt = dtparser.parse(strvalue)
        except ValueError:
            dt = None
            pass
        self.assertTrue(dt is not None)
        return dt

    #
    # TEST METHODS
    #

    def chk4expected(self, parameters, expectedoutput):
        result = utils.execmd(parameters)
        self.assertIn(expectedoutput.lower(), result.stdout.lower())

    def chk4unexpected(self, parameters, unexpectedoutput):
        result = utils.execmd(parameters)
        self.assertNotIn(unexpectedoutput.lower(), result.stdout.lower())

    def chk4success(self, parameters):
        result = utils.execmd(parameters)
        self.assertEqual(result.returncode, 0)

    def chk4failure(self, parameters):
        result = utils.execmd(parameters)
        self.assertNotEqual(result.returncode, 0)

    def chk4countequals(self, parameters, countexpected):
        result, resultslist = utils.execmd(parameters, returnstdout=True)
        self.assertEqual(result.returncode, 0)
        resultsfound = len(resultslist)
        self.assertEqual(resultsfound, countexpected)

    def chk4validlog(self, parameters):
        result, resultslist = utils.execmd(parameters, returnstdout=True)
        self.assertEqual(result.returncode, 0)
        for line in resultslist:
            chk = utils.parse_logline(line)
            self.assertIsNotNone(chk)

    def chk4datacondition(self, parameters, element, operator, value, startonline=None, endonline=None):
        operator = operator.lower()
        result, resultslist = utils.execmd(parameters, returnstdout=True)
        self.assertEqual(result.returncode, 0)
        i = 1
        max = len(resultslist)
        for line in resultslist:
            if startonline:
                if startonline < i:
                    continue
            if endonline:
                if i > endonline:
                    break
            chk = utils.parse_logline(line)
            self.assertTrue(element in chk)
            if operator == "eq":
                self.assertTrue(chk[element] == value)
            elif operator == "lt":
                self.assertTrue(chk[element] < value)
            elif operator == "le":
                self.assertTrue(chk[element] <= value)
            elif operator == "gt":
                self.assertTrue(chk[element] > value)
            elif operator == "ge":
                self.assertTrue(chk[element] >= value)
            elif operator == "in":
                self.assertTrue(chk[element] in value)
            elif operator == "notin":
                self.assertTrue(chk[element] not in value)
            elif operator == "before":
                dt = self.assertIsDatetime(chk[element])
                self.assertTrue(dt <= dtparser.parse(value))
            elif operator == "after":
                dt = self.assertIsDatetime(chk[element])
                self.assertTrue(dt >= dtparser.parse(value))
            elif operator == "like":
                self.assertRegex(chk[element], value)
            elif operator == "notlike":
                self.assertNotRegex(chk[element], value)
            else:
                self.assertTrue(chk[element] == value)

    #
    # TEST CASES
    #

    def test_no_args_passed(self):
        """
        User passes no args
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("")

    def test_basic_stdout(self):
        """
        Basic streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4success("-o %s" % testtemplate1)

    def test_basic_stdout_defaultcount(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o %s" % testtemplate1, 10000)

    def test_basic_stdout_specifiedcount_small(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o -r 17 %s" % testtemplate1, 17)

    @skip
    def test_basic_stdout_specifiedcount_big_longrunning(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o -r 987654 %s" % testtemplate1, 987654)

    def test_basic_stdout_specifiedcount_waywaytoobig(self):
        """
        cant set -r that high! error
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("-o -r 9876543210 %s" % testtemplate1)

    def test_basic_stdout_data(self):
        """
        Correctly structured fake log entries streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4validlog("-o %s" % testtemplate1)


    def test_abort(self):
        """
        Test -a flag, should abort on line #3 in the test file
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("-a -o %s" % testtemplate1)

    def test_specific_dates(self):
        """
        Test -s and -e flags
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o %s' % testtemplate1,
                               "_ts", "after", '2018-12-31 23:59:59', startonline=None, endonline=None)
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o %s' % testtemplate1,
                               "_ts", "before", '2019-01-03 00:00:00', startonline=None, endonline=None)

    def test_ipfilter(self):
        """
        Test -i flag using example ip 188.143.232.240 in the test log file; see if it obfuscates to 188.143.232.[0-255]
        Then ensure no other IP pattern other than 188.143.232.[0-255] appears
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-i "188.143.232.240" -o %s' % testtemplate1,
                               "remote_addr", "like", "^188.143.232.(?<!\d)(?:[1-9]?\d|1\d\d|2(?:[0-4]\d|5[0-5]))(?!\d)",
                               startonline=None, endonline=None)
        self.chk4datacondition('-i "188.143.232.240" -o %s' % testtemplate1,
                               "remote_addr", "notlike", "^(?!188.143.232.(?<!\d)(?:[1-9]?\d|1\d\d|2(?:[0-4]\d|5[0-5]))(?!\d)).*$",
                               startonline=None, endonline=None)

