#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  store.py
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


def get_users():
    """Get list of all users"""
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    users = {}
    for each in secrets:
        if isinstance(secrets[each], dict):
            users[each] = User(each, secrets[each]["password_hash"])
    return users


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
# For security purposes, delete the pre-hashed version of the key and the secrets data struct
del key, secrets


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
    return get_users()[username]


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
def search(term, internal=False):
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
        if not internal:
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
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
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

    login_user(get_users()[username], remember=remember)
    return redirect(url_for('home'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/add_game")
@login_required
def interface_ag():
    return render_template("add_game.html")


@app.route("/add_game", methods=["POST"])
@login_required
def add_game():
    db = sql.connect(settings["db_name"])
    # We can get everything except the base64, time, and downloads from the form
    # The remaining 2 (base64 and time) we have to get ourselves
    # Downloads can be assumed to be 1
    base64_val = base64.encodestring(request.form.get("URL").encode()).decode()
    base64_val = base64_val.strip("\r")
    base64_val = base64_val.strip("\n")
    name = request.form.get("name").replace(" ", "_")
    add = """VALUES ("%s", "%s", %s, "%s", "%s", "%s", "%s", "%s", "%s", %s, %s)""" % (name,
                                                                                       base64_val,
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
    temp = render_template("add_game.html")
    place_holder = "<!-- ### -->"
    added = "</br>" + name.replace("_", " ") + " Successfully Added!</br>"
    temp = temp.replace(place_holder, added)
    return temp


@app.route("/remove_game")
@login_required
def interface_rg():
    temp = render_template("remove_game.html")
    place_holder = "<!-- ### -->"
    base64_vals = """<input type="hidden" id="base64_vals" name="base64_vals" value="">"""
    temp = temp.replace(place_holder, base64_vals)
    return temp


@app.route("/remove_game", methods=["POST"])
@login_required
def rg_post_toggle():
    remove_games_button = request.form.get("remove_games")
    search_button = request.form.get("search")
    if search_button is not None:
        return get_games_rg(search_button)
    base64_vals = request.form.get("base64_vals").split(",")
    for each in base64_vals:
        each = each.strip("\r")
        each = each.strip("\n")
    return remove_games(base64_vals, request.form)


@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=current_user.username)


def get_games_rg(orig_search_term):
    if orig_search_term[0] == "$":
        search_term = "tags=" + orig_search_term[1:]
    else:
        search_term = "free-text=" + orig_search_term
    search_results = search(search_term, internal=True)
    temp = render_template("remove_game.html")
    place_holder = "<!-- ### -->"
    output = []
    base64_output = []
    # We have our search terms. We have our template. Now we need to generate the
    # data to parse into the template
    for each in search_results:
        check_box = """
            <div class="field">
                <label class="checkbox">
                    <input type="checkbox" name="%s">
                    <!-- ### -->
                </label>
            </div>
""" % (search_results[each]["base64"])
        check_box = check_box.replace(place_holder, search_results[each]["Name"].replace("_", " "))
        # Make sure replacing it later doesn't overwrite the copied value
        output.append(copy.deepcopy(check_box))
        base64_output.append(search_results[each]["base64"])
    base64_vals = """<input type="hidden" id="base64_vals" name="base64_vals" value="%s">""" % (",".join(base64_output))
    prev_search_term = """<input type="hidden" id="prev_search_term" name="prev_search_term" value="%s">""" % (orig_search_term)
    output = "</br>".join(output)
    output = base64_vals + prev_search_term + "</br>" + output
    temp = temp.replace(place_holder, output)
    return temp


def remove_games(base64_vals, form):
    db = sql.connect(settings["db_name"])
    deleted = []
    delete_command = """DELETE FROM games WHERE base64=\""""
    select_command = """SELECT * FROM games WHERE base64=\""""
    place_holder = "<!-- ### -->"
    temp = render_template("remove_game.html")
    for each in base64_vals:
        if form.get(each) == "on":
            data = format_data(db.execute(select_command + each + "\"").fetchall())[0]
            print(data)
            deleted.append(data["Name"].replace("_", " "))
            db.execute(delete_command + each + "\"")
    db.commit()
    deleted = "</br>" + ", ".join(deleted) + " Successfully Deleted!</br>"
    temp = temp.replace(place_holder, deleted)
    return temp


@app.route("/add_account")
@login_required
def serve_add_account(errors=""):
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    username = current_user.username
    place_holder = "<!-- ### -->"
    error = ""
    if errors == "mismatch_password":
        error = "Passwords do not match!"
    elif errors == "username_taken":
        error = "That username is taken!"
    elif errors == "account_created":
        error = "Account Created Successfully!"
    temp = render_template("create_account.html", error=error)
    radio_button = """
    <input type="radio" id="%s" name="hash_algo" value="%s" %s>
    <label for="%s">%s</label><br>
    """
    output = []
    for each in hash.algorithms_guaranteed:
        if "shake" not in each:
            if each == secrets[username]["hash_algo"]:
                output.append(radio_button % (each, each, "checked", each, each))
            else:
                output.append(radio_button % (each, each, "", each, each))
    output = "</br>".join(output)
    temp = temp.replace(place_holder, output)
    return temp


@app.route("/add_account", methods=["POST"])
@login_required
def add_account():
    # Load a local copy of the auth file
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    username = request.form.get("username")
    password = request.form.get("password")
    password_check = request.form.get("password_check")
    hash_algo = request.form.get("hash_algo")
    hash_number = int(request.form.get("hash_number"))
    removable = request.form.get("removable")
    if removable == "on":
        removable = True
    else:
        removable = False
    # Check password
    if password != password_check:
        return serve_add_account(errors="mismatch_password")
    # Check username
    del password_check
    if username in secrets:
        return serve_add_account(errors="username_taken")
    gen_hash = password
    hash_func = getattr(hash, hash_algo)
    for each in range(hash_number):
        gen_hash = hash_func(gen_hash.encode()).hexdigest()
    secrets[username] = {"password_hash": gen_hash, "hash_algo": hash_algo,
                         "rehash_count": hash_number, "removable": removable}
    with open(settings["secrets_file"], "w") as file:
        json.dump(secrets, file, indent=2)
    # Delete everything we had in memory to make it harder to access in compromised situations
    del secrets, hash_func, gen_hash, password, username, hash_algo, hash_number
    return serve_add_account(errors="account_created")


@app.route("/remove_account")
@login_required
def serve_remove_account(errors=""):
    """Serve remove account"""
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    place_holder = "<!-- ### -->"
    error = ""
    if errors == "missing_account":
        error = "Account Not Found!"
    elif errors == "account_removed":
        error = "Account Removed Successfully!"
    temp = render_template("remove_account.html", error=error)
    radio_button = """
    <input type="radio" id="%s" name="remove" value="%s">
    <label for="%s">%s</label><br>
    """
    output = []
    workable = {}
    for each in secrets:
        if isinstance(secrets[each], dict):
            workable[each] = secrets[each]
    for each in workable:
        if workable[each]["removable"]:
            output.append(radio_button % (each, each, each, each))
    if output == []:
        output.append("No removable accounts found")
    output = "</br>".join(output)
    temp = temp.replace(place_holder, output)
    return temp


@app.route("/remove_account", methods=["POST"])
@login_required
def remove_account():
    """Remove accounts"""
    account = request.form.get("remove")
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    if account not in secrets:
        return serve_remove_account(error="missing_account")
    del secrets[account]
    with open(settings["secrets_file"], "w") as file:
        json.dump(secrets, file, indent=2)
    return serve_remove_account(errors="account_removed")


@app.route("/edit_account")
@login_required
def serve_edit_account(errors=""):
    """Edit your account"""
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    place_holder = "<!-- ### -->"
    error = ""
    if errors == "edit_success":
        error = "Account Change Successfull!"
    elif errors == "mismatch_password":
        error = "Passwords do not match!"
    elif errors == "unknown_password":
        error = "In order to change hashing settings, you must reset or change your password."
    username = current_user.username
    hash_count = secrets[username]["rehash_count"]
    temp = render_template("edit_account.html", error=error, username=username,
                           hash_number=hash_count)
    radio_button = """
    <input type="radio" id="%s" name="hash_algo" value="%s" %s>
    <label for="%s">%s</label><br>
    """
    output = []
    for each in hash.algorithms_guaranteed:
        if "shake" not in each:
            if each == secrets[username]["hash_algo"]:
                output.append(radio_button % (each, each, "checked", each, each))
            else:
                output.append(radio_button % (each, each, "", each, each))
    output = "</br>".join(output)
    temp = temp.replace(place_holder, output)
    return temp


@app.route("/edit_account", methods=["POST"])
@login_required
def edit_account(errors=""):
    """Edit account"""
    with open(settings["secrets_file"], "r") as file:
        secrets = json.load(file)
    username = current_user.username
    password = request.form.get("password")
    password_check = request.form.get("password_check")
    hash_algo = request.form.get("hash_algo")
    hash_number = int(request.form.get("hash_number"))
    if password != password_check:
        return serve_edit_account(errors="mismatch_password")
    if ((hash_algo != secrets[username]["hash_algo"]) and ("" in (password, password_check))):
        return serve_edit_account(errors="unknown_password")
    if ((hash_number != secrets[username]["rehash_count"]) and ("" in (password, password_check))):
        return serve_edit_account(errors="unknown_password")
    del password_check
    gen_hash = password
    hash_func = getattr(hash, hash_algo)
    for each in range(hash_number):
        gen_hash = hash_func(gen_hash.encode()).hexdigest()
    secrets[username]["password_hash"] = gen_hash
    secrets[username]["rehash_count"] = hash_number
    secrets[username]["hash_algo"] = hash_algo
    with open(settings["secrets_file"], "w") as file:
        json.dump(secrets, file, indent=2)
    del secrets, hash_func, gen_hash, password, username, hash_algo, hash_number
    return serve_edit_account(errors="edit_success")


if __name__ == "__main__":
    app.run()
