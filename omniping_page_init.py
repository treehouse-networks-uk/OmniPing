'''
control respnses to http://<omniping>/page_init
version, current config and test engine status
'''
import cherrypy


class OmniPingPageInit():
    '''
    Version Class returns intial Query information collated from
    the SetUp and Test_engine Classes.
    '''

    exposed = True

    def __init__(self, version='', setup=False, test_engine=False):
        self.version = version
        self.config = setup.config
        self.test_engine = test_engine

    @cherrypy.tools.json_out()
    def GET(self):
        '''
        Handle Get Requests - thats all this class does TBF
        '''
        mess = ''
        if self.test_engine.running:
            mess = ' and Polling'
        response = {'version': self.version,
                    'heading': self.config['heading'],
                    'colour': self.config['colour'],
                    'running': self.test_engine.running,
                    'message': f'OmniPing Alive {mess}'
                    }
        return response
