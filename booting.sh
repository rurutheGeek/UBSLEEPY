#!/bin/sh

#start_app.serviceで実行されるスクリプトファイル
#sudo systemctl enable start_app.serviceで有効化

echo ...Bot booting...
cd /home/ruru/UBSLEEPY
git --git-dir=.git pull origin main
nohup python3 /home/ruru/UBSLEEPY/main.py &
nohup /home/ruru/actions-runner/run.sh &
exit 0