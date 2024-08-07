import os
from flask import Flask, request, jsonify
import logging
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Slack webhook URL
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL')
SLACK_COLOR = os.getenv('SLACK_COLOR', '#C70039')

# Tableau API URL and token
TABLEAU_SERVER = os.getenv('TABLEAU_SERVER')
TABLEAU_USERNAME = os.getenv('TABLEAU_USERNAME', )
TABLEAU_PASSWORD = os.getenv('TABLEAU_PASSWORD', '')
TABLEAU_SITE_ID = os.getenv('TABLEAU_SITE_ID')
VERSION = float(os.getenv('TABLEAU_VERSION', 3.21))  # Ensure VERSION is a float
XMLNS = {'t': 'http://tableau.com/api'}

# Check if SLACK_WEBHOOK_URL and Tableau variables are set
if not all([SLACK_WEBHOOK_URL, SLACK_CHANNEL]):
    logging.error("Slack environment variable are not set")
    raise RuntimeError("(SLACK_WEBHOOK_URL, SLACK_CHANNEL) environment variable are required")

if not all([TABLEAU_SERVER, TABLEAU_USERNAME, TABLEAU_PASSWORD]):
    logging.error("Tableau environment variables are not set")
    raise RuntimeError(
        "Tableau environment variables (TABLEAU_SERVER, TABLEAU_USERNAME, TABLEAU_PASSWORD) are required")

# List of valid Tableau events
VALID_TABLEAU_EVENTS = [
    'AdminPromoted',
    'AdminDemoted',
    'DatasourceUpdated',
    'DatasourceCreated',
    'DatasourceDeleted',
    'DatasourceRefreshStarted',
    'DatasourceRefreshSucceeded',
    'DatasourceRefreshFailed',
    'LabelCreated',
    'LabelUpdated',
    'LabelDeleted',
    'SiteCreated',
    'SiteUpdated',
    'SiteDeleted',
    'UserDeleted',
    'ViewDeleted',
    'WorkbookUpdated',
    'WorkbookCreated',
    'WorkbookDeleted',
    'WorkbookRefreshStarted',
    'WorkbookRefreshSucceeded',
    'WorkbookRefreshFailed',
]


class ApiCallError(Exception):
    """ ApiCallError """
    pass


class UserDefinedFieldError(Exception):
    """ UserDefinedFieldError """
    pass


def _encode_for_display(text):
    """
    Encodes strings so they can display as ASCII in a Windows terminal window.
    This function also encodes strings for processing by xml.etree.ElementTree functions.

    Returns an ASCII-encoded version of the text.
    Unicode characters are converted to ASCII placeholders (for example, "?").
    """
    return text.encode('ascii', errors="backslashreplace").decode('utf-8')


def _check_status(server_response, success_code):
    """
    Checks the server response for possible errors.

    'server_response'       the response received from the server
    'success_code'          the expected success code for the response
    Throws an ApiCallError exception if the API call fails.
    """
    if server_response.status_code != success_code:
        parsed_response = ET.fromstring(server_response.text)

        # Obtain the 3 xml tags from the response: error, summary, and detail tags
        error_element = parsed_response.find('t:error', namespaces=XMLNS)
        summary_element = parsed_response.find('.//t:summary', namespaces=XMLNS)
        detail_element = parsed_response.find('.//t:detail', namespaces=XMLNS)

        # Retrieve the error code, summary, and detail if the response contains them
        code = error_element.get('code', 'unknown') if error_element is not None else 'unknown code'
        summary = summary_element.text if summary_element is not None else 'unknown summary'
        detail = detail_element.text if detail_element is not None else 'unknown detail'
        error_message = '{0}: {1} - {2}'.format(code, summary, detail)
        raise ApiCallError(error_message)
    return


def sign_in(server, username, password, site):
    """
    Signs in to the server specified with the given credentials

    'server'   specified server address
    'username' is the name (not ID) of the user to sign in as.
               Note that most of the functions in this example require that the user
               have server administrator permissions.
    'password' is the password for the user.
    'site'     is the ID (as a string) of the site on the server to sign in to. The
               default is "", which signs in to the default site.
    Returns the authentication token and the site ID.
    """
    url = server + "/api/{0}/auth/signin".format(VERSION)

    # Builds the request
    xml_request = ET.Element('tsRequest')
    credentials_element = ET.SubElement(xml_request, 'credentials', personalAccessTokenName=username,
                                        personalAccessTokenSecret=password)
    ET.SubElement(credentials_element, 'site', contentUrl=site)
    xml_request = ET.tostring(xml_request)

    # Make the request to server
    server_response = requests.post(url, data=xml_request)
    _check_status(server_response, 200)

    # ASCII encode server response to enable displaying to console
    server_response = _encode_for_display(server_response.text)

    # Reads and parses the response
    parsed_response = ET.fromstring(server_response)

    # Gets the auth token and site ID
    token = parsed_response.find('t:credentials', namespaces=XMLNS).get('token')
    site_id = parsed_response.find('.//t:site', namespaces=XMLNS).get('id')
    # user_id = parsed_response.find('.//t:user', namespaces=XMLNS).get('id')
    return token, site_id


def sign_out(server, auth_token):
    """
    Destroys the active session and invalidates authentication token.

    'server'        specified server address
    'auth_token'    authentication token that grants user access to API calls
    """
    url = server + "/api/{0}/auth/signout".format(VERSION)
    server_response = requests.post(url, headers={'x-tableau-auth': auth_token})
    _check_status(server_response, 204)
    return


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        data = request.json
        logging.info(f"Received data: {data}")

        # Extract necessary information
        event_type = data.get('event_type', 'Unknown Event')
        text = data.get('text', 'No additional information provided.')
        resource_name = data.get('resource_name', 'Unknown Resource')

        # Post data to Slack with attachments
        slack_data = {
            'channel': SLACK_CHANNEL,
            'attachments': [
                {
                    'fallback': f'{event_type} - {resource_name}',
                    'color': SLACK_COLOR,
                    'pretext': f'{event_type}:',
                    'fields': [
                        {
                            'title': resource_name,
                            'value': text,
                            'short': False
                        }
                    ]
                }
            ]
        }
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_data)

        if response.status_code == 200:
            logging.info("Alert posted to Slack successfully")
            return jsonify({'status': 'success'}), 200
        else:
            logging.error(f"Failed to post data to Slack: {response.text}")
            return jsonify({'status': 'failure', 'error': response.text}), 500
    else:
        return jsonify({'status': 'failure'}), 400


@app.route('/create_tableau_webhook', methods=['POST'])
def create_tableau_webhook():
    if request.method == 'POST':
        data = request.json
        logging.info(f"Received data for Tableau webhook creation: {data}")

        webhook_name = data.get('name')
        event_type = data.get('event')
        destination_url = data.get('destination_url')

        if not webhook_name:
            logging.error("Webhook name is missing")
            return jsonify({'status': 'failure', 'error': 'Webhook name is required'}), 400

        if not event_type:
            logging.error("Event type is missing")
            return jsonify({'status': 'failure', 'error': 'Event type is required'}), 400

        if event_type not in VALID_TABLEAU_EVENTS:
            logging.error("Invalid event type")
            return jsonify({
                'status': 'failure',
                'error': f'Invalid event type: {event_type}. Please refer to the valid event types: https://help.tableau.com/current/developer/webhooks/en-us/docs/webhooks-events-payload.html'
            }), 400

        if not destination_url:
            logging.error("Destination URL is missing")
            return jsonify({'status': 'failure', 'error': 'Destination URL is required'}), 400
        logging.info(f"Webhook name: {webhook_name}")
        logging.info(f"Event type: {event_type}")
        logging.info(f"Destination URL: {destination_url}")

        # Create the XML payload
        token, site_id = sign_in(TABLEAU_SERVER, TABLEAU_USERNAME, TABLEAU_PASSWORD, TABLEAU_SITE_ID)
        ts_request = ET.Element('tsRequest')
        webhook_xml = ET.SubElement(ts_request, 'webhook', name=webhook_name, event=event_type)
        webhook_destination = ET.SubElement(webhook_xml, 'webhook-destination')
        ET.SubElement(webhook_destination, 'webhook-destination-http', method='POST', url=destination_url)
        xml_payload = ET.tostring(ts_request, encoding='utf-8', method='xml')
        logging.info(f"Calling tableau webhook api with payload: {xml_payload}")

        tableau_url = f"{TABLEAU_SERVER}/api/{VERSION}/sites/{site_id}/webhooks"
        headers = {
            'X-Tableau-Auth': token,
            'Content-Type': 'application/xml'
        }
        response = requests.post(tableau_url, data=xml_payload, headers=headers)

        if response.status_code == 201:
            logging.info("Tableau webhook created successfully")
            return jsonify({'status': 'success'}), 201
        else:
            logging.error(f"Failed to create Tableau webhook: {response.text}")
            return jsonify({'status': 'failure', 'error': response.text}), 500
    else:
        return jsonify({'status': 'failure'}), 400


@app.route('/list_tableau_webhooks', methods=['GET'])
def list_tableau_webhooks():
    token, site_id = sign_in(TABLEAU_SERVER, TABLEAU_USERNAME, TABLEAU_PASSWORD, TABLEAU_SITE_ID)
    url = TABLEAU_SERVER + f"/api/{VERSION}/sites/{site_id}/webhooks"
    server_response = requests.get(url, headers={'x-tableau-auth': token})
    _check_status(server_response, 200)
    webhooks_data = []
    root = ET.fromstring(server_response.text)
    for _webhook in root.findall('.//{http://tableau.com/api}webhook'):
        webhook_data = {
            'id': _webhook.get('id'),
            'name': _webhook.get('name'),
            'event': _webhook.get('event'),
            'url': _webhook.find('.//{http://tableau.com/api}webhook-destination-http').get('url')
        }
        webhooks_data.append(webhook_data)

    return jsonify({'status': 'success', 'webhooks': webhooks_data}), 200


@app.route('/delete_tableau_webhook', methods=['POST'])
def delete_tableau_webhook():
    data = request.json
    webhook_id = data.get('webhook_id')

    if not webhook_id:
        logging.error("Missing required parameters: site_id or webhook_id")
        return jsonify({'status': 'failure', 'error': 'Missing required parameters: site_id or webhook_id'}), 400

    token, site_id = sign_in(TABLEAU_SERVER, TABLEAU_USERNAME, TABLEAU_PASSWORD, TABLEAU_SITE_ID)
    tableau_url = f"{TABLEAU_SERVER}/api/{VERSION}/sites/{site_id}/webhooks/{webhook_id}"
    headers = {
        'X-Tableau-Auth': token,
        'Content-Type': 'application/xml'
    }
    response = requests.delete(tableau_url, headers=headers)

    if response.status_code == 204:
        logging.info("Tableau webhook deleted successfully")
        return jsonify({'status': 'success'}), 204
    else:
        logging.error(f"Failed to delete Tableau webhook: {response.text}")
        return jsonify({'status': 'failure', 'error': response.text}), response.status_code


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

