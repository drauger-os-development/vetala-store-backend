#!/bin/bash
echo "Removing files and disabling. . ."
sudo systemctl disable store_backend
sudo rm -fv /etc/nginx/sites-available/store_backend.conf /etc/nginx/sites-enabled/store_backend.conf /etc/systemd/system/store_backend.service
sudo systemctl restart nginx
