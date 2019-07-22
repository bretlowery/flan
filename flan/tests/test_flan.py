import os
from flan.tests.utils import Utils
from unittest import TestCase, skip
import inspect
from dateutil import parser as dtparser

testpath = os.path.dirname(__file__)
testtemplate1 = os.path.join(testpath, '100testrecords.access.log')
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

    def chk4datacondition(self, parameters, element, operator, value, startonline=None, endonline=None, status='pass'):
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
            if status == 'fail':
                if operator == "eq":
                    self.assertFalse(chk[element] == value)
                elif operator == "lt":
                    self.assertFalse(chk[element] < value)
                elif operator == "le":
                    self.assertFalse(chk[element] <= value)
                elif operator == "gt":
                    self.assertFalse(chk[element] > value)
                elif operator == "ge":
                    self.assertFalse(chk[element] >= value)
                elif operator == "in":
                    self.assertFalse(chk[element] in value)
                elif operator == "notin":
                    self.assertFalse(chk[element] not in value)
                elif operator == "before":
                    dt = self.assertIsDatetime(chk[element])
                    self.assertFalse(dt <= dtparser.parse(value))
                elif operator == "after":
                    dt = self.assertIsDatetime(chk[element])
                    self.assertFalse(dt >= dtparser.parse(value))
                elif operator == "like":
                    self.assertNotRegex(chk[element], value)
                elif operator == "notlike":
                    self.assertRegex(chk[element], value)
                else:
                    self.assertFalse(chk[element] == value)
            else:
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

    # def chksums(self, parameters, compare2checksums=None):
    #     self.assertTrue(compare2checksums is list if compare2checksums else True)
    #     result, resultslist = utils.execmd(parameters, returnstdout=True)
    #     self.assertEqual(result.returncode, 0)
    #     checksums = []
    #     for line in resultslist:
    #         chk = utils.parse_logline(line)
    #         self.assertIsNotNone(chk)
    #         checksum = utils.checksum(line)
    #         if compare2checksums:
    #             self.assertIn(checksum, compare2checksums)
    #         else:
    #             checksums.append(checksum)
    #     return checksums

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
        self.chk4success("-o stdout %s" % testtemplate1)

    def test_basic_filewrite(self):
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

    def test_multiple_filewrite(self):
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

    def test_multiple_filewrite_gzip_1(self):
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


    def test_multiple_filewrite_gzip_2(self):
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

    def test_basic_stdout_defaultcount(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o stdout %s" % testtemplate1, 10000)

    def test_basic_stdout_specifiedcount_small(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o stdout -r 17 %s" % testtemplate1, 17)

    @skip
    def test_basic_stdout_specifiedcount_big_longrunning(self):
        """
        Count records streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals("-o stdout -r 987654 %s" % testtemplate1, 987654)

    def test_basic_stdout_specifiedcount_waywaytoobig(self):
        """
        cant set -r that high! error
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("-o stdout -r 9876543210 %s" % testtemplate1)

    def test_basic_stdout_data(self):
        """
        Correctly structured fake log entries streaming to stdout
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4validlog("-o stdout %s" % testtemplate1)

    def test_abort(self):
        """
        Test -a flag, should abort on line #3 in the test file
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4failure("-a -o stdout %s" % testtemplate1)

    def test_bad_dates(self):
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

    def test_date_ranges(self):
        """
        Test that -s and -e flags actually generate log entries within those dates
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "after", '2018-12-31 23:59:59', startonline=None, endonline=None)
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "before", '2019-01-03 00:00:00', startonline=None, endonline=None)
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "before", '2018-12-31 23:59:59', startonline=None, endonline=None, status='fail')
        self.chk4datacondition('-s "2019-01-01 00:00:00" -e "2019-01-02 23:59:59" -o stdout %s' % testtemplate1,
                               "_ts", "after", '2019-01-03 00:00:00', startonline=None, endonline=None, status='fail')

    def test_ipfilter(self):
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

    def test_replaylog(self):
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


    def test_nouatag(self):
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

    def test_linedelimiters(self):
        """
        Test a couple of -l flag settings
        """
        utils.newtest(inspect.currentframe().f_code.co_name.upper())
        self.chk4countequals('-r 3 -l CRLF -o stdout %s' % testtemplate1, countexpected=3, linedelimiter="\r\n")
        self.chk4countequals('-r 5 -l CR -o stdout %s' % testtemplate1, countexpected=5, linedelimiter="\r")
        self.chk4countequals('-r 7 -l LF -o stdout %s' % testtemplate1, countexpected=7, linedelimiter="\n")

