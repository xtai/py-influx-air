#!/bin/bash

if [ ! -f .env.installed ]; then
    cp .env.example .env.installed
fi

cp ./py-influx-air.service /lib/systemd/system/
chmod 644 /lib/systemd/system/py-influx-air.service

systemctl disable py-influx-air.service

systemctl daemon-reload
systemctl enable py-influx-air.service
systemctl start py-influx-air.service
