#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from flask import Flask, request, Response
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
#import requests
import json
#import api
import db
app = Flask(__name__)

CORS(app)
auth = HTTPBasicAuth()

admin_username = os.environ.get("ADMIN_USERNAME")
admin_password = os.environ.get("ADMIN_PASS")

@auth.verify_password
def verify_password(username, password):
    if username == admin_username and password == admin_password:
        return username


@app.route("/api/action", methods=['GET', 'POST'])
def action():
    payload = json.loads(request.form["payload"])
    # team_id = requestDict['team']['id']
    responses = []
    response_url = payload['response_url']

    for action in payload['actions']:
        responses.append(button_rsvp(
            payload['user']['id'], action['value'], payload['original_message'], response_url))

    return '', 200

@app.route("/api/events", methods=['GET', 'POST'])
@auth.login_required
def events():
    if request.method == 'GET':
        raw_events = db.get_previous_pizza_events()
        events = [{"time": a[0], "place":a[1], "attendees":a[2].split(', ')} for a in raw_events]
        return events
    else:
        if events := request.json.get('events',None):
            db.create_new_pizza_events([(convert_datetime_object_to_timestamp(event['time']), event["place"]) for event in events])
            return '', 201
    return '', 400

def convert_datetime_object_to_timestamp(date):
    months={"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
    strings = date.split()
    timestamp = f"{strings[3]}{months[strings[1]]}{strings[2]} {strings[4]} GMT"
    return timestamp


@app.route("/api/future_events", methods=['GET'])
@auth.login_required
def future_events():
    raw_events = db.get_future_pizza_events()
    return raw_events_to_list_of_dict(raw_events)

def raw_events_to_list_of_dict(raw_events):
    out_list = []
    for a in raw_events:
        event_dict = {"time": a[0], "place":a[1]}
        if a[2] is None:
            event_dict["attendees"] = []
        else:
            event_dict["attendees"] = a[2].split(', ')
        out_list.append(event_dict)
    return out_list

@app.route("/api/restaurants", methods=['GET', 'POST'])
@auth.login_required
def restaurants():
    if request.method == 'GET':
        raw_restaurants = db.get_restaurants()
        restaurants = []
        for restaurant in raw_restaurants:
            restaurants.append({
                "id": restaurant[0],
                "name": restaurant[1],
                "address": restaurant[2],
                "phone_number": restaurant[3]
            })
        return restaurants

    else:
        restaurant = request.json['restaurant']
        db.create_restaurant(restaurant)
        return '', 201


@app.route("/api/restaurants/<id>", methods=['PUT', 'DELETE'])
@auth.login_required
def edit_restaurants(id):
    if request.method == 'DELETE':
        db.delete_restaurant(str(id))
    elif request.method == 'PUT':
        restaurant = request.json['restaurant']
        db.edit_restaurant(str(id), restaurant)
    return ""

@app.route("/api/login", methods=['GET'])
@auth.login_required
def login():
    return "Ok"



def button_rsvp(user_id, rsvp, original_message, response_url):
    if user_id in api.get_invited_users():
        api.rsvp(user_id, rsvp)
        if(rsvp == "attending"):
            api.finalize_event_if_complete()
            response_JSON = response_message(
                original_message, "✅ Sweet! Det blir sykt nice! 😋")
            requests.post(response_url, response_JSON)
        elif (rsvp == "not attending"):
            api.invite_if_needed()
            response_JSON = response_message(
                original_message, "⛔️ Ah, ok. Neste gang! 🤝")
            requests.post(response_url, response_JSON)
    else:
        response_JSON = response_message(
            original_message, "💣 Hmm, hva har du gjort for noe rart nå?")
        requests.post(response_url, response_JSON)


def response_message(original_message, text):
    original_message['attachments'] = [{'text': text}]
    return json.dumps(original_message)
