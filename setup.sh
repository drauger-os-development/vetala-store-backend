#!/bin/bash
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
echo "Disabling default site . . ."
sudo rm -fv /etc/nginx/sites-enabled/default
echo "Enabling site and restarting Nginx . . ."
sudo systemctl enable store_backend
sudo ln -sv /etc/nginx/sites-available/store_backend.conf /etc/nginx/sites-enabled/store_backend.conf
sudo systemctl restart nginx
echo "Please open port 80 so that Download Optimizer may be exposed to the network"
