ここに実際のDiscord Botを入れてください。

Node.js:
  1. bot.js / package.json などをこのフォルダーへ配置
  2. Web CMDで:
       cd bot
       npm install
  3. /workspace/bot.config:
       BOT_COMMAND=node bot.js
  4. botctl restart

Python:
  1. bot.py / requirements.txt を配置
  2. Web CMDで:
       cd bot
       pip install -r requirements.txt
  3. /workspace/bot.config:
       BOT_COMMAND=python bot.py
  4. botctl restart
