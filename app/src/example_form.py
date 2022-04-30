import copy
import requests
from .dict_templates import DictTemplate


class ErtekeloForm:
    def __init__(self):
        self.create_item_list = []

    def create_item_func(self, item, index):
        create_item = copy.deepcopy(DictTemplate.create_item)
        create_item["createItem"]["item"] = item
        create_item["createItem"]["location"]["index"] = index

        self.create_item_list.append(create_item)

    @staticmethod
    def create_image_item(url):
        image_item = copy.deepcopy(DictTemplate.image_item)
        image_item["imageItem"]["image"]["sourceUri"] = url
        return image_item

    def create_form_questions(self, player_number, index_int, question_title="", is_image=True):
        if isinstance(player_number, int):
            question_title = f"#{player_number}"
        player_url = f"https://pena-form-players.s3.eu-central-1.amazonaws.com/{player_number}.png"
        r = requests.get(player_url)
        question_item = copy.deepcopy(DictTemplate.question_item)
        question_item["title"] = question_title

        if r.status_code == 200:
            image = self.create_image_item(player_url)
            if is_image:
                question_item["questionItem"]["image"] = image["imageItem"]["image"]

        self.create_item_func(question_item, index_int)

        return self.create_item_list

    def add_image_item(self, image_type):
        image_item = self.create_image_item(f"https://pena-form-players.s3.eu-central-1.amazonaws.com/{image_type}.png")
        self.create_item_func(image_item, 0)

    def update_form(self):
        update = {
            "requests": self.create_item_list
        }

        return update

    @staticmethod
    def create_form_info(home_team, away_team):
        form_info = {
            "title": f"Így Láttátok Ti: {home_team} - {away_team}"
        }

        final_form_info = {
            "info": form_info
        }

        return final_form_info

    def update_form_info(self, home_team, away_team):
        form_title = f"Így Láttátok Ti: {home_team} - {away_team}"
        upd_form_info = copy.deepcopy(DictTemplate.upd_form_info)
        upd_form_info["updateFormInfo"]["info"]["title"] = form_title
        upd_form_info["updateFormInfo"]["info"]["documentTitle"] = form_title

        self.create_item_list.append(upd_form_info)