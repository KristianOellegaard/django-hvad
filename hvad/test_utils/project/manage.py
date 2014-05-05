#!/usr/bin/env python
from django.core.management import execute_from_command_line
import sys
import os

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASEDIR)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hvad.test_utils.project.settings")
    execute_from_command_line(sys.argv)
