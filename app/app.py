from __future__ import print_function

import os

from googleapiclient import discovery
from src.example_form import ErtekeloForm
from src.get_match_info_api import LastMatchApiClient
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
import flask

app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "supersecret"


def get_secret(project_id, secret_id, version_id, secret_create=True):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")

    if not secret_create:
        return payload
    file_path = create_secret_file(payload, secret_id)
    return file_path


def create_secret_file(obj_to_write, file_name):
    CURR_DIR = dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = f"{CURR_DIR}/tmp/{file_name}.json"
    with open(file_path, "w+") as f:
        f.writelines(obj_to_write)
    return file_path


def create_update_batch_list(class_instance, home_team, away_team, subs, starters):
    class_instance.update_form_info(home_team, away_team)
    class_instance.add_image_item("coach")
    class_instance.create_form_questions("ancelotti", 1, "ANC")
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


def create_form2(rapid_api, form_service):
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


@app.route('/api/createform', methods=['GET'])
def main():
    # os.mkdir("tmp/")
    project_id = "pena-340621"
    cs_name = "client_secret_form_creator"
    sc_name = "credentials_pena_form_creator"
    global SCOPES, DISCOVERY_DOC, CLIENT_SECRETS_FILE, rapid_api_key

    CLIENT_SECRETS_FILE = get_secret(project_id, cs_name, "latest")
    # client_secret = json.loads(get_secret(project_id, cs_name, "latest", False))
    # csw = client_secret["web"]
    # storage_credentials_path = get_secret(project_id, sc_name, "latest")
    api_key = get_secret(project_id, "pena_form_creator_api_key", "latest", False)
    rapid_api_key = get_secret(project_id, "rapidapi-key", "latest", False)
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    DISCOVERY_DOC = f"https://forms.googleapis.com/$discovery/rest?version=v1beta&key={api_key}&labels=FORMS_BETA_TESTERS"
    print("scopes: ", SCOPES, "discdoc: ", DISCOVERY_DOC, "csfile:", CLIENT_SECRETS_FILE)

    return flask.redirect("/api/form_url")
    # form = create_form(SCOPES, DISCOVERY_DOC, CLIENT_SECRETS_FILE, storage_credentials_path, rapid_api_key)

    return cucc


@app.route("/api/hello", methods=["GET"])
def hello_world():
    return "hello_world"


@app.route('/api/form_url')
def test_api_request():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = Credentials(
        **flask.session['credentials'])

    drive = discovery.build(
        'forms', 'v1beta', credentials=credentials, discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)

    form_url = create_form2(rapid_api_key, drive)
    flask.session['credentials'] = credentials_to_dict(credentials)
    # shutil.rmtree("tmp/")
    return form_url


@app.route('/api/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    # flow = client.OAuth2WebServerFlow(client_id=csw["client_id"], auth_uri=csw["auth_uri"],
    #                                  token_uri=csw["token_uri"], client_secret=csw["client_secret"],
    #                                  redirect_uri=csw["redirect_uris"], scope=SCOPES)

    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    flask.session['state'] = state

    return flask.redirect(authorization_url)


@app.route('/api/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response_http = flask.request.url
    authorization_response = authorization_response_http.replace("http", "https")
    print(authorization_response, type(authorization_response))
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.redirect(flask.url_for('test_api_request'))


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
