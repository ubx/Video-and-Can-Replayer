# coding: utf-8

"""
This module contains the generic :class:`LogReader` as
well as :class:`MessageSync` which plays back messages
in the recorded order an time intervals.
"""

from can import LogReader
from sqlite2 import SqliteReader2

class LogReader2(LogReader):

    @staticmethod
    def __new__(cls, filename, start_time=None, *args, **kwargs):
        """
        :param str filename: the filename/path the file to read from
        :param real start_time: the time where to start in log, in Epoch time format
        """
        if filename.endswith(".db") and start_time is not None:
            return SqliteReader2(filename, "messages", start_time, *args, **kwargs)
        else:
            return super().__new__(cls, filename, *args, **kwargs)
