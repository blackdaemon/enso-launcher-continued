# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:
from __future__ import with_statement
import Queue
import cgi
import logging
import os
import socket
import threading
import urllib
import urllib2
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import enso.config
from enso.contrib.scriptotron import cmdretriever, tracker
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.messages import displayMessage as display_xml_message


def serve_install_js(request):
    jspath = os.path.join(os.path.split(__file__)[0], "webui", "install.js")
    with open(jspath, "r") as fp:
        js = fp.read()
    request.send_response(200)
    request.send_header("Content-Type", "text/javascript")
    request.end_headers()
    request.wfile.write(js)


def serve_favicon(request):
    webdir = os.path.realpath(
        os.path.join(os.path.split(__file__)[0], "..", "web"))
    icopath = os.path.join(webdir, "favicon.ico")
    with open(icopath, "rb") as fp:
        ico = fp.read()
    request.send_response(200)
    request.send_header("Content-Type", "image/x-icon")
    request.end_headers()
    request.wfile.write(ico)


def serve_static_content(request, file_name):
    print "serving", file_name
    _, ext = os.path.splitext(file_name)
    if ext not in (".css", ".txt", ".gif", ".jpg", ".png"):
        request.send_response(404)
        request.end_headers()
        request.wfile.write("404 Not Found")
        return

    webdir = os.path.realpath(
        os.path.join(os.path.split(__file__)[0], "..", "web", "static"))
    filepath = os.path.join(webdir, file_name)
    if not os.path.isfile(filepath):
        request.send_response(404)
        request.end_headers()
        request.wfile.write("404 Not Found")
        return

    with open(filepath, "rb") as fd:
        content = fd.read()

    request.send_response(200)
    if ext == ".css":
        request.send_header("Content-Type", "text/css")
    elif ext == ".txt":
        request.send_header("Content-Type", "text/plain")
    elif ext == ".gif":
        request.send_header("Content-Type", "image/gif")
    elif ext == ".jpg":
        request.send_header("Content-Type", "image/jpg")
    elif ext == ".png":
        request.send_header("Content-Type", "image/png")
    request.end_headers()
    request.wfile.write(content)


def serve_js(request, file_name):
    print "serving", file_name
    _, ext = os.path.splitext(file_name)
    if ext not in (".js"):
        request.send_response(404)
        request.end_headers()
        request.wfile.write("404 Not Found")
        return

    webdir = os.path.realpath(
        os.path.join(os.path.split(__file__)[0], "..", "web", "js"))
    filepath = os.path.join(webdir, file_name)
    if not os.path.isfile(filepath):
        request.send_response(404)
        request.end_headers()
        request.wfile.write("404 Not Found")
        return

    with open(filepath, "r") as fd:
        content = fd.read()

    request.send_response(200)
    if ext == ".js":
        request.send_header("Content-Type", "text/javascript")
    request.end_headers()
    request.wfile.write(content)


class myhandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server, queue):
        self.queue = queue
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        webdir = os.path.realpath(
            os.path.join(os.path.split(__file__)[0], "..", "web"))
        if self.path == "/install.js":
            serve_install_js(self)
        elif self.path.startswith("/help/command/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write("COMMAND HELP")
        elif self.path == "/favicon.ico":
            serve_favicon(self)
        elif self.path.startswith("/static/"):
            file_name = self.path[len("/static/"):]
            serve_static_content(self, file_name)
        elif self.path.startswith("/help/"):
            if self.path == "/help" or self.path == "/help/":
                with open(os.path.join(webdir, "help", "index.html"), "r") as htmlfile:
                    html = htmlfile.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write("404 Not Found")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("404 Not Found")

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })
        action = form.getfirst("action", None)
        if action == "install_command":
            url = form.getfirst("url", None)
            if url:
                self.queue.put(url)
                self.send_response(200)
                self.end_headers()
                self.wfile.write("""OK""")
            else:
                self.send_response(401)
                self.end_headers()
                self.wfile.write("""Bad Request""")

        else:
            self.send_response(401)
            self.end_headers()
            self.wfile.write("""Bad Request""")


class myhttpd(HTTPServer):

    def __init__(self, server_address, RequestHandlerClass, queue):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.queue = queue

    def server_bind(self):
        HTTPServer.server_bind(self)
        self.socket.settimeout(1)
        self.run = True

    def get_request(self):
        while self.run:
            try:
                sock, addr = self.socket.accept()
                sock.settimeout(None)
                return (sock, addr)
            except socket.timeout:
                if not self.run:
                    raise socket.error

    def finish_request(self, request, client_address):
        # overridden from SocketServer.TCPServer
        logging.info("Finish request called")
        self.RequestHandlerClass(request, client_address, self, self.queue)

    def stop(self):
        self.run = False

    def serve_forever(self):
        """ Override serve_forever to handle shutdown. """
        while self.run:
            self.handle_request()


class Httpd(threading.Thread):

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.server = None

    def run(self):
        self.server = myhttpd(('localhost', 31750), myhandler, self.queue)
        self.server.serve_forever()

    def stop(self):
        if self.server:
            logging.info("Stopping the WebUI server")
            self.server.stop()
            self.server = None


@safetyNetted
def get_commands_from_object(text, filename):
    allGlobals = {}
    code = compile(text, filename, "exec")
    exec code in allGlobals
    return cmdretriever.getCommandsFromObjects(allGlobals)


def urlopen(url, timeout=None):
    fp = None
    if timeout is not None:
        try:
            # Use urllib2 with timeout on Python >= 2.6
            fp = urllib2.urlopen(url, timeout=timeout)
        except (TypeError, ImportError):
            fp = urllib.urlopen(url)
    else:
        fp = urllib.urlopen(url)
    return fp


def install_command_from_url(command_url):
    try:
        resp = urlopen(command_url, timeout=15.0)
    except Exception as e:
        logging.error(e)
        display_xml_message("<p>Couldn't install that command</p>")
        return

    if "Content-Disposition" in resp.info():
        # If command file is provided as an attachment, parse the correct filename
        # from the headers
        command_file_name = resp.info()["Content-Disposition"].split(
            "filename=")[1].strip("\"'")
    elif resp.url != command_url:
        # If there was redirect, get the filename from the redirected URL
        command_file_name = urllib.unquote(resp.url.split("/")[-1])
    else:
        # Otherwise get the filename from the current URL
        command_file_name = urllib.unquote(command_url.split("/")[-1])

    if not command_file_name.endswith(".py"):
        display_xml_message(
            u"<p>Not a valid command <command>%s</command></p>"
            % command_file_name)
        return

    try:
        text = resp.read()
    except socket.timeout:
        display_xml_message(
            u"<p>Timeout occurred while downloading the command. Please try again.</p>")
        return
    finally:
        resp.close()

    # Normalize newlines to "\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")
    if len(lines) < 3:
        display_xml_message(u"<p>There was no command to install!</p>")
        return
    while lines[0].strip() == "":
        lines.pop(0)

    cmd_folder = tracker.getScriptsFolderName()
    command_file_path = os.path.expanduser(
        os.path.join(cmd_folder, command_file_name))
    short_name = os.path.splitext(command_file_name)[0]
    if os.path.exists(command_file_path):
        display_xml_message(
            u"<p>You already have a command named <command>%s</command></p>"
            % short_name)
        return

    commands = get_commands_from_object(text, command_file_path)
    if commands:
        installed_commands = [x["cmdName"] for x in commands]
        if len(installed_commands) == 1:
            install_message = (u"<command>%s</command> is now a command"
                               % installed_commands[0])
        elif len(installed_commands) > 1:
            install_message = (u"<command>%s</command> are now commands"
                               % u"</command>, <command>".join(installed_commands))
        display_xml_message(u"<p>%s</p>" % install_message)
        # Use binary mode for writing so endlines are not converted to "\r\n"
        # on win32
        with open(command_file_path, "wb") as fp:
            fp.write(text)
    else:
        display_xml_message(u"<p>No commands to install</p>")


commandq = Queue.Queue()
_poll_ms_accumulator = 0


def pollqueue(ms):
    global _poll_ms_accumulator
    _poll_ms_accumulator += ms
    if _poll_ms_accumulator < 500:
        return
    _poll_ms_accumulator = 0

    try:
        command_url = commandq.get(False, 0)
    except Queue.Empty:
        return

    # FIXME: here we should check to see if it's OK to install this command!
    install_command_from_url(command_url)


def start(eventManager):
    logging.info("Starting WebUI")
    httpd_server = Httpd(commandq)
    httpd_server.setDaemon(True)
    httpd_server.start()
    eventManager.registerResponder(pollqueue, "timer")
    return httpd_server
