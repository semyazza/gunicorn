# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

from optparse import make_option
import sys
import os

 
import django
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import translation
from django.core.servers.basehttp import AdminMediaHandler, WSGIServerException
from django.core.handlers.wsgi import WSGIHandler
 
from gunicorn.arbiter import Arbiter
from gunicorn.main import daemonize, UMASK, set_owner_process
from gunicorn.util import parse_address
 
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
        make_option('-w', '--workers', dest='workers', default='1',
            help='Specifies the number of worker processes to use.'),
        make_option('--pid', dest='pidfile', default='',
            help='set the background PID file'),
        make_option( '--daemon', dest='daemon', action="store_true",
            help='Run daemonized in the background.'),
        make_option('--umask', dest='umask', type='int',
            help="Define umask of daemon process"),
        make_option('-u', '--user', dest="user", 
            help="Change worker user"),
        make_option('-g', '--group', dest="group", 
            help="Change worker group"),
    )
    help = "Starts a fully-functional Web server using gunicorn."
    args = '[optional port number, or ipaddr:port or unix:/path/to/sockfile]'
 
    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False
 
    def handle(self, addrport='', *args, **options):
        if args:
            raise CommandError('Usage is runserver %s' % self.args)
            
        bind = addrport or '127.0.0.1'
        addr = parse_address(bind)

        admin_media_path = options.get('admin_media_path', '')
        workers = int(options.get('workers', '1'))
        daemon = options.get('daemon')
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
        pidfile = options.get('pidfile', None)
        umask = options.get('umask', UMASK)

        print "Validating models..."
        self.validate(display_num_errors=True)
        print "\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE)
        
        if isinstance(addr, basestring):
            print "Development server is running at unix:/%s" % addr
        else:
            print "Development server is running at http://%s:%s/" % addr
        print "Quit the server with %s." % quit_command
 
        # django.core.management.base forces the locale to en-us.
        translation.activate(settings.LANGUAGE_CODE)
 
        try:
            handler = AdminMediaHandler(WSGIHandler(), admin_media_path)
            arbiter = Arbiter(addr, workers, handler,
                pidfile=pidfile)
            if daemon:
                daemonize(umask)
            else:
                os.setpgrp()
            set_owner_process(options.get("user"), options.get("group"))
            arbiter.run()
        except WSGIServerException, e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                13: "You don't have permission to access that port.",
                98: "That port is already in use.",
                99: "That IP address can't be assigned-to.",
            }
            try:
                error_text = ERRORS[e.args[0].args[0]]
            except (AttributeError, KeyError):
                error_text = str(e)
            sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
            sys.exit(1)