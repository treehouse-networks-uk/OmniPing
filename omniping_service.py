'''
define the API used to interogate
the omniping probes
'''
import cherrypy
from omniping_setup import OmniPingSetUp
from omniping_test_eng import OmniPingTestEng
from omniping_page_init import OmniPingPageInit


class OmniPingService():
    '''
    This is the main OmniPing class that directs requests
    to the appropriate aggregated classes
    '''

    def __init__(self, version, path):
        '''
        build the Classes required to handle each rquest
        '''
        cherrypy.log(f'[II] Starting OmniPing Version {version}')
        self.setup = OmniPingSetUp(path=path)
        self.test_engine = OmniPingTestEng(self.setup)
        self.page_init = OmniPingPageInit(
                version=version,
                setup=self.setup,
                test_engine=self.test_engine,
                )

    def _cp_dispatch(self, vpath):
        '''
        this method redirects requests to the configured classes
        '''
        if vpath[0] in ['version', 'page_init']:
            return self.page_init
        if vpath[0] in ['tests', 'setup']:
            return self.setup
        if vpath[0] in ['run', 'engine']:
            return self.test_engine
        return self
