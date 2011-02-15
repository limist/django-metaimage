#!/usr/bin/env python

"""Utility functions to open URLs are here, particularly to access web
services like Amazon API via REST format.

Code originally from Mark Pilgrim's book, Dive Into Python.
"""

from cStringIO import StringIO
import gzip
import socket
from time import sleep
import urllib2 
import urlparse


USER_AGENT = 'Test'
FETCH_RETRY_NUM = 5
FETCH_RETRY_DELAY = 1.2  # seconds
FETCH_MAX_SIZE = 1048576  # 1 MB
# Set global timeout
timeout = 5  # seconds
socket.setdefaulttimeout(timeout)


class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        return result


class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        result = urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
        result.status = code
        return result


def open_anything(source, etag=None, lastmodified=None, agent=USER_AGENT):
    """URL, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the lastmodified argument is supplied, it must be a formatted
    date/time string in GMT (as returned in the Last-Modified header of
    a previous request).  The formatted date/time will be used
    as the value of an If-Modified-Since request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.
    """
    if hasattr(source, 'read'):
        return source
    if source == '-':
        return sys.stdin
    if urlparse.urlparse(source)[0] == 'http':
        # Open URL with urllib2
        request = urllib2.Request(source)
        request.add_header('User-Agent', agent)
        if lastmodified:
            request.add_header('If-Modified-Since', lastmodified)
        if etag:
            request.add_header('If-None-Match', etag)
        request.add_header('Accept-encoding', 'gzip')
        opener = urllib2.build_opener(SmartRedirectHandler(), DefaultErrorHandler())
        try:
            return opener.open(request)
        except urllib2.URLError:
            return None
    # Try to open with native open function (if source is a filename)
    try:
        return open(source)
    except (IOError, OSError):
        pass
    # Treat source as string
    return StringIO(str(source))


def fetch(source, etag=None, lastmodified=None, agent=USER_AGENT, retry_attempts=FETCH_RETRY_NUM, retry_delay=FETCH_RETRY_DELAY, max_size=FETCH_MAX_SIZE):
    """Fetch data and metadata from a URL, file, stream, or string.
    """
    result = {}
    attempt_num = 0
    f = None
    while f is None and attempt_num < retry_attempts:
        if attempt_num > 0:
            sleep(retry_delay)
        attempt_num += 1
        f = open_anything(source, etag, lastmodified, agent)
    result['data'] = f.read(max_size)
    if hasattr(f, 'headers'):
        # save ETag, if the server sent one
        result['etag'] = f.headers.get('ETag')
        # save Last-Modified header, if the server sent one
        result['lastmodified'] = f.headers.get('Last-Modified')
        if f.headers.get('content-encoding') == 'gzip':
            # data came back gzip-compressed, decompress it
            result['data'] = gzip.GzipFile(fileobj=StringIO(result['data'])).read()
    if hasattr(f, 'url'):
        result['url'] = f.url
        result['status'] = 200
    if hasattr(f, 'status'):
        result['status'] = f.status
    f.close()
    return result
