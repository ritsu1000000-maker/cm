#!/usr/bin/env bash
set -euo pipefail

mkdir -p /workspace/.botbox/logs /workspace/bot

# Python Botでpipを使いやすくするための、コンテナ内部用venv。
# Web CMDそのものの隔離はDockerで行われます。
if [ ! -x /workspace/.venv/bin/python ]; then
  python3 -m venv /workspace/.venv >/dev/null 2>&1 || true
fi

# Webターミナルのbash設定を生成。
cat > "$HOME/.bashrc" <<'EOF'
export TERM=xterm-256color
export PATH="/workspace/.venv/bin:$PATH"

cd /workspace 2>/dev/null || true

# Windows CMD風の補助コマンド
alias cls='clear'
alias py='python'
alias copy='cp'
alias ren='mv'
alias where='command -v'

type() {
  if [ "$#" -eq 0 ]; then
    builtin type
  else
    cat -- "$@"
  fi
}

del() {
  rm -- "$@"
}

bothelp() {
  cat <<'HELP'
Virtual CMD commands
--------------------
dir                      ファイル一覧
cd bot                   Botフォルダーへ移動
cls                      画面クリア
type FILE                ファイル表示
copy SRC DEST            コピー
ren SRC DEST             名前変更
del FILE                 削除
where node               コマンド場所確認
node -v                  Node.js確認
python --version         Python確認
npm install              Node依存関係インストール
pip install -r requirements.txt
botctl status            Bot状態
botctl start             Bot起動
botctl stop              Bot停止
botctl restart           Bot再起動
botctl logs              Botログ
botctl errors            Botエラーログ
botctl config            Bot起動設定表示
botctl help              Bot管理ヘルプ
HELP
}

# CMD風の表示。実体はDocker内のbashです。
export PS1='C:\VirtualBot\$(basename "$PWD")> '
EOF

exec /usr/bin/supervisord -c /opt/botbox/supervisord.conf
