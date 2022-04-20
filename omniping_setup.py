'''
Controls and manages the Configuration of Omniping
'''
import os
import re
import json

import cherrypy


class OmniPingSetUp():
    '''
    Handles updates and requests for the setup of OmniPing Including:
    - Saving to local text file
    - Validation and quality control
    '''

    exposed = True
    default_config = {}
    default_config['tests'] = [{
            "active": False,
            "desc": "Useful Description",
            "host": "192.168.1.205",
            "test": "PING"
        },
        {
            "active": False,
            "desc": "Useful Description",
            "host": "10.255.255.6",
            "test": "HTTP"
        }]
    default_config['heading'] = 'OmniPing'
    default_config['colour'] = '#FFFFFF'
    default_config['interval'] = 4.0

    colour_re = r'^\s*(#[0-9a-f]{6})\s*$'
    desc_re = r'^\s?([0-9a-z\-\_\'\. #]+)\s?$'
    host_re = r'^\s?([0-9a-z\.:\/]+)\s?$'
    host_http_re = r'^\s?([0-9a-z\.:\/]+)\s?$'
    host_ping_re = r'^\s?([0-9a-z\.]+)\s?$'

    content = [
        '''Use this page to set up the Omniping Probe. Colour sets the colour of
        the banner at the top of the page. The heading is displayed in the curly
        braces at the top of the page. These are simply to make the page more
        recognisable if you have multiple instances running at different points in
        a network. The colour field uses the standard hexadecimal RGB colour used
        in web design.''',
        '''The polling interval is simply the frequency with which the tests are run.
        Whilst this can be set to 1 seconds at its lowest it is better to set the
        interval to a reasonable value between 2 and 5. This has the additional benefit
        of utilising additional source port numbers which may help pick up issues where
        load sharing over multiple paths based on source and destination socket hashes.
        The tests are set up using the following format:''',
        '''<span style="font-style: italic;">&nbsp;&nbsp;&nbsp;&nbsp;
        host : description : type</span> <br/>-or-<br/>
           <span style="font-style: italic;">&nbsp;&nbsp;&nbsp;&nbsp;
        host ; description ; type </span>''',
        '''fields can be delimited using ":" or ";" but once saved a ";" is used to
        improve clarity when a server port is specified ''',
        '''A "#" can be used to comment out an entry which will be preserved but not
        tested ie:''',
        '''<span style="font-style: italic;">&nbsp;&nbsp;&nbsp;&nbsp;
        # host : description : type </span>''',
        '''The "host" field can be an IP address or domain name and a specific port can be set using
        <span style="font-style: italic;">host:port </span> syntax
        (NOTE: appropriate DNS resolution needs to be considered when running within the container).
        Acceptable test types are PING | HTTP | HTTPS (NOTE: some additional CPU
        overhead is anticipated for HTTPS tests)'''
    ]

    def __init__(self, path):
        self.host_file = os.path.join(path, 'hosts.json')
        self.get_setup_from_file()
        self.pending_changes = False

    @cherrypy.tools.json_out()
    def GET(self):
        '''
        Handle Get Requests for the Setup page
        '''
        self.get_setup_from_file()
        return self.make_response()

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        '''
        Handle POST Requests from the Setup page.
         - save and validate setup fields
        '''
        updated_config = {}

        if cherrypy.request.json.get('colour', False):
            colour_match = re.match(
                self.colour_re,
                cherrypy.request.json['colour'],
                re.IGNORECASE
                )
            if colour_match is None:
                mess = f'Invalid colour - {cherrypy.request.json["colour"]}'
                cherrypy.log(f'[EE] {mess}')
                raise cherrypy.HTTPError(400, f'{mess}')
            updated_config['colour'] = colour_match.group(1).upper()

        if cherrypy.request.json.get('interval', False):
            try:
                updated_config['interval'] = float(cherrypy.request.json['interval'])
            except ValueError:
                mess = f'Interval not valid {cherrypy.request.json["interval"]}'
                raise cherrypy.HTTPError(400, f'{mess}')

            if updated_config['interval'] < 1:
                mess = "Interval under 1 second"
                updated_config['interval'] = False
            elif updated_config['interval'] > 1000:
                updated_config['interval'] = False
                mess = "Interval over 1000 seconds"

            if updated_config['interval'] is False:
                cherrypy.log(f'[EE] {mess}')
                raise cherrypy.HTTPError(400, f'{mess}')

        if cherrypy.request.json.get('heading', False):
            heading_match = re.match(self.desc_re, cherrypy.request.json['heading'], re.IGNORECASE)
            if heading_match is None:
                mess = f'Invalid Heading - "{updated_config["heading"]}"'
                cherrypy.log(f'[EE] {mess}')
                raise cherrypy.HTTPError(400, f'{mess}')

            updated_config['heading'] = heading_match.group(1)

        new_tests = self.check_tests(cherrypy.request.json.get('tests', False))
        message = self.update(updated_config, new_tests)
        self.save_setup_to_file()
        response = self.make_response()
        response['message'] = message
        return response

    def make_response(self):
        '''
        prepare a standaridised response
        message is overwritten in POST method
        '''
        response = {}
        response['tests'] = self.config['tests']
        response['colour'] = self.config['colour']
        response['heading'] = self.config['heading']
        response['interval'] = self.config['interval']
        response['content'] = self.content
        response['message'] = 'Set Up info retrieved'
        return response

    def get_setup_from_file(self):
        '''
        opens up the hosts.txt file and extracts the information required to operate
        if available
        '''
        self.config = self.default_config.copy()
        try:
            with open(self.host_file, 'r') as tests_file:
                self.config = json.load(tests_file)

        except (PermissionError, FileNotFoundError):
            cherrypy.log('[II] Can\'t find or read configuration file Using defaults !!')
        except json.decoder.JSONDecodeError:
            cherrypy.log('[II] Empty or Invalid configuration file Using defaults !!')

    def save_setup_to_file(self):
        '''
        Updates the hosts.json file with current configuration
        updated to use json
        '''
        try:
            with open(self.host_file, 'w') as tests_file:
                json.dump(
                        self.config,
                        tests_file,
                        sort_keys=True,
                        indent=4,
                        ensure_ascii=False
                        )
                cherrypy.log('[II] OmniPing Configuration Saved')

        except (PermissionError, FileNotFoundError):
            cherrypy.log('[EE] Can\'t save Omniping Config !!')

    def is_valid_test(self, test):
        '''
        Validate parameters of each test dictionary
        '''
        valid_keys = ['host', 'desc', 'test', 'active']
        for key in valid_keys:
            if key not in test.keys():
                return False

        if test.get('test', '').upper() not in ['PING', 'HTTP', 'HTTPS']:
            return False

        host_match = re.match(self.host_http_re, test.get('host', '%'), re.IGNORECASE)

        if test.get('test', '').upper() in ['PING']:
            host_match = re.match(self.host_ping_re, test.get('host', '%'), re.IGNORECASE)

        if not host_match:
            return False

        desc_match = re.match(self.desc_re, test.get('desc', '%'), re.IGNORECASE)
        if not desc_match:
            return False

        if not isinstance(test['active'], bool):
            return False
        return True

    def check_tests(self, tests):
        '''
        orchestrate checking of each test
        '''
        if tests:
            new_tests = []
            for test in tests:
                if self.is_valid_test(test):
                    new_tests.append(test)
                else:
                    test_str = f'{test["host"]} ; {test["desc"]} ; {test["test"]}'
                    mess = f'[EE] Invalid Test - {test_str}'
                    cherrypy.log(mess)
                    raise cherrypy.HTTPError(400, f'{mess}')
            self.pending_changes = True
            return new_tests
        return self.config['tests']

    def has_changed(self, new_tests):
        '''
        checks if test configurations have changed
        '''
        if len(new_tests) != len(self.config['tests']):
            return True

        for pos, test in enumerate(new_tests):
            for key in test.keys():
                if test[key] != self.config['tests'][pos][key]:
                    return True
        return False

    def update(self, updated_config, new_tests):
        '''
        orchestrate configuration update process
        '''
        mess_list = []
        mess_prepend = ''
        if self.has_changed(new_tests):
            self.config['tests'] = new_tests
            mess_list.append('Tests')

        valid_keys = ['heading', 'colour', 'interval']
        for key in valid_keys:
            if updated_config.get(key, '') != self.config[key]:
                mess_list.append(key.capitalize())
                self.config[key] = updated_config.get(key, self.config[key])

        if not self.config['tests']:
            mess_prepend = ("- 0 tests Defined !!")

        if len(mess_list) > 1:
            message = f'Updated: {", ".join(mess_list[0:-1])} & {mess_list[-1]}{mess_prepend}'
        elif len(mess_list) == 1:
            message = f'Updated: {mess_list[0]} {mess_prepend}'
        else:
            message = f'No changes made {mess_prepend}'

        return message
