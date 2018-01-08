#!/usr/bin/env python
import os
import sys
import django
import logging
from pythonrv import rv

if __name__ == "__main__":
    django.setup()

    from main import auction_rvspecs

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emg.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

