import os
from flan.tests.utils import Utils
from unittest import TestCase, skip
import inspect
from dateutil import parser as dtparser

testpath = os.path.dirname(__file__)
testtemplate1 = os.path.join(testpath, '99good1bad.test.access.log')
testout = os.path.join(testpath, 'testresults')
testreplay = os.path.join(testpath, '../flan.replay')
utils = Utils()


class FlanTestCases(TestCase):

    #
    # CUSTOM ASSERTS
    #

    def assertFileExists(self, value):
        fileexists = False
        if os.path.exists(value):
            fileexists = os.path.isfile(value)
        self.assertTrue(fileexists is True)

    def assertFileNotExists(self, value):
        fileexists = False
        if os.path.exists(value):
            fileexists = os.path.isfile(value)
        self.assertFalse(fileexists is True)

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

    def chk4success(self, parameters, linedelimiter="\r\n"):
        result = utils.execmd(parameters, linedelimiter=linedelimiter)
        self.assertEqual(result.returncode, 0)

    def chk4failure(self, parameters, linedelimiter="\r\n"):
        result = utils.execmd(parameters, linedelimiter=linedelimiter)
        self.assertNotEqual(result.returncode, 0)

    def chk4countequals(self, parameters, countexpected, linedelimiter="\r\n"):
        result, resultslist = utils.execmd(parameters, returnstdout=True, linedelimiter=linedelimiter)
        self.assertEqual(result.returncode, 0)
        resultsfound = len(resultslist)
        self.assertEqual(resultsfound, countexpected)

    def chk4validlog(self, parameters):
        result, resultslist = utils.execmd(parameters, returnstdout=True)
        self.assertEqual(result.returncode, 0)
        for line in resultslist:
            chk = utils.parse_logline(line)
            self.assertIsNotNone(chk)

    def _dtt(self, x, op, val):
        dt1 = self.assertIsDatetime(x)
        dt2 = self.assertIsDatetime(val)
        if op == "after":
            self.assertTrue(dt1 >= dt2)
        elif op == "before":
            self.assertTrue(dt1 <= dt2)
        else:
            ValueError("invalid op passed to _dtt")

    def _dtf(self, x, op, val):
        dt1 = self.assertIsDatetime(x)
        dt2 = self.assertIsDatetime(val)
        if op == "after":
            self.assertFalse(dt1 >= dt2)
        elif op == "before":
            self.assertFalse(dt1 <= dt2)
        else:
            ValueError("invalid op passed to _dtf")

    def _passes(self, x, op, value):
        if op == "eq":
            self.assertTrue(x == value)
        elif op == "lt":
            self.assertTrue(x < value)
        elif op == "le":
            self.assertTrue(x <= value)
        elif op == "gt":
            self.assertTrue(x > value)
        elif op == "ge":
            self.assertTrue(x >= value)
        elif op == "in":
            self.assertTrue(x in value)
        elif op == "notin":
            self.assertTrue(x not in value)
        elif op == "before":
            self._dtt(x, op, value)
        elif op == "after":
            self._dtt(x, op, value)
        elif op == "like":
            self.assertRegex(x, value)
        elif op == "notlike":
            self.assertNotRegex(x, value)
        else:
            ValueError("invalid op passed to _passes")

    def _fails(self, x, op, value):
        if op == "eq":
            self.assertFalse(x == value)
        elif op == "lt":
            self.assertFalse(x < value)
        elif op == "le":
            self.assertFalse(x <= value)
        elif op == "gt":
            self.assertFalse(x > value)
        elif op == "ge":
            self.assertFalse(x >= value)
        elif op == "in":
            self.assertFalse(x in value)
        elif op == "notin":
            self.assertFalse(x not in value)
        elif op == "before":
            self._dtf(x, op, value)
        elif op == "after":
            self._dtf(x, op, value)
        elif op == "like":
            self.assertNotRegex(x, value)
        elif op == "notlike":
            self.assertRegex(x, value)
        else:
            ValueError("invalid op passed to _fails")

    def _chk(self, status, chk, element, operator, value):
        self.assertTrue(element in chk)
        if status == 'fail':
            self._fails(chk[element], operator, value)
        elif status == 'pass':
            self._passes(chk[element], operator, value)
        else:
            ValueError("invalid status passed to _chk")

    def chk4datacondition(self, parameters, element, operator, value, startonline=None, endonline=None, scope="every", status='pass'):
        operator = operator.lower()
        result, resultslist = utils.execmd(parameters, returnstdout=True)
        self.assertEqual(result.returncode, 0)
        i = 0
        max = len(resultslist)
        rtn = False
        for line in resultslist:
            i += 1
            if startonline:
                if startonline < i:
                    continue
            if endonline:
                if i > endonline:
                    break
            chk = utils.parse_logline(line)
            if scope == "any":
                try:
                    self._chk(status, chk, element, operator, value)
                    rtn = True
                except AssertionError:
                    pass
                if rtn:
                    break
            elif scope == "every":
                self._chk(status, chk, element, operator, value)
                rtn = True
            else:
                ValueError("invalid scope passed to chk4datacondition")
        return rtn

    #
    # TEST CASES
    #

    def test_1000_no_args_passed(self):
        """
        User passes no args
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("")

    def test_1010_basic_stdout(self):
        """
        Basic streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4success("-o stdout %s" % testtemplate1)

    def test_1020_abort(self):
        """
        Test -a flag, should abort on line #3 in the test file
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("-a -o stdout %s" % testtemplate1)

    def test_1030_basic_filewrite(self):
        """
        Basic file writing to one output access.log
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        x = testout
        if os.path.exists(testout):
            utils.wipe(testout)
        os.mkdir(testout)
        self.chk4success("-n 1 %s %s" % (testtemplate1, testout))
        self.assertFileExists("%s/access.log" % testout)

    def test_1040_multiple_filewrite(self):
        """
        File writing to three output access logs
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        if os.path.exists(testout):
            utils.wipe(testout)
        os.mkdir(testout)
        self.chk4success("-n 3 %s %s" % (testtemplate1, testout))
        self.assertFileExists("%s/access.log" % testout)
        self.assertFileExists("%s/access.log.1" % testout)
        self.assertFileExists("%s/access.log.2" % testout)
        self.assertFileNotExists("%s/access.log.3" % testout)

    def test_1050_multiple_filewrite_gzip_1(self):
        """
        File writing to three output access logs, one gzipped
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        if os.path.exists(testout):
            utils.wipe(testout)
        os.mkdir(testout)
        self.chk4success("-n 3 -g 1 %s %s" % (testtemplate1, testout))
        self.assertFileExists("%s/access.log" % testout)
        self.assertFileNotExists("%s/access.log.gz" % testout)
        self.assertFileExists("%s/access.log.1" % testout)
        self.assertFileNotExists("%s/access.log.1.gz" % testout)
        self.assertFileNotExists("%s/access.log.2" % testout)
        self.assertFileExists("%s/access.log.2.gz" % testout)
        self.assertFileNotExists("%s/access.log.3" % testout)
        self.assertFileNotExists("%s/access.log.3.gz" % testout)


    def test_1050_multiple_filewrite_gzip_2(self):
        """
        File writing to three output access logs, two gzipped
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        if os.path.exists(testout):
            utils.wipe(testout)
        os.mkdir(testout)
        self.chk4success("-n 3 -g 2 %s %s" % (testtemplate1, testout))
        self.assertFileExists("%s/access.log" % testout)
        self.assertFileNotExists("%s/access.log.gz" % testout)
        self.assertFileNotExists("%s/access.log.1" % testout)
        self.assertFileExists("%s/access.log.1.gz" % testout)
        self.assertFileNotExists("%s/access.log.2" % testout)
        self.assertFileExists("%s/access.log.2.gz" % testout)
        self.assertFileNotExists("%s/access.log.3" % testout)
        self.assertFileNotExists("%s/access.log.3.gz" % testout)

    def test_1060_basic_stdout_defaultcount(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o stdout %s" % testtemplate1, 10000)

    def test_1070_basic_stdout_specifiedcount_small(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o stdout -r 17 %s" % testtemplate1, 17)

    @skip
    def test_1080_basic_stdout_specifiedcount_big_longrunning(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o stdout -r 987654 %s" % testtemplate1, 987654)

    def test_1090_basic_stdout_specifiedcount_waywaytoobig(self):
        """
        cant set -r that high! error
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("-o stdout -r 9876543210 %s" % testtemplate1)

    def test_1100_basic_stdout_data(self):
        """
        Correctly structured fake log entries streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4validlog("-o stdout %s" % testtemplate1)


    def test_1110_bad_dates(self):
        """
        Check for badly formatted or specified -s and -e datetimes
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4success('-s "2019-01-01 00:00:00" -o stdout %s' % testtemplate1)
        self.chk4success('-e "2029-01-01 00:00:00" -o stdout %s' % testtemplate1)
        self.chk4failure('-e "2019-01-01 00:00:00" -o stdout %s' % testtemplate1)
        self.chk4failure('-s "THIS IS NOT A DATETIME" -o stdout %s' % testtemplate1)
        self.chk4failure('-e "THIS IS NOT A DATETIME EITHER" -o stdout %s' % testtemplate1)
        self.chk4failure('-s "2019-01-01 00:00:00" -e "1999-01-01 00:00:00" -o stdout %s' % testtemplate1)
        self.chk4failure('-s "2019-01-01 00:00:00" -e "2019-01-01 00:00:00" -o stdout %s' % testtemplate1)

    def test_1120_date_range_1(self):
        """
        Test -s and -e lower bound inclusive
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "after", '2018-12-31 23:59:59', startonline=None, endonline=None, status='pass')

    def test_1120_date_range_2(self):
        """
        Test -s and -e upper bound inclusive
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "before", '2019-01-03 00:00:00', startonline=None, endonline=None, status='pass')

    def test_1120_date_range_3(self):
        """
        Test -s and -e lower bound exclusive
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "before", '2018-12-31 23:59:59', startonline=None, endonline=None, status='fail')

    def test_1120_date_range_4(self):
        """
        Test -s and -e upper bound exclusive
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "after", '2019-01-03 00:00:00', startonline=None, endonline=None, status='fail')

    def test_1120_date_range_5(self):
        """
        Test -s and -e lower bound inclusive boundary condition
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        anypass = self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "after", "2019-01-02 22:00:00", startonline=None, endonline=None, status='pass', scope='any')
        self.assertTrue(anypass)

    def test_1120_date_range_6(self):
        """
        Test -s and -e upper bound inclusive boundary condition
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        anypass = self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "before", '2019-01-01 02:00:00', startonline=None, endonline=None, status='pass', scope='any')
        self.assertTrue(anypass)

    def test_1130_ipfilter(self):
        """
        Test -i flag using example ip 188.143.232.240 in the test log file; see if it obfuscates to 188.143.232.[0-255]
        Then ensure no other IP pattern other than 188.143.232.[0-255] appears
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-i "188.143.232.240" -o stdout %s' % testtemplate1,
                               "remote_addr", "like", "^188.143.232.(?<!\d)(?:[1-9]?\d|1\d\d|2(?:[0-4]\d|5[0-5]))(?!\d)",
                               startonline=None, endonline=None)
        self.chk4datacondition('-i "188.143.232.240" -o stdout %s' % testtemplate1,
                               "remote_addr", "notlike", "^(?!188.143.232.(?<!\d)(?:[1-9]?\d|1\d\d|2(?:[0-4]\d|5[0-5]))(?!\d)).*$",
                               startonline=None, endonline=None)

    def test_1140_replaylog(self):
        """
        Basic replay log test
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        if os.path.isfile(testreplay):
            os.unlink(testreplay)
        self.assertFileNotExists(testreplay)
        self.chk4success("-y -o stdout %s" % testtemplate1)
        self.assertFileExists(testreplay)
        self.chk4success("-y -o stdout %s" % testtemplate1)
        self.assertFileExists(testreplay)


    def test_1150_nouatag(self):
        """
        Test --nouatag flag
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-o stdout %s' % testtemplate1,
                               "http_user_agent", "like", "(Flan/+\d.+\d.+\d. \(https://bret\.guru\/flan\))$",
                               startonline=None, endonline=None)
        self.chk4datacondition('--nouatag -o stdout %s' % testtemplate1,
                               "http_user_agent", "notlike", "(Flan/+\d.+\d.+\d. \(https://bret\.guru\/flan\))$",
                               startonline=None, endonline=None)

    def test_1160_linedelimiters(self):
        """
        Test a couple of -l flag settings
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals('-r 3 -l CRLF -o stdout %s' % testtemplate1, countexpected=3, linedelimiter="\r\n")
        self.chk4countequals('-r 5 -l CR -o stdout %s' % testtemplate1, countexpected=5, linedelimiter="\r")
        self.chk4countequals('-r 7 -l LF -o stdout %s' % testtemplate1, countexpected=7, linedelimiter="\n")

