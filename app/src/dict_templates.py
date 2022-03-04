class DictTemplate:
    image = {
        "properties": {
            "alignment": "LEFT",
            "width": 740
        }
    }

    question_item = {
        "questionItem": {
            "question": {
                "required": "True",
                "scaleQuestion": {
                    "low": 1,
                    "high": 10
                }
            }
        }
    }

    image_item = {
        "imageItem": {
            "image": {
                "properties": {
                    "alignment": "LEFT",
                    "width": 740
                }
            }
        }
    }

    create_item = {
        "createItem": {
            "item": "",
            "location": {
                "index": ""
            }
        }
    }

    upd_form_info = {
        "updateFormInfo": {
            "info": {
                "description": "A meccs véget ért,így jöhet az értékelés - ezúttal tőled! A megszokott módon egy tízes skálán pontozhatod a srácokat, szigorúan szubjektíven."
            },
            "updateMask": "description, documentTitle"
        }
    }