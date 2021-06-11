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
import copy
import sqlite3 as sql
from flask import Flask, request


def __eprint__(*args, **kwargs):
    """Make it easier for us to print to stderr"""
    print(*args, file=sys.stderr, **kwargs)

if sys.version_info[0] == 2:
    __eprint__("Please run with Python 3 as Python 2 is End-of-Life.")
    exit(2)

app = Flask(__name__)
if not os.path.isfile("settings.json"):
    __eprint__("Settings file not present. Please make a settings file and retry.")
    sys.exit(1)
with open("settings.json", "r") as file:
    settings = json.load(file)

# Initialize the DB
db = sql.connect(settings["db_name"])
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
if len(tables) < 1:
    db.execute("""CREATE TABLE games
    (name TEXT, base64 BLOB, downloads INTEGER, genres TEXT, url BLOB,
    screenshots_url BLOB, description TEXT, rating TEXT, compile_type TEXT,
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
                          default_games[each]["compile_type"],
                          default_games[each]["joined"],
                          default_games[each]["in_pack_man"]))
    db.commit()

def format_data(to_format):
    return_data = {}
    length = 0
    for data in to_format:
        add = {"Name": data[0], "base64": data[1], "downloads": data[2],
               "genres": data[3].split(","), "URL": data[4],
               "screenshots_url": data[5], "description": data[6],
               "rating": data[7].upper(), "compile_type": data[8].lower(),
               "joined": data[9], "in_pack_man": data[10]}
        return_data[length] = copy.deepcopy(add)
        length+=1
    return return_data

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
    return data



# Looking at an individual game
@app.route("/games/<name>")
def view_game(name):
    db = sql.connect(settings["db_name"])
    data = db.execute("SELECT * FROM games WHERE name='%s'" % (name)).fetchall()
    data = format_data(data)
    del data[0]["URL"]
    del data[0]["base64"]
    del data[0]["in_pack_man"]
    return data[0]


# Download game
@app.route("/games/<name>/download")
def download_game(name):
    db = sql.connect(settings["db_name"])
    data = db.execute("SELECT * FROM games WHERE name='%s'" % (name))
    return_data = format_data(data.fetchall())
    db.execute("UPDATE games SET downloads = %s WHERE base64 = '%s'" % (return_data[0]["downloads"] + 1, return_data[0]["base64"]))
    db.commit()
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
                if ((tag in data[game]["genres"]) or (tag == data[game]["rating"]) or (tag == data[game]["compile_type"])):
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
    # return_data = json.dumps(return_data, indent=1)
    return return_data
