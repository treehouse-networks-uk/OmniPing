
import os
import sys
import json
import cherrypy
from OmniPingServices import OmniPingService


class OmniPingPage():
    '''
    simply servers up the HTML Page - Not dynamic
    '''
    def __init__(self, path):
        self.path = path

    @cherrypy.expose
    def index(self):
        return open(os.path.join(self.path, 'pages/index.html'))


def json_error(status, message, traceback, version):
    '''
    New error function to overwrite the html Error page
    replacing it with JSON so the JS Client handles it
    '''
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({
            'status': status,
            'message': message
            })


if __name__ == '__main__':

    # Allow non default port numbers
    port = 8080
    if len(sys.argv) == 2:
        if sys.argv[1].isdigit():
            port = int(sys.argv[1])
        else:
            print(f'Bad Port {port} Number Exiting')
            sys.exit(1)

    # Update Cherrpy Config
    cwd = os.getcwd()
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': port,
        'log.screen': True,
        'log.access_file': f'{cwd}/logs/omniPing.log',
        'log.error_file': f'{cwd}/logs/omniPing.log',
        })

    conf = {
      '/': {
        'request.show_tracebacks': False,
        'tools.staticdir.root': os.path.abspath(cwd),
        'tools.encode.on': True,
        'tools.encode.encoding: ': 'utf-8',
      },
      '/omniping': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'request.show_tracebacks': False,
        'error_page.default': json_error,
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [('Content-Type', 'application/json')],
      },
      '/static': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': './public'
      }
    }

    # set the Version number and start the page and application
    version = '0.12'
    op = OmniPingPage(path=cwd)
    op.omniping = OmniPingService(version=version, path=cwd)
    cherrypy.quickstart(op, '/', conf)
