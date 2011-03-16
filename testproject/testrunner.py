from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner
from nani.test_utils.unittest import TextTestRunner

try: # pragma: no cover
    from xmlrunner import XMLTestRunner as runner
except: # pragma: no cover
    runner = False

class TestSuiteRunner(DjangoTestSuiteRunner): # pragma: no cover
    use_runner = runner

    def run_suite(self, suite, **kwargs):
        if self.use_runner and not self.failfast:
            return self.use_runner(
                output=getattr(settings, 'JUNIT_OUTPUT_DIR', '.')
            ).run(suite)
        else:
            return TextTestRunner(**kwargs).run(suite)