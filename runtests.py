#!/usr/bin/env python
from django.utils.encoding import force_str
from hvad.test_utils.cli import configure
from hvad.test_utils.context_managers import TemporaryDirectory
import argparse
import sys


def main(test_runner='hvad.test_utils.runners.NormalTestRunner', junit_output_dir='.',
         time_tests=False, verbosity=1, failfast=False, test_labels=None):
    if not test_labels:
        test_labels = ['hvad']
    with TemporaryDirectory() as STATIC_ROOT, TemporaryDirectory() as MEDIA_ROOT:
        configure(LANGUAGE_CODE='en', TEST_RUNNER=test_runner, JUNIT_OUTPUT_DIR=junit_output_dir,
            TIME_TESTS=time_tests, STATIC_ROOT=STATIC_ROOT, MEDIA_ROOT=MEDIA_ROOT)
        from django.core import checks
        errors = checks.run_checks()
        if errors:
            for error in errors:
                print(force_str(error))
            sys.exit(len(errors))

        from django.conf import settings
        from django.test.utils import get_runner
        TestRunner = get_runner(settings)

        test_runner = TestRunner(pattern='*.py', verbosity=verbosity, interactive=False, failfast=failfast)
        failures = test_runner.run_tests(test_labels)
    sys.exit(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--jenkins', action='store_true', default=False,
            dest='jenkins')
    parser.add_argument('--jenkins-data-dir', default='.', dest='jenkins_data_dir')
    parser.add_argument('--failfast', action='store_true', default=False,
            dest='failfast')
    parser.add_argument('--verbosity', default=1)
    parser.add_argument('--time-tests', action='store_true', default=False,
            dest='time_tests')
    parser.add_argument('test_labels', nargs='*')
    args = parser.parse_args()
    if getattr(args, 'jenkins', False):
        test_runner = 'hvad.test_utils.runners.JenkinsTestRunner'
    else:
        test_runner = 'hvad.test_utils.runners.NormalTestRunner'
    junit_output_dir = getattr(args, 'jenkins_data_dir', '.')
    time_tests = getattr(args, 'time_tests', False)
    test_labels = ['hvad.%s' % label for label in args.test_labels]
    main(test_runner=test_runner, junit_output_dir=junit_output_dir, time_tests=time_tests,
         verbosity=args.verbosity, failfast=args.failfast, test_labels=test_labels)
    
