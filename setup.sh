#!/bin/bash
# -*- coding: utf-8 -*-
#
#  setup.sh
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
set -Ee
set -o pipefail
port="$1"
if [ "$port" == "" ]; then
	port="80"
fi
echo "Installing Dependencies . . ."
sudo apt install --assume-yes $(<requirements.txt)
username=$(whoami)
echo "Configuring your system . . ."
sudo cp -v store_backend.nginx_conf /etc/nginx/sites-available/store_backend.conf
sudo cp -v store_backend.service /etc/systemd/system/store_backend.service
sudo sed -i "s:<path to>:$PWD:g" /etc/nginx/sites-available/store_backend.conf
sudo sed -i "s:<port>:$port:g" /etc/nginx/sites-available/store_backend.conf
sudo sed -i "s:<path to>:$PWD:g" /etc/systemd/system/store_backend.service
sudo sed -i "s:<username>:$username:g" /etc/systemd/system/store_backend.service

# Only bother trying to delete this file if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
	echo "Disabling default site . . ."
	sudo rm -fv /etc/nginx/sites-enabled/default
fi

echo "Enabling site and restarting Nginx . . ."
sudo systemctl enable store_backend
sudo ln -sv /etc/nginx/sites-available/store_backend.conf /etc/nginx/sites-enabled/store_backend.conf
sudo systemctl restart nginx
sudo systemctl start store_backend
git log | grep "^commit " | head -n1 | awk '{print $2}' > .git_commit_number
echo "Please ensure port $port is open so that the Vetala Store Backend may be exposed to the network"
