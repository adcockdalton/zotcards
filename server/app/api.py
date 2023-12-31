import json
import os
import secrets

import openai
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify
from flask_login import current_user, AnonymousUserMixin

from .model import User, CardSet, Card, AnswerChoice, db

api = Blueprint("api", __name__)


@api.route("/api/get_user_sets", methods=["GET", "POST"])
def get_user_sets():
    data = request.json

    user_email = data.get('user_email')

    user = User.query.filter_by(email=user_email).first()

    card_sets = user.card_sets

    response = {}

    for i, card_set in enumerate(card_sets):
        response[i] = {
            "title": card_set.title,
            "progress": card_set.progress,
            "last_studied": card_set.last_studied,
            "user_id": card_set.user_id
        }

    return jsonify(response)


# ********** GPT API ********** #

load_dotenv()
API_KEY = os.environ.get("API_KEY")
openai.api_key = API_KEY


# this is a test function to see if GPT is returning any text or if API is not working
@api.route("/api/chat", methods=["GET", "POST"])
def chat():
    data = request.json
    chat_text = data.get('chat_text')

    response = get_gpt_message(chat_text)
    return response, 200


def gpt_string_to_array(string):
    string = string.replace("'", '"')
    print(string)
    print(json.loads(string))
    print(json.loads(string).values())
    print(list(json.loads(string).values()))
    result = list(json.loads(string).values())
    return result


def get_gpt_message(prompt, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(model=model, messages=messages, temperature=0)
    return response.choices[0].message["content"]


def create_card_set(parsed_set):
    card_set = CardSet(title="test_title")

    if not isinstance(current_user, AnonymousUserMixin):
        my_user = current_user
    else:
        my_user = User(email=secrets.token_hex(64))

    for card in parsed_set:
        db_card = Card(question_text=card["question"])

        for answer in card["choices"]:
            if answer == card["correct"]:
                db_card.answer_choices.append(AnswerChoice(answer_text=card["choices"][answer], is_correct=True))
            else:
                db_card.answer_choices.append(AnswerChoice(answer_text=card["choices"][answer], is_correct=False))

        card_set.cards.append(db_card)

    my_user.card_sets.append(card_set)

    db.session.add(card_set)
    db.session.commit()


@api.route("/api/get-question", methods=["GET", "POST"])
def get_question():
    # notes is the string of text representing the person's notes
    # question_type is either "MCQ" or "TrueFalse"

    data = request.json

    notes = data.get('notes')
    question_type = data.get('question_type')

    notes_prompt = f"""Generate 5 {question_type} questions based on the notes I have provided below. Format it in JSON format like so: 
        {{
            'q1': {{
                'question': '(Enter question here)',
                'choices': {{
                    'A': '(Choice A here)',
                    'B': '(Choice B here)',
                    'C': '(Choice C here)',
                    'D': '(Choice D here)',
                }},
                'correct': '(LETTER of the correct answer here)'
            }}

        }}

        I gave the structure for one question above but repeat for the other questions too in the same JSON object.
        Here are the notes: """

    final_prompt = notes_prompt + notes
    response = get_gpt_message(final_prompt)

    parsed_set = gpt_string_to_array(response)
    create_card_set(parsed_set)  # populates database

    return parsed_set, 200


# TEST

@api.route("/api/test", methods=["GET", "POST"])
def api_test():
    return jsonify({"message": "Hello from Flask backend!"})


@api.route("/api/testsend", methods=["GET", "POST"])
def api_test_send():
    message = request.json.get('test')
    return jsonify({"message": f"{message}"})


@api.route("/", methods=["GET", "POST"])
def index():
    return "INDEX"
