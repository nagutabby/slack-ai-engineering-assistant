# Slack AI Engineering Assistant

このプロジェクトは、LM Studio上で動作するLLM（Gemma 4 26B A4B）をバックエンドとして使用し、Slack上で最新情報の検索やウェブページの精査ができるエンジニアリング・アシスタント・ボットです。

## 🌟 主な機能

* **最新情報の検索**: DuckDuckGo検索を利用し、LLMの学習データに含まれない最新情報を取得します。
* **ウェブサイトの精査**: 検索結果や指定されたURLの内容をスクレイピングし、詳細なコンテキストを読み取ります。
* **スレッドコンテキストの維持**: Slackのスレッド内での会話履歴を読み取り、文脈に沿った対話が可能です。

## 📋 前提条件

### 1. LM Studioのセットアップ

このボットを動作させるには、LM Studioでモデルがロードされ、サーバーが起動している必要があります。

1. LM Studio のインストール: [LM Studio公式サイト](https://lmstudio.ai/)からアプリをダウンロードしてインストールします。
2. モデルの検索とダウンロード:
    * LM Studio内の「Search」タブで "Gemma 4 26B A4B" を検索します。
    * 適切な量子化バリアントを選択してダウンロードしてください。
3. モデルのロード:
    * 「AI Chat」または「Local Server」セクションで、ダウンロードした Gemma 4 26B A4B を選択してロードします。
4. Local Server の起動:
    * 「Local Server」タブ（左側の ↔️ アイコン）を開きます。
    * Server Port がデフォルトの 1234 であることを確認します。
    * "Start Server" ボタンをクリックします。

### 2. Slackアプリの設定

1. [Slack API](https://api.slack.com/apps)で新しいアプリを作成します。
2. Socket Mode を有効にします。
3. Event Subscriptions で app_mention イベントを購読します。
4. 以下のスコープを Bot Token Scopes に追加します：
    * app_mentions:read
    * chat:write
    * channels:history
    * groups:history
    * im:history
    * mpim:history
5. SLACK_BOT_TOKEN (xoxb-) と SLACK_APP_TOKEN (xapp-) を取得します。

### 3. pyenvのインストール
Pythonのバージョンを管理するため、[pyenv](https://github.com/pyenv/pyenv)をインストールします。

### 4. Poetryのインストール
ライブラリのバージョンを管理するため、[Poetry](https://github.com/python-poetry/poetry)をインストールします。

---

## 🚀 インストールと実行

### 1. 依存関係のインストール

```
pyenv install
poetry install
```

### 2. 環境変数の設定

プロジェクトのルートディレクトリに .env ファイルを作成し、以下の情報を記入します。

```
SLACK_BOT_TOKEN=<xoxb-your-bot-token>
SLACK_APP_TOKEN=<xapp-your-app-token>
MODEL_ID=google/gemma-4-26b-a4b
```

### 3. ボットの起動

LM Studioのサーバーが起動していることを確認してから、以下のコマンドを実行します。

```
poetry run python bot.py
```

---

## 🛠 ツール構成

ボットは必要に応じて以下の関数を自律的に呼び出します。

| 関数名 | 内容 |
| :--- | :--- |
| search_web | インターネットで最新情報を検索します。 |
| visit_website | 指定されたURLにアクセスしてテキスト内容を抽出します。詳細なドキュメント確認や記事の精査に使用します。 |
