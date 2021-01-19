
from datetime import datetime
import os
import re

import cherrypy
from cherrypy.process.plugins import BackgroundTask
from OmniPingTestClass import OmniPingTester
import time

import pprint


class OmniPingVersion():
    '''
    Version Class returns intial Query information collated from
    the SetUp and Test_engine Classes.
    '''

    exposed = True

    def __init__(self, version='', setup=False, test_engine=False):
        self.version = version
        self.setup = setup
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
                    'heading': self.setup.heading,
                    'colour': self.setup.colour,
                    'running': self.test_engine.running,
                    'message': f'OmniPing Alive {mess}'
                    }
        return response


class OmniPingSetUp():
    '''
    Handles updates and requests for the setup of OmniPing Including:
    - Saving to local text file
    - Validation and quality control
    '''

    exposed = True
    default_tests = [(
            '192.168.1.1',
            'Useful Description',
            'ping',
            False
        ), (
            '192.168.1.1',
            'Useful Description',
            'http',
            False
        )]
    default_heading = 'OmniPing'
    default_colour = '#FFFFFF'
    default_interval = 4.0
    desc_re = r'^[0-9a-z\-\_\' ]+$'
    colour_re = r'^#[0-9a-f]{6}$'
    host_re = r'^\S+$'

    content = [
        '''Use the above page to set up the Omniping Server.
        Colour sets the colour of the banner at the top of the page.
        This is simply to make the page more recogniable if you have multiple
        instances running. It uses the standard hexidecimal RGB colour used in web design.
        The heading is also a means to describe the instance in the event that there is more than
        one. The output is displayed in the curly braces at the top of the page.''',
        '''The polling interval is simply the frequency with which the tests are run.
        Whilst this can be set to 0.5 seconds at its lowest it is better to set the interval to
        a reasonable value such as 2. Increased traffic loading can be achieved by duplicating
        tests to increase load, granularity.
        The tests are set up using the following format:''',
        '''<span style="font-style: italic;">&nbsp;&nbsp;&nbsp;&nbsp;
        host : description : type</span> ''',
        '''A "#" can be used to comment out an entry which will be preserved but not tested ie: ''',
        '''<span style="font-style: italic;">&nbsp;&nbsp;&nbsp;&nbsp;
        # host : description : type </span>''',
        '''The "host" field can be an IP address or domain name (NOTE: appropriate DNS resolution
        needs to be considered when running within the container). Acceptable test types are
        PING | HTTP | HTTPS (NOTE: some additional CPU overhead is anticipated for HTTPS tests)'''
    ]

    def __init__(self, path):
        self.host_file = os.path.join(path, 'hosts.txt')
        self.tests = []
        self.heading = self.default_heading
        self.colour = self.default_colour
        self.interval = self.default_interval
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
        update_dict = {}

        update_dict['colour'] = cherrypy.request.json.get('colour', '').strip()
        if update_dict['colour']:
            if not re.search(self.colour_re, update_dict['colour'], re.IGNORECASE):
                mess = f'Invalid colour - {update_dict["colour"]}'
                cherrypy.log(f'[EE] {mess}')
                raise cherrypy.HTTPError(400, f'{mess}')

        update_dict['interval'] = cherrypy.request.json.get('interval', False)
        if update_dict['interval']:
            if isinstance(update_dict['interval'], int):
                update_dict['interval'] = float(update_dict['interval'])
            if isinstance(update_dict['interval'], str):
                try:
                    update_dict['interval'] = float(update_dict['interval'])
                except ValueError:
                    mess = f'Interval not valid {update_dict["interval"]}'
                    update_dict['interval'] = False

            if isinstance(update_dict['interval'], float):
                if update_dict['interval'] < 1:
                    mess = "Interval under 1 second"
                    update_dict['interval'] = False
                elif update_dict['interval'] > 500:
                    update_dict['interval'] = False
                    mess = "Interval over 500 seconds"

            if not update_dict['interval']:
                cherrypy.log(f'[EE] {mess}')
                raise cherrypy.HTTPError(400, f'{mess}')

        update_dict['heading'] = cherrypy.request.json.get('heading', '').strip()
        if update_dict['heading']:
            if not re.search(self.desc_re, update_dict['heading'], re.IGNORECASE):
                mess = f'Invalid Heading - "{update_dict["heading"]}"'
                cherrypy.log(f'[EE] {mess}')
                raise cherrypy.HTTPError(400, f'{mess}')

        new_tests = self.check_tests(cherrypy.request.json.get('tests', False))

        message = self.update(update_dict, new_tests)
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
        response['tests'] = self.tests
        response['colour'] = self.colour
        response['heading'] = self.heading
        response['interval'] = self.interval
        response['content'] = self.content
        response['message'] = 'Set Up info retrieved'
        return response

    def get_setup_from_file(self):
        '''
        opens up the hosts.txt file and extracts the information required to operate
        if available
        '''
        try:
            self.heading = self.default_heading
            self.colour = self.default_colour
            self.interval = self.default_interval

            server_line_re_4 = r'^>>\s*([a-z0-9_\-\s]+)\s*:\s*(#[0-9a-f]{6})\s*:\s*([0-9\.]{1,3})$'
            server_line_re_3 = r'^>>\s*([a-z0-9_\-\s]+)\s*:\s*(#[0-9a-f]+)$'
            server_line_re_2 = r'^>>\s*([a-z0-9_\-\s]+)\s*:\s*([0-9\.]{1,3})$'
            server_line_re_1 = r'^>>\s*([a-z0-9_\-\s]+)$'
            testhost_re = r"^(#*) *([a-z0-9_:/\-\.]+)\s*:\s*([a-z0-9\s']+)\s*:\s*(http|ping|https)$"

            with open(self.host_file, 'r') as tests_file:
                self.tests = []
                for line in tests_file.readlines():
                    server_line_match = re.match(server_line_re_4, line, re.IGNORECASE)
                    if server_line_match:
                        self.heading = server_line_match.group(1).strip()
                        self.colour = server_line_match.group(2)
                        self.interval = float(server_line_match.group(3))
                        continue
                    server_line_match = re.match(server_line_re_3, line, re.IGNORECASE)
                    if server_line_match:
                        self.heading = server_line_match.group(1).strip()
                        self.colour = server_line_match.group(2)
                        continue
                    server_line_match = re.match(server_line_re_2, line, re.IGNORECASE)
                    if server_line_match:
                        self.heading = server_line_match.group(1).strip()
                        self.interval = float(server_line_match.group(2))
                        continue
                    server_line_match = re.match(server_line_re_1, line, re.IGNORECASE)
                    if server_line_match:
                        self.heading = server_line_match.group(1).strip()
                        continue
                    testhost_match = re.match(testhost_re, line, re.IGNORECASE)
                    if testhost_match:
                        live = not testhost_match.group(1) == '#'
                        host = testhost_match.group(2)
                        desc = testhost_match.group(3).strip()
                        test = testhost_match.group(4).upper()
                        self.tests.append((host, desc, test, live))
            if not len(self.tests):
                self.tests = self.default_tests
        except FileNotFoundError:
            cherrypy.log('[II] Can\'t find tests_file !!')

    def save_setup_to_file(self):
        '''
        Updates the hosts.txt file and based on the current tests
        '''
        raw_file = self.make_raw_setup_info()
        with open(self.host_file, 'w') as tests_file:
            tests_file.write(raw_file)
            tests_file.flush()

    def make_raw_setup_info(self):

        raw_tests = f'>> {self.heading} : {self.colour} : {self.interval}\n'
        for test in self.tests:
            if test[3]:
                raw_tests += f'{test[0]} : {test[1]} : {test[2]}\n'
            else:
                raw_tests += f'# {test[0]} : {test[1]} : {test[2]}\n'
        return raw_tests

    def is_valid_test(self, test):
        if len(test) != 4:
            return False
        if not re.search(self.host_re, test[0].strip(), re.IGNORECASE):
            return False
        if not re.search(self.desc_re, test[1].strip(), re.IGNORECASE):
            print('here')
            return False
        if test[2].upper() not in ['PING', 'HTTP', 'HTTPS']:
            return False
        if not isinstance(test[3], bool):
            return False
        return True

    def check_tests(self, tests):
        new_tests = []
        if tests:
            for test in tests:
                if self.is_valid_test(test):
                    new_tests.append(test)
                else:
                    mess = f'[EE] Invalid Test - {test}'
                    cherrypy.log(mess)
                    raise cherrypy.HTTPError(400, f'{mess}')
        self.pending_changes = True
        return new_tests

    def update(self, update_dict, new_tests):
        mess_list = []
        if update_dict.get('heading', False):
            self.heading = update_dict['heading']
            mess_list.append('Heading')
        if update_dict.get('interval', False):
            self.interval = update_dict['interval']
            mess_list.append('Interval')
        if update_dict.get('colour', False):
            self.colour = update_dict['colour'].upper()
            mess_list.append('Colour')
        if new_tests:
            self.tests = new_tests
            test_count = len(new_tests)
            ess = ''
            if test_count != 1:
                ess = 's'
            mess_list.append(f'{test_count} Test{ess}')

        if len(mess_list) > 1:
            message = f'Updated: {", ".join(mess_list[0:-1])} & {mess_list[-1]}'
        elif len(mess_list) == 1:
            message = f'Updated: {mess_list[0]}'
        else:
            message = f'No changed made'
        return message


class OmniPingTestEng():
    '''
    This handles incoming requests to start/stop/reset polling
    As well as retuning the latest report
    '''

    exposed = True

    content = [
        '''When it comes to results if it says "Good" with a tick then obvisouly,
        things are good. If you see a cross and a row turns red then the status
        should explain what has happened. If you see "Incomplete" and the row is
        amber then the report has been requested whilst a test has not completed.
        The durations of the tests can vary; a failed ping takes long than a
        successful one. If you haveany doubts then stopping polling should allow
        any outstanding tests to complete.''',
        '''If you find too many incomplete tasks you could try and reduce the
        interval between tests. Or try running less tests if possible.
        the Client Auto refresh runs every 3 Seconds ''',
    ]

    def __init__(self, setup):
        self.setup = setup
        self.running = False
        self.bgtask = False
        self.tester = False
        self.report = self.make_initial_report()

    @cherrypy.tools.json_out()
    def GET(self):
        report = self.make_jsonable_report()
        count = report.get('count', 'Error')
        report['message'] = f'Retrieved report ({count})'
        report['running'] = self.running
        report['content'] = self.content
        return report

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        action = False
        valid_actions = ['start', 'stop', 'reset', 'restart_cp', 'clear']

        if cherrypy.request.json.get('action', False):
            action = cherrypy.request.json['action'].lower()

        if action in valid_actions:
            update = 'No change'
            if action == 'start' and not self.running:
                if self.setup.pending_changes:
                    self.report = self.make_initial_report()
                    self.setup.pending_changes = False
                self.start()
                update = f'Started Polling ({self.setup.interval} secs)'
            if action == 'stop' and self.running:
                self.stop()
                update = "Stopped Polling"
            if action == 'reset':
                update = "Report Cleared"
                if self.running:
                    self.stop()
                    update = "Report Cleared and Polling Stopped"
                self.report = self.make_initial_report()
            if action == 'clear':
                restart = False
                if self.running:
                    self.stop()
                    restart = True
                    time.sleep(self.setup.interval)
                self.report = self.make_initial_report()
                if restart:
                    self.start()
                update = "Report Counters Cleared"
            if action == 'restart_cp':
                self.stop()
                update = "Restarting CherryPy Server"
                cherrypy.engine.restart()

            cherrypy.log(f'[II] {update}')
            response = {}
            response['message'] = update
            response['polling'] = self.running
            return response

        mess = 'Invalid action requested'
        cherrypy.log(f'[EE] {mess}')
        raise cherrypy.HTTPError(400, f'{mess}')

    def testerCall(self):
        '''
        the function refrenced by the CherryPy background task to update the report
        '''
        self.report = self.tester.run_once(self.report)
        # pprint.pprint(new_report)
        # self.report = new_report
        cherrypy.log(f'[II] Poll Count: {self.report["count"]} - Time {self.report["duration"]}')

    def start(self):
        '''
        Starts Polling by initialising the CherryPy background task and the
        tester Class and
        '''
        self.tester = OmniPingTester(interval=self.setup.interval)
        actual_interval = self.tester.interval - self.tester.timeout
        self.bgtask = BackgroundTask(actual_interval, self.testerCall, bus=cherrypy.engine)
        self.bgtask.start()
        self.running = True

    def stop(self):
        '''
        Stops Polling by deleting the CherryPy background task
        and the tester. just to keep things clean (hopefully)
        '''
        if self.bgtask:
            self.bgtask.cancel()
        self.bgtask = False
        self.tester = False
        self.running = False

    def make_initial_report(self):
        '''
        Construct the report dictionary prior to tests running.
        '''
        def make_test_dictionary(host, desc, test_type, pos):
            test_dict = {}
            test_dict['host'] = host
            test_dict['desc'] = desc
            test_dict['test'] = test_type.upper()
            test_dict['good'] = False
            test_dict['last_stat'] = '--'
            test_dict['status'] = '--'
            test_dict['rtt'] = '--'
            test_dict['total'] = 0
            test_dict['total_successes'] = 0
            test_dict['success_percent'] = "0.00 %"
            test_dict['last_good'] = '--'
            test_dict['last_bad'] = '--'
            test_dict['last_bad_status'] = '--'
            test_dict['pos'] = pos
            return test_dict

        report = {}
        report['started'] = False
        report['time'] = False
        report['count'] = 0
        report['duration'] = 0
        report['tests'] = [False]
        pos = 0
        for host, desc, test_type, live in self.setup.tests:
            if live:
                report['tests'].append(make_test_dictionary(host, desc, test_type, pos))
                pos += 1
        return report

    def make_jsonable_report(self):
        '''
        make sure all elements of the report dictionary are JSON serializable.
        prior to putting in the response.
        Also does some formating/ordering
        '''
        response = self.report.copy()
        if response['duration'] != 0:
            response['duration'] = '{}'.format(str(response['duration'])[:-4])
        if isinstance(response['started'], datetime):
            response['started'] = response['started'].strftime('%a %d %b %Y %I:%M:%S %p')
        if isinstance(response['time'], datetime):
            response['time'] = response['time'].strftime('%a %d %b %Y %I:%M:%S %p')

        new_tests = [{}] * (len(response['tests']) - 1)
        for test in response['tests']:
            if not test:
                continue
            new_tests[test['pos']] = test
        response['tests'] = new_tests
        return response


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
        self.version = OmniPingVersion(
                version=version,
                setup=self.setup,
                test_engine=self.test_engine,
                )

    def _cp_dispatch(self, vpath):
        '''
        this method redirects requests to the configured classes
        '''
        if vpath[0] == 'version':
            return self.version
        if vpath[0] in ['tests', 'setup']:
            return self.setup
        if vpath[0] in ['run', 'engine']:
            return self.test_engine
        return self
