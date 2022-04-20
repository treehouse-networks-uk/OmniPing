'''
Manages the test engine, i.e. get reports and starts and stops the background process
'''
from datetime import datetime
import time

import cherrypy
from cherrypy.process.plugins import BackgroundTask

from omniping_tester import OmniPingTester


class OmniPingTestEng():
    '''
    This handles incoming requests to start/stop/reset polling
    As well as retuning the latest report
    '''

    exposed = True

    content = [
        '''When it comes to results if it says "Good" with a tick then obviously,
        things are good. If you see a cross and a row turns red then the status
        should explain what has happened. If you see "Incomplete" then the report
        has been requested whilst a test has not completed.''',
        '''The durations of the tests can vary; a failed ping takes long than a
        successful one. If you have any doubts then stopping polling should allow
        any outstanding tests to complete. If you find too many incomplete tasks
        you could try and reduce the interval between tests. Or try running less
        tests if possible.''',
        '''The Client Auto-refresh runs every 3 Seconds, so if you are polling
        devices every second you are more likely to ask for a report when some
        tests have not completed.''',
        '''When Running HTTP and HTTPS tests it is not obvious how best to treat
        any given HTTP error code, for example a 401 or 403 might be expected and
        hence be a good result showing the server is available. As such any HTTP
        response code is not considered a failure and subsequently Not flagged as
        a failure. However, the status will be highlighted yellow if it isn't good.
        Just so it stands out. Hope that makes sense.'''
    ]

    def __init__(self, setup):
        self.setup = setup
        self.running = False
        self.bgtask = False
        self.tester = False
        self.report = self.make_initial_report()

    @cherrypy.tools.json_out()
    def GET(self):
        '''
        Handle Get Requests for the Report page
        '''
        report = self.make_jsonable_report()
        count = report.get('count', 'Error')
        report['message'] = f'Retrieved report ({count})'
        report['running'] = self.running
        report['content'] = self.content
        return report

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        '''
        Handle POST Requests from the Report page.
         - start stop and reset the test engine
        '''
        action = False
        valid_actions = ['start', 'stop', 'reset', 'restart_cp', 'clear']

        action = cherrypy.request.json.get('action', 'no action').lower()

        if action not in valid_actions:
            mess = 'Invalid action requested'
            cherrypy.log(f'[EE] {mess}')
            raise cherrypy.HTTPError(400, f'{mess}')

        update = 'No change'
        if action == 'start' and not self.running:
            if self.setup.pending_changes:
                self.report = self.make_initial_report()
                self.setup.pending_changes = False
            if len(self.report['tests']) != 1:
                self.start()
                update = f'Started Polling ({self.setup.config["interval"]} secs)'
            else:
                update = 'No Tests: Not starting'
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
                time.sleep(self.setup.config['interval'])
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

    def testerCall(self):
        '''
        the function refrenced by the CherryPy background task to update the report
        '''
        self.report = self.tester.run_once(self.report)
        cherrypy.log(f'[II] Poll Count: {self.report["count"]} - Time {self.report["duration"]}')

    def start(self):
        '''
        Starts Polling by initialising the CherryPy background task and the
        tester Class and
        '''
        self.tester = OmniPingTester(interval=self.setup.config['interval'])
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
        def make_test_dictionary(test, pos):
            test_dict = {}
            test_dict['host'] = test['host']
            test_dict['desc'] = test['desc']
            test_dict['test'] = test['test'].upper()
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
        for test in self.setup.config['tests']:
            if test['active']:
                report['tests'].append(make_test_dictionary(test, pos))
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
