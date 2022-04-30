from __future__ import print_function

import json
import logging
import os

import google_auth_httplib2
from googleapiclient import discovery
from src.example_form import ErtekeloForm
from src.get_match_info_api import LastMatchApiClient
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
import flask
from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv()


def get_secret(secret_id, version_id="latest", secret_create=True, project_id=os.getenv("GCP_PROJECT_ID")):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")

    if not secret_create:
        return payload
    file_path = create_secret_file(payload, secret_id)
    return file_path


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = get_secret(os.getenv("FLASK_SECRET_KEY_NAME"), secret_create=False)


def create_secret_file(obj_to_write, file_name):
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{curr_dir}/tmp/{file_name}.json"
    with open(file_path, "w+") as f:
        f.writelines(obj_to_write)
    return file_path


def create_update_batch_list(class_instance, home_team, away_team, subs, starters):
    class_instance.update_form_info(home_team, away_team)
    class_instance.add_image_item("coach")
    class_instance.create_form_questions(os.getenv("COACH_NAME"), 1, os.getenv("COACH_ABBR"))
    if subs:
        for idx, sub in enumerate(subs):
            class_instance.create_form_questions(sub, idx)
        class_instance.add_image_item("subs")

    for idx, starter in enumerate(starters):
        class_instance.create_form_questions(starter, idx)
    class_instance.add_image_item("players")
    class_instance.create_form_questions(away_team, 0, away_team, False)
    class_instance.create_form_questions(home_team, 0, home_team, False)
    class_instance.add_image_item("teams")


def create_form(rapid_api, form_service):
    match_api_consumer = LastMatchApiClient(rapid_api)
    starting_11, substitutes, home_team_name, away_team_name = match_api_consumer.main()

    form = ErtekeloForm.create_form_info(home_team_name, away_team_name)
    ertekelo_form = ErtekeloForm()

    # Prints the details of the sample form
    createresult = form_service.forms().create(body=form).execute()
    form_url = createresult["responderUri"]

    create_update_batch_list(ertekelo_form, home_team_name, away_team_name, substitutes, starting_11)
    update = ertekelo_form.update_form()
    form_service.forms().batchUpdate(
        formId=createresult["formId"], body=update).execute()
    return form_url


@app.route("/api/createform", methods=["GET"])
def main():
    cs_name = os.getenv("CS_NAME")
    global SCOPES, DISCOVERY_DOC, CLIENT_SECRETS_FILE, rapid_api_key

    CLIENT_SECRETS_FILE = get_secret(cs_name)
    api_key = get_secret(os.getenv("PENA_FORM_KEY_NAME"), secret_create=False)
    rapid_api_key = get_secret(os.getenv("RAPIDAPI_KEY_NAME"), secret_create=False)
    SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/userinfo.profile"]
    DISCOVERY_DOC = f"https://forms.googleapis.com/$discovery/rest?version=v1beta&key={api_key}&labels=FORMS_BETA_TESTERS"

    return flask.redirect("/api/form_url")


@app.route("/api/form_url")
def call_form_creation():
    if "credentials" not in flask.session:
        return flask.redirect("authorize")
    credentials = Credentials(
        **flask.session["credentials"])

    drive = discovery.build("forms", "v1beta", credentials=credentials, discoveryServiceUrl=DISCOVERY_DOC,
                            static_discovery=False)

    form_url = create_form(rapid_api_key, drive)
    flask.session["credentials"] = credentials_to_dict(credentials)
    return form_url


@app.route("/api/authorize")
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

    authorization_url, state = flow.authorization_url(include_granted_scopes="true")

    flask.session["state"] = state

    return flask.redirect(authorization_url)


def get_user_info(credentials):
    user_info_service = discovery.build(
        serviceName="oauth2", version="v2",
        credentials=credentials)
    user_info = None
    try:
        user_info = user_info_service.userinfo().get().execute()
    except Exception as e:
        logging.warning(f"An error occurred: {e}")
    if user_info and user_info.get("id"):
        return user_info


def run_bigquery_query(client, table_id):
    query = f"SELECT user_id, flow_credentials FROM `{table_id}`"
    query_job = client.query(query)  # Make an API request.

    return query_job


def insert_rows(user_id, flow_credentials, client, table_id):
    rows_to_insert = [
        {"user_id": user_id,
         "flow_credentials": str(flow_credentials)}
    ]
    errors = client.insert_rows_json(table_id, rows_to_insert)  # Make an API request.
    if errors:
        logging.warning(f"Encountered errors while inserting rows: {errors}")


@app.route("/api/oauth2callback")
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session["state"]

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

    authorization_response_http = flask.request.url
    authorization_response = authorization_response_http.replace("http", "https")
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    user_id = get_user_info(credentials)["id"]
    table_id = "pena-340621.google_flow_credentials.user_id_flows"

    flask.session["credentials"] = check_for_user_or_insert(credentials, user_id, table_id)

    return flask.redirect(flask.url_for("call_form_creation"))


def check_for_user_or_insert(credentials, user_id, table_id, has_been_found=False, client=bigquery.Client()):
    stored_flows = run_bigquery_query(client, table_id)
    for stored_flow in stored_flows:
        flow_credentials = stored_flow["flow_credentials"].replace("'", '"')
        if user_id == stored_flow["user_id"]:
            logging.warning("user has been found")
            has_been_found = True
            return json.loads(flow_credentials)
    if not has_been_found:
        insert_rows(user_id, credentials_to_dict(credentials), client, table_id)
        return credentials_to_dict(credentials)


def credentials_to_dict(credentials):
    return {"token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
