#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  app.py
#
#  Copyright 2021 Thomas Castleman <contact@draugeros.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
"""Explain what this program does here!!!"""
from __future__ import print_function
import sys
import json
import os
import base64
import time
import copy
import random
import hashlib as hash
import sqlite3 as sql
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import login_user, login_required, current_user, logout_user, UserMixin, LoginManager


def __eprint__(*args, **kwargs):
    """Make it easier for us to print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


def gen_rand_string(length=16):
    string = []
    for each in range(length):
        add = random.randint(33, 1000)
        if random.randint(0, 1000) % 1.85:
            string.append(chr(add))
        else:
            string.append(str(add))
    return "".join(string)



if sys.version_info[0] == 2:
    __eprint__("Please run with Python 3 as Python 2 is End-of-Life.")
    exit(2)

app = Flask(__name__)
if not os.path.isfile("settings.json"):
    __eprint__("Settings file not present. Please make a settings file and retry.")
    sys.exit(1)
with open("settings.json", "r") as file:
    settings = json.load(file)

with open(settings["secrets_file"], "r") as file:
    secrets = json.load(file)


class User(UserMixin):
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash

    def get_id(self):
        return self.username


users = {}
for each in secrets:
    if isinstance(secrets[each], dict):
        users[each] = User(each, secrets[each]["password_hash"])

# Initialize the DB
db = sql.connect(settings["db_name"])
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
if len(tables) < 1:
    db.execute("""CREATE TABLE games
    (name TEXT, base64 BLOB, downloads INTEGER, genres TEXT, url BLOB,
    screenshots_url BLOB, description TEXT, rating TEXT, platform TEXT,
    add_time INTEGER, in_pack_man BOOLEAN)""")
    if os.path.isfile("default_games.json"):
        with open("default_games.json", "r") as file:
            default_games = json.load(file)
        for each in default_games:
            db.execute("""INSERT INTO games VALUES
("%s", "%s", %s, "%s", "%s", "%s", "%s",
"%s", "%s", %s, %s)""" % (default_games[each]["Name"],
                          default_games[each]["base64"],
                          default_games[each]["downloads"],
                          ",".join(default_games[each]["genres"]),
                          default_games[each]["URL"],
                          default_games[each]["screenshots_url"],
                          default_games[each]["description"],
                          default_games[each]["rating"],
                          default_games[each]["platform"],
                          default_games[each]["joined"],
                          default_games[each]["in_pack_man"]))
    db.commit()
db.close()

# Initalize Flask
# Generate a random, alpha numeric key. With optional salting.
key = gen_rand_string(length=secrets["secret_key_len"]) + secrets["salt"]
app.config["SECRET_KEY"] = hash.sha512(key.encode()).hexdigest()
# For security purposes, delete the pre-hashed version of the key
del key


def format_data(to_format):
    return_data = {}
    length = 0
    for data in to_format:
        add = {"Name": data[0], "base64": data[1], "downloads": data[2],
               "genres": data[3].split(","), "URL": data[4],
               "screenshots_url": data[5], "description": data[6],
               "rating": data[7].upper(), "platform": data[8].lower(),
               "joined": data[9], "in_pack_man": data[10]}
        return_data[length] = copy.deepcopy(add)
        length+=1
    return return_data


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(username):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return users[username]


@app.route("/")
def front_page():
    return """
This is the %s API. This page is here to greet end users.
We strongly advise that you use the official client to interact with this API.
""" % (settings["store_name"])


@app.route("/games")
def game_front_page():
    db = sql.connect(settings["db_name"])
    data = db.execute("SELECT * FROM games").fetchall()
    data = format_data(data)
    if data == {}:
        return {}
    for each in data:
        del data[each]["URL"]
        del data[each]["base64"]
        del data[each]["in_pack_man"]
    db.close()
    return data



# Looking at an individual game
@app.route("/games/<name>")
def view_game(name):
    db = sql.connect(settings["db_name"])
    data = db.execute("SELECT * FROM games WHERE name='%s'" % (name)).fetchall()
    data = format_data(data)
    if data == {}:
        return {}
    del data[0]["URL"]
    del data[0]["base64"]
    del data[0]["in_pack_man"]
    db.close()
    return data[0]


# Download game
@app.route("/games/<name>/download")
def download_game(name):
    db = sql.connect(settings["db_name"])
    data = db.execute("SELECT * FROM games WHERE name='%s'" % (name))
    return_data = format_data(data.fetchall())
    db.execute("UPDATE games SET downloads = %s WHERE base64 = '%s'" % (return_data[0]["downloads"] + 1, return_data[0]["base64"]))
    db.commit()
    db.close()
    return {"URL": return_data[0]["URL"], "in_pack_man": return_data[0]["in_pack_man"]}

# Searching for games
@app.route("/search/<term>")
def search(term):
    db = sql.connect(settings["db_name"])
    if term[:4] == "tags":
        tags = term[5:].split(",")
        return_data = {}
        length = 0
        data = format_data(db.execute("SELECT * FROM games").fetchall())
        for game in data:
            for tag in tags:
                if ((tag in data[game]["genres"]) or (tag == data[game]["rating"]) or (tag == data[game]["platform"])):
                    return_data[length] = data[game]
                    length+=1
                    break
    elif term[:9] == "free-text":
        text = term[10:]
        return_data = {}
        length = 0
        data = format_data(db.execute("SELECT * FROM games").fetchall())
        for game in data:
            if ((text.lower() in data[game]["Name"].lower()) or (text.lower() in data[game]["description"].lower())):
                return_data[length] = data[game]
                length+=1
    for each in return_data:
        del return_data[each]["URL"]
        del return_data[each]["base64"]
        del return_data[each]["in_pack_man"]
    db.close()
    return return_data


@app.route("/tags")
def get_tags():
    games = game_front_page()
    output = {"genres": [], "ratings": [], "platforms": []}
    for each in games:
        for each1 in games[each]["genres"]:
            if each1 not in output["genres"]:
                output["genres"].append(each1)
        if games[each]["rating"] not in output["ratings"]:
            output["ratings"].append(games[each]["rating"])
        if games[each]["platform"] not in output["platforms"]:
            output["platforms"].append(games[each]["platform"])
    return output


# Admin UI Section
@app.route("/" + settings["login_path"])
def login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get("username")
    gen_hash = request.form.get("password")
    remember = True if request.form.get('remember') else False

    # Check to see if the user exisits
    if username in secrets:
        # get their settings and hash their password
        stored_hash = secrets[username]["password_hash"]
        hash_func = getattr(hash, secrets[username]["hash_algo"].lower())
        for each in range(secrets[username]['rehash_count']):
            gen_hash = hash_func(gen_hash.encode()).hexdigest()

    # Double check the user exists and that the hash matches
    if ((username not in secrets) or (stored_hash != gen_hash)):
        flash('Please check your login details and try again.')
        return redirect(url_for("login"))

    login_user(users[username], remember=remember)
    return redirect(url_for('add_game'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/add_game")
@login_required
def interface():
    return render_template("interface.html")

@app.route("/add_game", methods=["POST"])
@login_required
def add_game():
    db = sql.connect(settings["db_name"])
    # We can get everything except the base64, time, and downloads from the form
    # The remaining 2 (base64 and time) we have to get ourselves
    # Downloads can be assumed to be 1
    add = """VALUES ("%s", "%s", %s, "%s", "%s", "%s", "%s", "%s", "%s", %s, %s)""" % (request.form.get("name"),
                                                                                       base64.encodestring(request.form.get("URL").encode()).decode(),
                                                                                       1, request.form.get("genres"),
                                                                                       request.form.get("URL"),
                                                                                       request.form.get("screenshots_url"),
                                                                                       request.form.get("description"),
                                                                                       request.form.get("rating").upper(),
                                                                                       request.form.get("platform").lower(),
                                                                                       time.time(),
                                                                                       True if request.form.get('in_pack_man') else False)
    command = """INSERT INTO games (name, base64, downloads, genres, url, screenshots_url, description, rating, platform, add_time, in_pack_man) %s """ % (add)
    db.execute(command)
    db.commit()
    db.close()
    return redirect(url_for('interface'))

@app.route("/remove_game")
