# -----------------------------------------
# Phantom sample App Connector python file
# -----------------------------------------

# Phantom App imports
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

# Usage of the consts file is recommended
# from jask_consts import *
import os
import requests
import json
import time
from bs4 import BeautifulSoup


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class JaskConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(JaskConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_reponse(self, response, action_result):

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):

        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code,
                error_text)

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                            url,
                            # auth=("REPLACE ME: Replace with auth credentials"),
                            json=data,
                            headers=headers,
                            verify=config.get('verify_server_cert', False),
                            params=params)
        except Exception as e:
            return RetVal(action_result.set_status( phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        self.save_progress("Test connectivity initiated")
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.
        self.save_progress("Connecting to endpoint")
        self.save_progress("Checking user: " + str(self._api_user))
        self.save_progress("Checking cluster: " + str(self._base_url))

        jask_test_params = { 'username': self._api_user, 'api_key': self._api_key, 'limit': 1 }

        self.save_progress("Connecting to endpoint")
        ret_val, response = self._make_rest_call('/api/search/signals', action_result, params=jask_test_params, headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            self.save_progress("Test Connectivity Failed. Error: {0}".format(action_result.get_message()))
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        # self.save_progress("Test Connectivity Failed, action not yet implemented")
        # return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")
    def _save_alert(self, alert_json):

        # Build the container JSON
        container_json = {}
        container_json['name'] = alert_json['name']
        container_json['description'] = alert_json['description']
        container_json['source_data_identifier'] = alert_json['id']
        container_json['label'] = 'incident'
        container_json['status'] = 'new'
        container_json['open_time'] = alert_json['timestamp']

        # Save the container
        ret_val, message, container_id = self.save_container(container_json)

        # Build artifacts from supporting signals
        try:
            signal_count = len(alert_json['signals'])
            for signal in alert_json['signals']:
                # Build JSON object to be posted later
                artifact_json = {}
                artifact_json['name'] = str(signal['name'])
                artifact_json['end_time'] = str(signal['timestamp'])
                artifact_json['label'] = 'event'
                artifact_json['type'] = 'host'
                artifact_json['end_time'] = str(signal['timestamp'] + '.0Z')
                artifact_json['source_data_identifier'] = str(signal['id'])
                artifact_json['description'] = str(signal['description'])
                artifact_json['cef'] = {}
                artifact_json['cef']['baseEventCount'] = str(signal['record_count'])
                artifact_json['cef']['src'] = str(signal['asset']['ip'])
                artifact_json['cef']['cs1'] = str(signal['detail_url'])
                artifact_json['cef']['cs1Label'] = 'Jask_Signal_Url'
                artifact_json['container_id'] = container_id

                if signal_count != 1:
                    artifact_json['run_automation'] = False
                    signal_count -= 1
                else:
                    artifact_json['run_automation'] = True

                ret_val, message, resp = self.save_artifact(artifact_json)

        except KeyError:
            pass

    def _handle_on_poll(self, param):

        # Implement the handler here
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Get time from last poll, save now as time for this poll
        last_time = str(self._state.get('last_time', 0))
        self._state['last_time'] = str(int(round(time.time() * 1000)))

        # Set the last and start times for the API
        jask_query = str('* AND timestamp: [' + last_time + ' TO *]')
        jask_alert_params = { 'username': self._api_user,
                              'api_key': self._api_key,
                              'q': jask_query,
                              'sort_by': 'timestamp',
                              'offset': '0',
                              'limit': 100 }

        self.save_state(self._state)

        # make rest call
        ret_val, response = self._make_rest_call('/api/search/alerts', action_result, params=jask_alert_params, headers=None)
        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Process the JASK SmartAlerts
        for jask_alert in response['objects']:
            self._save_alert(jask_alert)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary['important_data'] = "value"

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS)

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS
        config = self.get_config()
        self._api_user = config['api_user']
        self._api_key = config['api_key']
        self._base_url = config['login_url']

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'on_poll':
            ret_val = self._handle_on_poll(param)

        return ret_val

    def initialize(self):

        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        # self.last_run = str(int(round(time.time())))

        # get the asset config
        # config = self.get_config()

        # Access values in asset config by the name

        # Required values can be accessed directly
        # required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        # optional_config_name = config.get('optional_config_name')

        return phantom.APP_SUCCESS

    def finalize(self):

        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import pudb
    import argparse

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if (username is not None and password is None):
        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if (username and password):
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print ("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print ("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print ("Unable to get session id from the platfrom. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = JaskConnector()
        connector.print_progress_message = True

        if (session_id is not None):
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print (json.dumps(json.loads(ret_val), indent=4))

    exit(0)
