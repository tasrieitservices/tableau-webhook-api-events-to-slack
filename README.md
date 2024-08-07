
# Tableau Webhooks Api Events and Slack Integration

This project is developed by Tasrie IT Services using python and provides a Flask application to integrate Tableau Webhooks with Slack. The application can create, list, and delete Tableau webhooks and post notifications to Slack when events occur.

## Prerequisites

- Python 3.8+
- Flask
- Requests
- Docker (for containerization)

## Setup

### Environment Variables

The application requires the following environment variables to be set:

- `SLACK_WEBHOOK_URL`: The Slack webhook URL to post messages to.
- `SLACK_CHANNEL`: The Slack channel to post messages to.
- `SLACK_COLOR` (optional): The color of the Slack message attachments (default is `#C70039`).

- `TABLEAU_SERVER`: The Tableau server URL.
- `TABLEAU_USERNAME`: The Tableau username.
- `TABLEAU_PASSWORD`: The Tableau password.
- `TABLEAU_SITE_ID`: The Tableau site ID.
- `TABLEAU_VERSION` (optional): The Tableau API version (default is `3.21`).

### Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Running the Application

### Locally

To run the application locally, use the following command:

```bash
python webhook.py
```

The application will be accessible at `http://0.0.0.0:5001`.

### Using Docker

Build and run the Docker container:

```bash
docker build -t tableau-webhooks .
docker run -p 5000:5000 --env-file .env tableau-webhooks
```

## API Endpoints

### Webhook Endpoint

**URL:** `/webhook`  
**Method:** `POST`  
**Description:** Receives Tableau event notifications and posts them to Slack.

### Create Tableau Webhook

**URL:** `/create_tableau_webhook`  
**Method:** `POST`  
**Description:** Creates a new Tableau webhook.

**Payload:**

```json
{
  "name": "webhook_name",
  "event": "event_type",
  "destination_url": "destination_url"
}
```

### List Tableau Webhooks

**URL:** `/list_tableau_webhooks`  
**Method:** `GET`  
**Description:** Lists all Tableau webhooks.

### Delete Tableau Webhook

**URL:** `/delete_tableau_webhook`  
**Method:** `POST`  
**Description:** Deletes a Tableau webhook.

**Payload:**

```json
{
  "webhook_id": "webhook_id"
}
```

## Logging

The application uses the Python `logging` module to log information. Logs include timestamps, log level, and messages.

## Error Handling

The application includes custom exception classes (`ApiCallError` and `UserDefinedFieldError`) to handle specific errors.

