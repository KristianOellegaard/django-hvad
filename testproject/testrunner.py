from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner
import os

try: # pragma: no cover
    from xmlrunner import XMLTestRunner
    class runner(XMLTestRunner):
        def _make_result(self):
            return _UnicodeXMLTestResult(self.stream, self.descriptions, 
                self.verbosity, self.elapsed_times)
except: # pragma: no cover
    runner = False
    _UnicodeXMLTestResult = None

if runner:
    from xmlrunner import _XMLTestResult
    class _UnicodeXMLTestResult(_XMLTestResult):
        
        def generate_reports(self, test_runner):
            "Generates the XML reports to a given XMLTestRunner object."
            from xml.dom.minidom import Document
            all_results = self._get_info_by_testcase()
            
            if type(test_runner.output) == str and not \
                os.path.exists(test_runner.output):
                os.makedirs(test_runner.output)
            
            for suite, tests in all_results.items():
                doc = Document()
                
                # Build the XML file
                testsuite = _XMLTestResult._report_testsuite(suite, tests, doc)
                for test in tests:
                    _XMLTestResult._report_testcase(suite, test, testsuite, doc)
                _XMLTestResult._report_output(test_runner, testsuite, doc)
                xml_content = doc.toprettyxml(indent='\t').encode('utf-8')
                
                if type(test_runner.output) is str:
                    report_file = file('%s%sTEST-%s.xml' % \
                        (test_runner.output, os.sep, suite), 'w')
                    try:
                        report_file.write(xml_content)
                    finally:
                        report_file.close()
                else:
                    # Assume that test_runner.output is a stream
                    test_runner.output.write(xml_content)

class TestSuiteRunner(DjangoTestSuiteRunner): # pragma: no cover
    use_runner = runner

    def run_suite(self, suite, **kwargs):
        if self.use_runner and not self.failfast:
            return self.use_runner(
                output=getattr(settings, 'JUNIT_OUTPUT_DIR', '.')
            ).run(suite)
        else:
            return super(TestSuiteRunner, self).run_suite(suite, **kwargs)