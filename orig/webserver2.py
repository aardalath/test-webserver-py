#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
Simple web server that demonstrates how browser/server interactions
work for GET and POST requests. Use it as a starting point to create a
custom web server for handling specific requests but don't try to use
it for any production work.

You start by creating a simple index.html file in web directory
somewhere like you home directory: ~/www.

You then add an HTML file: ~/www/index.html. It can be very
simple. Something like this will do nicely:

   <!DOCTYPE html>
   <html>
     <head>
       <meta charset="utf-8">
       <title>WebServer Test</title>
     </head>
     <body>
       <p>Hello, world!</p>
     </body>
   </html>

At this point you have a basic web infrastructure with a single file
so you start the server and point to the ~/www root directory:

   $ webserver.py -r ~/www

This will start the web server listening on your localhost on port
8080. You can change both the host name and the port using the --host
and --port options. See the on-line help for more information (-h,
--help).

If you do not specify a root directory, it will use the directory that
you started the server from.

Now go to your browser and enter http://0.0.0.0:8080 on the command
line and you will see your page.

Try entering http://0.0.0.0:8080/info to see some server information.

You can also use http://127.0.0.1.

By default the server allows you to see directory listings if there is
no index.html or index.htm file. You can disable this by specifying
the --no-dirlist option.

If you want to see a directory listing of a directory that contains a
index.html or index.htm directory, type three trailing backslashes in
the URL like this: http://foo/bar/spam///. This will not work if the
--no-dirlist option is specified.

The default logging level is "info". You can change it using the
"--level" option.

The example below shows how to use a number of the switches to run a
server for host foobar on port 8080 with no directory listing
capability and very little output serving files from ~/www:

  $ hostname
  foobar
  $ webserver --host foobar --port 8080 --level warning --no-dirlist --rootdir ~/www

To daemonize a process, specify the -d or --daemonize option with a
process directory. That directory will contain the log (stdout), err
(stderr) and pid (process id) files for the daemon process. Here is an
example:

  $ hostname
  foobar
  $ webserver --host foobar --port 8080 --level warning --no-dirlist --rootdir ~/www --daemonize ~/www/logs
  $ ls ~/www/logs
  webserver-foobar-8080.err webserver-foobar-8080.log webserver-foobar-8080.pid
'''

# LICENSE
#   Copyright (c) 2015 Joe Linoff
#   
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#   
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#   
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.

# VERSIONS
#   1.0  initial release
#   1.1  replace req with self in request handler, add favicon
#   1.2  added directory listings, added --no-dirlist, fixed plain text displays, logging level control, daemonize
VERSION = '1.2'

from time import gmtime, strftime, time, sleep

import argparse
import BaseHTTPServer
import cgi
import logging
import os
import sys
import urlparse
import re
import json
import posixpath

from astropy.io import fits
import numpy as np

def make_request_handler_class(opts):
    '''
    Factory to make the request handler and add arguments to it.

    It exists to allow the handler to access the opts.path variable
    locally.
    '''
    class QLARqstHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        '''
        Factory generated request handler class that contain
        additional class variables.
        '''
        m_opts = opts
        content_type = {
            '.css': 'text/css',
            '.gif': 'image/gif',
            '.htm': 'text/html',
            '.html': 'text/html',
            '.jpeg': 'image/jpeg',
            '.jpg': 'image/jpg',
            '.js': 'text/javascript',
            '.png': 'image/png',
            '.text': 'text/plain',
            '.txt': 'text/plain',
            '.fits': 'application/fits',
            '.json': 'application/json'
        }

        pool_of_files = []
        obs_id = 12000
        input_files_dir = "input"

        def send_content(self, code=200, type='text/html'):
            '''
            Send response code (default 200), and content type (default text/html)
            :param code: response code (default:200)
            :param type: content type (default:text/html)
            :return: -
            '''
            self.send_response(200)  # OK
            if len(type) > 0:
                self.send_header('Content-type', type)
                self.end_headers()

        def create_dummy_file(self, file_name):
            '''
            Create dummy FITS file
            :param file_name: Name of the file to be created
            :return:
            '''
            n = np.arange(100.0)  # a simple sequence of floats from 0.0 to 99.9
            hdu = fits.PrimaryHDU(n)
            full_file_name = QLARqstHandler.m_opts.rootdir + "/" + file_name
            logging.debug('Trying to create dummy file {}'.format(full_file_name))
            hdu.writeto(full_file_name, clobber=True)

        def get_new_input_files(self, pool):
            '''
            Method to get new file names, with path relative to rootdir.
            This simple test does not get file names from the file system, but
            generates them:
            :param pool: List to append the new files to
            :return:
            '''
            for x in range(10):
                for dither in range(1, 5):
                    datetime_tag = strftime("%Y%m%dT%H%M%S", gmtime(time() + 100000000 + x * 100))
                    file_name = 'EUC_LE1_VIS-W-{}-{}_{}.0Z.fits'.format(QLARqstHandler.obs_id, dither, datetime_tag)
                    pool.append(file_name)
                    # create dummy file
                    logging.debug('New file: {}'.format(file_name))
                    self.create_dummy_file(QLARqstHandler.input_files_dir + '/' + file_name)
                    QLARqstHandler.obs_id = QLARqstHandler.obs_id + 1

        def do_HEAD(self):
            '''
            Handle a HEAD request.
            '''
            logging.debug('HEADER %s' % (self.path))
            self.send_content()

        def do_info(self):
            '''
            Display some useful server information.

            http://127.0.0.1:8080/info
            '''
            self.send_content()

            self.wfile.write('<html><head><title>Server Info</title></head>')
            self.wfile.write('<body><table><tbody>')
            self.wfile.write('<tr><td>client_address</td><td>%r</td></tr>' % (repr(self.client_address)))
            self.wfile.write('<tr><td>command</td><td>%r</td></tr>' % (repr(self.command)))
            self.wfile.write('<tr><td>headers</td><td>%r</td></tr>' % (repr(self.headers)))
            self.wfile.write('<tr><td>path</td><td>%r</td></tr>' % (repr(self.path)))
            self.wfile.write('<tr><td>server_version</td><td>%r</td></tr>' % (repr(self.server_version)))
            self.wfile.write('<tr><td>sys_version</td><td>%r</td></tr>' % (repr(self.sys_version)))
            self.wfile.write('</tbody></table></body></html>')

        def do_get_task(self):
            '''
            Provide input data to the client to run a new task

            http://127.0.0.1:8080/get_task
            :return: -
            '''
            pool_of_files = []
            # Check pool of files
            if len(QLARqstHandler.pool_of_files) < 1:
                self.get_new_input_files(QLARqstHandler.pool_of_files)

            in_file = QLARqstHandler.pool_of_files.pop(0)
            out_file = re.sub('.fits', '.json', re.sub('LE1_VIS', 'QLA_LE1-VIS', in_file))
            log_file = re.sub('.json', '.log', re.sub('LE1_VIS', 'LE1-VIS-LOG', out_file))
            new_task_id = strftime("QDTsrv_%Y%m%d-%H%M%S", gmtime())
            
            # Build JSON dictionary with task information
            task_params = {'task_id': new_task_id,
                           'in_file': in_file,
                           'out_file': out_file,
                           'log_file': log_file,
                           'retrieve_path': QLARqstHandler.input_files_dir}
            task_params_jsonstr = json.dumps(task_params)
            logging.debug(task_params_jsonstr)

            # Send it
            self.send_content(type='application/json')
            self.wfile.write(task_params_jsonstr)
                
        def do_end_task(self):
            '''
            Provide input data to the client to run a new task

            http://127.0.0.1:8080/get_task
            '''
            self.send_content()

        def send_file(self, path):
            '''
            Sends an existing, requested file
            :param path: Full path of the requested file
            :return: -
            '''
            _, ext = os.path.splitext(path)
            ext = ext.lower()

            # This is a test, files are tiny, so let's simulate that it takes a bit of time
            sleep(10)

            # If it is a known extension, set the correct
            # content type in the response.
            if ext in QLARqstHandler.content_type:
                self.send_content(type=QLARqstHandler.content_type[ext])
                with open(path) as ifp:
                    self.wfile.write(ifp.read())
            else:
                # Unknown file type or a directory.
                # Treat it as plain text.
                self.send_content()
                with open(path) as ifp:
                    self.wfile.write(ifp.read())

        def retrieve_outputs(self):
            '''
            Retrieves a posted file
            :return: -
            '''
            logging.debug("Retrieving outputs . . .")
            boundary = self.headers.plisttext.split("=")[1]
            remainbytes = int(self.headers['Content-length'])
            line = self.rfile.readline()
            remainbytes -= len(line)
            if not boundary in line:
                return (False, "Content NOT begin with boundary")
            line = self.rfile.readline()
            remainbytes -= len(line)
            fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line)
            if not fn:
                return (False, "Can't find out file name...")
            path = self.translate_path(self.path)
            fn = os.path.join(path, fn[0])
            line = self.rfile.readline()
            remainbytes -= len(line)
            try:
                out = open(fn, 'wb')
            except IOError:
                return (False, "Can't create file to write, do you have permission to write?")

            preline = self.rfile.readline()
            remainbytes -= len(preline)
            while remainbytes > 0:
                line = self.rfile.readline()
                remainbytes -= len(line)
                if boundary in line:
                    preline = preline[0:-1]
                    if preline.endswith('\r'):
                        preline = preline[0:-1]
                    out.write(preline)
                    out.close()
                    # This is a test, files are tiny, so let's simulate that it takes a bit of time
                    sleep(10)
                    return (True, "File '%s' upload success!" % fn)
                else:
                    out.write(preline)
                    preline = line
            return (False, "Unexpect Ends of data.")

        def translate_path(self, path):
            """Translate a /-separated PATH to the local filename syntax.

            Components that mean special things to the local file system
            (e.g. drive or directory names) are ignored.  (XXX They should
            probably be diagnosed.)

            """
            # abandon query parameters
            path = path.split('?', 1)[0]
            path = path.split('#', 1)[0]
            path = posixpath.normpath(urllib.unquote(path))
            words = path.split('/')
            words = filter(None, words)
            path = os.getcwd()
            for word in words:
                drive, word = os.path.splitdrive(word)
                head, word = os.path.split(word)
                if word in (os.curdir, os.pardir): continue
                path = os.path.join(path, word)
            return path

        def do_GET(self):
            '''
            Handle a GET request.
            '''
            logging.debug('GET %s' % (self.path))

            # Parse out the arguments.
            # The arguments follow a '?' in the URL. Here is an example:
            #   http://example.com?arg1=val1
            args = {}
            idx = self.path.find('?')
            if idx >= 0:
                rpath = self.path[:idx]
                args = urlparse.parse_qs(self.path[idx+1:])
            else:
                rpath = self.path

            # Print out logging information about the path and args.
            if 'content-type' in self.headers:
                ctype, _ = cgi.parse_header(self.headers['content-type'])
                logging.debug('TYPE %s' % (ctype))

            logging.debug('PATH %s' % (rpath))
            logging.debug('ARGS %d' % (len(args)))
            if len(args):
                i = 0
                for key in sorted(args):
                    logging.debug('ARG[%d] %s=%s' % (i, key, args[key]))
                    i += 1

            # Check to see whether the file is stored locally,
            # if it is, display it.
            # There is special handling for http://127.0.0.1/info. That URL
            # displays some internal information.
            if self.path == '/info' or self.path == '/info/':
                self.do_info()
            elif self.path == '/get_task' or self.path == '/get_task/':
                self.do_get_task()
            elif self.path == '/end_task' or self.path == '/end_task/':
                self.do_end_task()
            else:
                # Get the file path.
                path = QLARqstHandler.m_opts.rootdir + rpath
                dirpath = None
                logging.debug('FILE %s' % (path))

                # If it is a directory look for index.html
                # or process it directly if there are 3
                # trailing slashed.
                ## Allow the user to type "///" at the end to see the
                ## directory listing.
                #if rpath[-3:] == '///':
                #    dirpath = path
                #el
                if os.path.exists(path) and os.path.isdir(path):
                    dirpath = path  # the directory portion
                    index_files = ['/index.html', '/index.htm', ]
                    for index_file in index_files:
                        tmppath = path + index_file
                        if os.path.exists(tmppath):
                            path = tmppath
                            break

                if os.path.exists(path) and os.path.isfile(path):
                    # This is valid file, send it as the response
                    # after determining whether it is a type that
                    # the server recognizes.
                    self.send_file(path)
                else:
                    #if dirpath is None or self.m_opts.no_dirlist == True:
                        # Invalid file path, respond with a server access error
                        self.send_content(code=500)  # generic server error for now

                        self.wfile.write('<html>')
                        self.wfile.write('  <head>')
                        self.wfile.write('    <title>Server Access Error</title>')
                        self.wfile.write('  </head>')
                        self.wfile.write('  <body>')
                        self.wfile.write('    <p>Server access error.</p>')
                        self.wfile.write('    <p>%r</p>' % (repr(self.path)))
                        self.wfile.write('    <p><a href="%s">Back</a></p>' % (rpath))
                        self.wfile.write('  </body>')
                        self.wfile.write('</html>')
                    # else:
                    #     # List the directory contents. Allow simple navigation.
                    #     logging.debug('DIR %s' % (dirpath))
                    #
                    #     self.send_content()
                    #
                    #     self.wfile.write('<html>')
                    #     self.wfile.write('  <head>')
                    #     self.wfile.write('    <title>%s</title>' % (dirpath))
                    #     self.wfile.write('  </head>')
                    #     self.wfile.write('  <body>')
                    #     self.wfile.write('    <a href="%s">Home</a><br>' % ('/'));
                    #
                    #     # Make the directory path navigable.
                    #     dirstr = ''
                    #     href = None
                    #     for seg in rpath.split('/'):
                    #         if href is None:
                    #             href = seg
                    #         else:
                    #             href = href + '/' + seg
                    #             dirstr += '/'
                    #         dirstr += '<a href="%s">%s</a>' % (href, seg)
                    #     self.wfile.write('    <p>Directory: %s</p>' % (dirstr))
                    #
                    #     # Write out the simple directory list (name and size).
                    #     self.wfile.write('    <table border="0">')
                    #     self.wfile.write('      <tbody>')
                    #     fnames = ['..']
                    #     fnames.extend(sorted(os.listdir(dirpath), key=str.lower))
                    #     for fname in fnames:
                    #         self.wfile.write('        <tr>')
                    #         self.wfile.write('          <td align="left">')
                    #         path = rpath + '/' + fname
                    #         fpath = os.path.join(dirpath, fname)
                    #         if os.path.isdir(path):
                    #             self.wfile.write('            <a href="%s">%s/</a>' % (path, fname))
                    #         else:
                    #             self.wfile.write('            <a href="%s">%s</a>' % (path, fname))
                    #         self.wfile.write('          <td>&nbsp;&nbsp;</td>')
                    #         self.wfile.write('          </td>')
                    #         self.wfile.write('          <td align="right">%d</td>' % (os.path.getsize(fpath)))
                    #         self.wfile.write('        </tr>')
                    #     self.wfile.write('      </tbody>')
                    #     self.wfile.write('    </table>')
                    #     self.wfile.write('  </body>')
                    #     self.wfile.write('</html>')

        def do_POST(self):
            '''
            Handle POST requests.
            '''
            logging.debug('POST %s' % (self.path))

            # CITATION: http://stackoverflow.com/questions/4233218/python-basehttprequesthandler-post-variables
            ctype, pdict = cgi.parse_header(self.headers['content-type'])
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers['content-length'])
                postvars = urlparse.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                postvars = {}

            # Get the "Back" link.
            back = self.path if self.path.find('?') < 0 else self.path[:self.path.find('?')]
            logging.debug("back = '" + back + "'")
            # Print out logging information about the path and args.
            logging.debug('TYPE %s' % (ctype))
            logging.debug('PATH %s' % (self.path))
            logging.debug('ARGS %d' % (len(postvars)))
            if len(postvars):
                i = 0
                for key in sorted(postvars):
                    logging.debug('ARG[%d] %s=%s' % (i, key, postvars[key]))
                    i += 1

            for key in sorted(postvars):
                if key == 'task_id':
                    task_id = postvars[key]
                    self.send_content(code=100, type='')
                    r, info = self.retrieve_outputs()
                    if r:
                        logging.debug("File retrieval completed - {}".format(info))
                    else:
                        logging.debug("File retrieval failed - {}".format(info))

            # Tell the browser everything is OK
            self.send_content(type='')

            # # Display the POST variables.
            # self.wfile.write('<html>')
            # self.wfile.write('  <head>')
            # self.wfile.write('    <title>Server POST Response</title>')
            # self.wfile.write('  </head>')
            # self.wfile.write('  <body>')
            # self.wfile.write('    <p>POST variables (%d).</p>' % (len(postvars)))
            #
            # if len(postvars):
            #     # Write out the POST variables in 3 columns.
            #     self.wfile.write('    <table>')
            #     self.wfile.write('      <tbody>')
            #     i = 0
            #     for key in sorted(postvars):
            #         i += 1
            #         val = postvars[key]
            #         self.wfile.write('        <tr>')
            #         self.wfile.write('          <td align="right">%d</td>' % (i))
            #         self.wfile.write('          <td align="right">%s</td>' % key)
            #         self.wfile.write('          <td align="left">%s</td>' % val)
            #         self.wfile.write('        </tr>')
            #     self.wfile.write('      </tbody>')
            #     self.wfile.write('    </table>')
            #
            # self.wfile.write('    <p><a href="%s">Back</a></p>' % (back))
            # self.wfile.write('  </body>')
            # self.wfile.write('</html>')

    return QLARqstHandler


def err(msg):
    '''
    Report an error message and exit.
    '''
    print('ERROR: %s' % (msg))
    sys.exit(1)


def getopts():
    '''
    Get the command line options.
    '''

    # Get the help from the module documentation.
    this = os.path.basename(sys.argv[0])
    description = ('description:%s' % '\n  '.join(__doc__.split('\n')))
    epilog = ' '
    rawd = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=rawd,
                                     description=description,
                                     epilog=epilog)

    parser.add_argument('-H', '--host',
                        action='store',
                        type=str,
                        default='localhost',
                        help='hostname, default=%(default)s')

    parser.add_argument('-l', '--level',
                        action='store',
                        type=str,
                        default='info',
                        choices=['notset', 'debug', 'info', 'warning', 'error', 'critical',],
                        help='define the logging level, the default is %(default)s')

    parser.add_argument('--no-dirlist',
                        action='store_true',
                        help='disable directory listings')

    parser.add_argument('-p', '--port',
                        action='store',
                        type=int,
                        default=8080,
                        help='port, default=%(default)s')

    parser.add_argument('-r', '--rootdir',
                        action='store',
                        type=str,
                        default=os.path.abspath('.'),
                        help='web directory root that contains the HTML/CSS/JS files %(default)s')

    parser.add_argument('-v', '--verbose',
                        action='count',
                        help='level of verbosity')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s - v' + VERSION)

    opts = parser.parse_args()
    opts.rootdir = os.path.abspath(opts.rootdir)
    if not os.path.isdir(opts.rootdir):
        err('Root directory does not exist: ' + opts.rootdir)
    if opts.port < 1 or opts.port > 65535:
        err('Port is out of range [1..65535]: %d' % (opts.port))
    return opts


def httpd(opts):
    '''
    HTTP server
    '''
    RequestHandlerClass = make_request_handler_class(opts)
    server = BaseHTTPServer.HTTPServer((opts.host, opts.port), RequestHandlerClass)
    logging.info('Server starting %s:%s (level=%s)' % (opts.host, opts.port, opts.level))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    logging.info('Server stopping %s:%s' % (opts.host, opts.port))


def get_logging_level(opts):
    '''
    Get the logging levels specified on the command line.
    The level can only be set once.
    '''
    if opts.level == 'notset':
        return logging.NOTSET
    elif opts.level == 'debug':
        return logging.DEBUG
    elif opts.level == 'info':
        return logging.INFO
    elif opts.level == 'warning':
        return logging.WARNING
    elif opts.level == 'error':
        return logging.ERROR
    elif opts.level == 'critical':
        return logging.CRITICAL


def main():
    ''' main entry '''
    opts = getopts()
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=get_logging_level(opts))
    httpd(opts)


if __name__ == '__main__':
    main()  # this allows library functionality
