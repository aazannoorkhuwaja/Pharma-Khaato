#!/bin/bash

# A simple script to manage XAMPP on Ubuntu

# Check if the user provided an action
if [ -z "$1" ]; then
    echo "Usage: ./xampp.sh [start | stop | restart | gui]"
    exit 1
fi

ACTION=$1

# Run the correct XAMPP command based on user input
if [ "$ACTION" == "start" ]; then
    echo "Starting XAMPP server..."
    sudo /opt/lampp/lampp start
    sudo /opt/lampp/bin/mysql -u root -p


elif [ "$ACTION" == "stop" ]; then
    echo "Stopping XAMPP server..."
    sudo /opt/lampp/lampp stop

elif [ "$ACTION" == "restart" ]; then
    echo "Restarting XAMPP server..."
    sudo /opt/lampp/lampp restart

elif [ "$ACTION" == "gui" ]; then
    echo "Opening XAMPP Control Panel..."
    sudo /opt/lampp/manager-linux-x64.run

else
    echo "Invalid option! Use: start, stop, restart, or gui"
fi
