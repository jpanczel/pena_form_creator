import json
import requests


class LastMatchApiClient:

    def __init__(self, api_key):
        self.payload = {}
        self.headers = {
            'x-rapidapi-host': "api-football-v1.p.rapidapi.com/v3/",
            'x-rapidapi-key': api_key
        }

    def make_api_call(self, endpoint):
        conn = f"https://api-football-v1.p.rapidapi.com/v3/{endpoint}"
        response = requests.request("GET", conn, headers=self.headers, data=self.payload)
        text_response = json.loads(response.text)
        return text_response

    @staticmethod
    def loop_through_dict(loop_list, key_level1, key_level2, return_list=[]):
        for elem in loop_list:
            return_list.append(elem.get(key_level1).get(key_level2))
        return return_list

    def main(self):
        starting_player_number_list, sub_player_number_list = [], []
        # getting the home and away teams and match id
        text_response = self.make_api_call("fixtures?team=541&last=1")
        home_team = text_response["response"][0]["teams"]["home"]["name"]
        away_team = text_response["response"][0]["teams"]["away"]["name"]
        last_match_id = text_response["response"][0]["fixture"]["id"]

        # getting the substitute player ids
        text_response = self.make_api_call(f"fixtures/events?fixture={last_match_id}&team=541&type=Subst")
        subst_player_ids_list = self.loop_through_dict(text_response["response"], "player", "id")

        # getting the starting player ids
        text_response = self.make_api_call(f"fixtures/lineups?fixture={last_match_id}&team=541")
        starting_player_number_list = self.loop_through_dict(text_response["response"][0]["startXI"], "player", "number",
                                                        starting_player_number_list)

        for subst_player_id in subst_player_ids_list:
            for substitute_player in text_response["response"][0]["substitutes"]:
                if substitute_player["player"]["id"] == subst_player_id:
                    sub_player_number_list.append(substitute_player["player"]["number"])

        return starting_player_number_list, sub_player_number_list, home_team, away_team

    if __name__ == '__main__':

        main()
