'''
Class to manage OmniPing tests and generate a report
'''
from datetime import datetime
import time
import socket
import re
import asyncio
import http3
import cherrypy


class OmniPingTester():
    '''
    Task to manage asynchronous test calls
    '''

    # Diction ary to give meaningful responses when testing HTTP(S)
    stat_dict = {}
    stat_dict[200] = 'Good (200)'
    stat_dict[201] = 'Good (201)'
    stat_dict[202] = 'Good (202)'
    stat_dict[300] = 'Redir (300)'
    stat_dict[301] = 'Redir (301)'
    stat_dict[302] = 'Redir (302)'
    stat_dict[400] = 'Bad (400)'
    stat_dict[401] = 'Not Auth (401)'
    stat_dict[403] = 'Forbidden (403)'
    stat_dict[404] = 'Not Found (404)'

    def __init__(self, interval=2):
        '''
        time out and Interval values are calculated on instantiation
        based on desired interval. The interval the CherryPy
        Background process uses is calculated by refrenceing these
        '''
        self.timeout = 2.0
        self.interval = interval
        if self.interval <= 4.0:
            self.timeout = self.interval / 2
        self.loop = False

    def run_once(self, input_report):
        '''
        This Orchestrates the testing based on the passin report
        It creates a new asyncio event loop each time as this
        suffered less errors
        '''

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        if not input_report['started']:
            input_report['started'] = datetime.now()

        input_report['count'] += 1
        self.loop.create_task(self.dummy_fail())
        for test in input_report['tests']:
            if not test:
                continue
            if test['test'] in ['ICMP', 'PING']:
                test_func = self.ping_tester
            elif test['test'] in ['HTTP', 'HTTPS']:
                test_func = self.http_tester
            self.loop.create_task(test_func(test))

        try:
            group = asyncio.gather(*asyncio.Task.all_tasks(loop=self.loop))
            results = self.loop.run_until_complete(group)
            input_report['tests'] = results
            input_report['time'] = datetime.now()
            input_report['duration'] = input_report['time'] - input_report['started']
            return input_report
        except OSError as e:
            cherrypy.log(f'[EE] {e}')

    async def dummy_fail(self):
        '''
        This is here to simulate a timed out test in order to
        allow for consistent intervals between good (quick) tests and
        failed (timedout) tests
        '''
        await asyncio.sleep(self.timeout - 0.12)
        return False

    async def ping_tester(self, test_info):
        '''
        Method to test using PING
        uses Asyncio's subprocesses
        '''
        try:
            test_info['rtt'] = '--'
            test_info['good'] = False
            test_info['last_stat'] = test_info['status']
            test_info['status'] = 'Incomplete'
            proc = await asyncio.create_subprocess_shell(
                f'ping -c 1 -W {self.timeout} -n {test_info["host"]}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc.communicate()
            test_info['total'] += 1
            if proc.returncode == 0:
                test_info['total_successes'] += 1
                test_info['last_good'] = datetime.now().strftime('%a %H:%M:%S')
                test_info['good'] = True
                test_info['status'] = 'Good'
                rtt_line_re = r'[64]+\sbytes\sfrom\s[0-9\.:a-f]+:\sicmp_seq=1\sttl=[0-9]+\s' \
                              r'time=([0-9\.]+)\sms'
                if stdout:
                    for line in stdout.decode().split('\n'):
                        match = re.match(rtt_line_re, line)
                        if match:
                            test_info['rtt'] = f'{match.group(1)} ms'
                            break
            else:
                test_info['status'] = 'Time Out'
                test_info['last_bad'] = datetime.now().strftime('%a %H:%M:%S')
                test_info['good'] = False
                unreach_line_re = r'^From\s[0-9\.:a-f]+\sicmp_seq=1\s([0-9a-zA-Z\ ]+)$'
                if stdout:
                    for line in stdout.decode().split('\n'):
                        match = re.match(unreach_line_re, line)
                        if match:
                            test_info['status'] = 'Unreachable'
                            break
                test_info['last_bad_status'] = test_info['status']
        except asyncio.CancelledError:
            print('Cancelled !!')
        test_info['success_percent'] = sucPer(
                                            test_info['total'],
                                            test_info['total_successes']
                                            )
        return test_info

    async def http_tester(self, test_info):
        '''
        Method to test using HTTP or HTTPS using HTTP3 Library
        HTTP3 has async capabilities
        '''
        test_info['last_stat'] = test_info['status']
        test_info['rtt'] = '--'
        test_info['good'] = False
        test_info['status'] = 'Incomplete'
        try:
            client = http3.AsyncClient()
            start = time.time()
            if test_info['test'] == 'HTTP':
                url = f'http://{test_info["host"]}'
                resp = await client.get(url, timeout=self.timeout)
            if test_info['test'] == 'HTTPS':
                url = f'https://{test_info["host"]}'
                resp = await client.get(url, timeout=self.timeout, verify=False)
            test_info['good'] = True
            test_info['status'] = self.stat_dict.get(resp.status_code, 'Unknown')

        except http3.exceptions.RedirectLoop:
            test_info['good'] = False
            test_info['status'] = 'Redirect Loop'

        except http3.exceptions.ConnectTimeout:
            test_info['good'] = False
            test_info['status'] = 'Time Out'

        except http3.exceptions.ReadTimeout:
            test_info['good'] = False
            test_info['status'] = 'Time Out'

        except socket.gaierror:
            test_info['good'] = False
            test_info['status'] = 'Bad Address'

        except OSError:
            test_info['good'] = False
            test_info['status'] = 'Unreachable'

        except asyncio.CancelledError:
            print('Cancelled !!')

        test_info['total'] += 1

        if not test_info['good']:
            test_info['last_bad'] = datetime.now().strftime('%a %H:%M:%S')
            test_info['last_bad_status'] = test_info['status']
        else:
            test_info['last_good'] = datetime.now().strftime('%a %H:%M:%S')
            test_info['total_successes'] += 1
            test_info['rtt'] = '{:.2f} ms'.format((time.time() - start) * 1000)

        test_info['success_percent'] = sucPer(
                                            test_info['total'],
                                            test_info['total_successes']
                                            )
        return test_info


def sucPer(total_trys, successes):
    '''
    This is just a function to work out pecentage success
    and cope with the Zero division
    '''
    try:
        totp = "{0:.2f} %".format(successes/total_trys * 100)
    except ZeroDivisionError:
        totp = "0.00 %"
    return totp
