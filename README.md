# Discord Bot Virtual CMD - Production

ブラウザ内の見た目だけのCMDではありません。

`ttyd` のWebターミナルから、Dockerコンテナ内部の本物のbash/PTYを操作します。
Node.js / Python / npm / pip / git / nano などを実際に実行できます。

Discord Botは `supervisor` が別プロセスとして管理するため、
ブラウザを閉じてもBotは停止しません。Botが異常終了すると自動再起動します。

## 仕組み

Windows
  -> Docker Desktop
    -> 隔離コンテナ
       -> ttyd Web Terminal (xterm.js)
       -> supervisor
          -> Discord Bot

ホストのDockerソケット、C:\ ドライブ全体、管理者権限はコンテナへ渡していません。

## 初回起動

1. ZIPを展開
2. `setup.bat`
3. `start.bat`
4. ブラウザで `http://127.0.0.1:7681`

`setup.bat` はWeb CMD用のランダムパスワードを自動生成します。

確認:
`show-login.bat`

## Botを入れる

`workspace\bot\`

へ実際のBotファイルを置きます。

### Node.js Bot

Web CMD:

```text
C:\VirtualBot\workspace> cd bot
C:\VirtualBot\bot> npm install
```

`workspace\bot.config`:

```text
BOT_WORKDIR=/workspace/bot
BOT_COMMAND=node bot.js
```

Bot再起動:

```text
botctl restart
botctl status
```

### Python Bot

Web CMD:

```text
C:\VirtualBot\workspace> cd bot
C:\VirtualBot\bot> pip install -r requirements.txt
```

内部のPython venv (`/workspace/.venv`) がPATHへ自動追加されます。

`workspace\bot.config`:

```text
BOT_WORKDIR=/workspace/bot
BOT_COMMAND=python bot.py
```

## Bot環境変数

`workspace\.env` を編集します。

```env
DISCORD_TOKEN=...
CLIENT_ID=...
GUILD_ID=...
```

Bot起動時にこのファイルを環境変数として読み込みます。

## Web CMDコマンド

```text
dir
cd bot
cls
type FILE
copy SRC DEST
ren SRC DEST
del FILE
where node

node -v
npm -v
python --version
pip --version
git --version
nano FILE
```

Linuxコンテナのbashが実体ですが、よく使うWindows CMD風コマンドを追加しています。

## Bot管理

```text
botctl status
botctl start
botctl stop
botctl restart
botctl logs
botctl errors
botctl config
botctl help
```

`botctl logs` は Ctrl+C でログ表示だけを終了できます。Bot本体は停止しません。

## 24時間稼働

Dockerサービス:
`restart: unless-stopped`

Botプロセス:
`supervisor autorestart=true`

そのため、Botクラッシュ時は自動再起動します。
Dockerコンテナ自体が落ちた場合もDockerが再起動します。

ただしPCの電源OFF・スリープ中は動きません。
完全な24/7にはVPS等の常時稼働マシンで同じDocker Composeを動かしてください。

## 省負荷設定

初期値:

- CPU上限: 0.50 CPU
- メモリ上限: 768 MB
- PID上限: 192
- `/tmp`: 128 MB
- Botログ: ローテーション
- 高頻度ポーリングなし

必要なら `docker-compose.yml` の `cpus` / `mem_limit` を変更できます。

## 隔離

初期構成では:

- Web公開: `127.0.0.1:7681` のみ
- Basic認証あり
- `no-new-privileges`
- Linux capabilities: ALL drop
- Docker socket: マウントしない
- ホスト側は `workspace` フォルダーだけ共有

## 外部公開について

そのままインターネットへポート公開しないでください。
外部利用する場合はTLS・追加認証・アクセス制限を置いてください。

## ファイル

- `Dockerfile` — 仮想CMD環境
- `docker-compose.yml` — 隔離・負荷制限
- `runtime/` — ttyd / supervisor / botctl
- `workspace/bot/` — 実際のBot
- `workspace/.env` — Bot環境変数
- `workspace/bot.config` — Bot起動コマンド
- `setup.bat` — 初回構築
- `start.bat` — 起動
- `stop.bat` — 停止
- `restart.bat` — 再起動
- `open.bat` — Web CMDを開く
- `show-login.bat` — Web CMDログイン確認


# v2: Bot Upload + 24H Auto Run

## ブラウザからBotをアップロード

起動後:

```text
http://127.0.0.1:7682
```

Virtual CMDと同じユーザー名・パスワードでログインします。

アップロード画面では:

- 複数ファイル
- ZIP
- Chrome / Edgeのフォルダー選択
- ZIP自動展開
- 起動コマンド自動検出
- npm install
- pip install -r requirements.txt
- 完了後Bot再起動

に対応します。

アップロードされたファイルは実際に:

```text
/workspace/bot
```

へ保存され、Windows側では:

```text
workspace\bot
```

に残ります。

## CMD追加コマンド

```text
botctl detect
botctl install
botctl ready
botctl install-logs
botctl upload-url
```

Botファイルを配置した後、

```text
botctl ready
```

で起動ファイル検出 → 依存関係導入 → Bot再起動 → 状態確認まで実行できます。

## 24時間稼働

- Discord Bot: Supervisorの `autorestart=true`
- Web Terminal: Supervisorで自動復旧
- Upload Server: Supervisorで自動復旧
- Dockerコンテナ: `restart: unless-stopped`
- ブラウザを閉じてもBotは継続

PCの電源OFFまたはスリープ中は動作しません。
PC起動時にDocker Desktopも自動起動する設定にすると、コンテナも復帰しやすくなります。


# v3: Environment Variable Manager

## Web画面

Bot Upload画面の「環境変数」から:

- 環境変数を追加
- 同じ名前の環境変数を上書き
- 環境変数を削除
- Botを再起動して反映

できます。

保存先:

```text
/workspace/.env
```

Windows側:

```text
workspace\.env
```

一覧では値を表示せず、変数名だけ表示します。

## CMD

```text
botctl env-list
botctl env-set DISCORD_TOKEN
botctl env-del GUILD_ID
botctl env-restart
```

`env-set` は値を画面に表示しない入力方式です。

例:

```text
C:\VirtualBot\workspace> botctl env-set DISCORD_TOKEN
DISCORD_TOKEN の値:
DISCORD_TOKEN を保存しました。Bot再起動後に反映されます。

C:\VirtualBot\workspace> botctl env-restart
```

`botctl env-list` は:

```text
CLIENT_ID=<hidden>
DISCORD_TOKEN=<hidden>
GUILD_ID=<hidden>
```

のように秘密値を隠して表示します。
