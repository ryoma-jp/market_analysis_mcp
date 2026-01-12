# 技術動向調査エージェント（Market Analysis MCP）: ユーザマニュアル

このプロジェクトは、業界/技術動向調査のための **MCP stdioツールサーバ** を提供します。
既存のツール実装を、公式MCP（Python SDK）として公開し、Copilot Chat（Agent/Tools）などのMCPクライアントから呼び出せます。

補足:
- 公式MCP stdioサーバ入口: `python -m src.mcp_server`
- 旧 `python -m src.main` は開発用途の最小NDJSONプロトコルで、MCPクライアントとは互換ではありません。

## できること
- Webページを取得し（allowlistで制限可能）、HTMLを返す
- HTMLから本文テキストを抽出（readabilityベース）
- 主張（claims）ごとの根拠抜粋（1件最大500文字）を生成
- 参照ソース一覧（JSON）やレポート（Markdown）をファイルに保存

## 前提条件
- OS: Linux / macOS / Windows（WSL可）
- Python: 3.12 推奨（CIで使用）
- ネットワーク: `fetch_url` を使う場合は外部Webアクセスが必要

## インストール

このプロジェクトはDockerでの実行/テストをサポートしています。運用・再現性の観点から、まずはDocker利用を推奨します。

### Docker（推奨）

#### テスト実行

`env/Dockerfile.test` は `pytest -q` を実行するイメージです。

```bash
docker build -f env/Dockerfile.test -t market-analysis-mcp-test .
docker run --rm market-analysis-mcp-test
```

#### サーバ起動（stdio）

`env/Dockerfile` は実行環境を用意するイメージです（ENTRYPOINTは固定していないため、起動コマンドは `docker run` 側で指定します）。

```bash
docker build -f env/Dockerfile -t market-analysis-mcp .
docker run --rm -i market-analysis-mcp python -m src.mcp_server
```

> stdioサーバなので、`-i`（stdinを開く）を付けて入力できるようにします。

### Python（ローカル実行・任意）

1) 依存関係をインストールします。

```bash
pip install -r env/requirements.txt
```

2) 開発・テスト用途（任意）

```bash
pip install -r env/requirements-dev.txt
```

## 設定（config）

設定はYAMLで、既定の読み込み先は `env/config.yaml` です。

- 参照順序
	- `APP_CONFIG` 環境変数があればそのパス
	- それ以外は `env/config.yaml`
	- ファイルが無い場合はデフォルト値

### 設定ファイルを作成

```bash
cp env/config.example.yaml env/config.yaml
```

### 主な設定項目

#### `http.*`
- `user_agent`: 取得時のUser-Agent
- `timeout_seconds`: タイムアウト（秒）
- `max_content_length`: 最大取得サイズ（bytes）。超えると中断します
- `allow_domains`: 許可するドメインの末尾一致allowlist。`null` または未設定なら制限なし

#### `paths.*`
- `reports_dir`: レポートの既定保存先ディレクトリ名
- `sources_dir`: ソース一覧の既定保存先ディレクトリ名

#### `excerpts.*`
- `max_chars`: 抜粋の最大文字数（既定 500）
- `default_position`: 位置情報が取れない場合の既定文字列

## サーバ起動（stdio）

リポジトリルートで次を実行します。

```bash
python -m src.mcp_server
```

このプロセスはMCPクライアント（Copilot Chat等）から接続され、ツールがMCP経由で実行されます。

> 旧NDJSONプロトコル（`python -m src.main`）は下記に残しています（開発・デバッグ用途）。

## サーバの終了方法

stdioサーバのため、終了方法は「入力の終了」または「プロセスの停止」です。

- 対話的に起動している場合（待ち受けループ中）
	- `Ctrl+C` で終了します。
	- もしくは `Ctrl+D`（EOF）で標準入力を閉じると終了します。
- 1回の呼び出しで `printf ... | python -m src.main` のようにパイプ実行している場合
	- 入力がEOFになると自動的に終了します（追加操作は不要です）。
- Dockerで起動している場合
	- `docker run --rm -i ...` のターミナルで `Ctrl+C` するとコンテナが停止します。
	- 別ターミナルから止める場合は `docker stop <container_id>` を使用します。

## 利用方法（旧NDJSONプロトコル / 開発用）

### 1. ツール一覧の取得

入力:

```json
{"action":"list_tools"}
```

出力（例）:

```json
{"ok":true,"result":{"tools":["fetch_url","extract_main_text","extract_evidence_quotes","save_sources","save_report"]}}
```

### 2. ツールの呼び出し

入力フォーマット:

```json
{"action":"invoke","tool":"<tool_name>","params":{...}}
```

出力フォーマット:
- 成功: `{"ok": true, "result": ...}`
- 失敗: `{"ok": false, "error": "..."}`

## ツール仕様

### `fetch_url`

目的: URLを取得してHTMLを返します（allowlist/サイズ制限あり）。

- params
	- `url` (string, required)
- result（主なフィールド）
	- `final_url` (string)
	- `status_code` (int)
	- `fetched_at` (string; ISO 8601)
	- `content_type` (string|null)
	- `html` (string)

例（bash）:

```bash
printf '%s\n' '{"action":"invoke","tool":"fetch_url","params":{"url":"https://example.com"}}' \
	| python -m src.main
```

### `extract_main_text`

目的: HTMLから本文テキストとメタ情報を抽出します。

- params
	- `html` (string, required)
	- `base_url` (string, optional) - publisher推定に利用
- result
	- `title` (string|null)
	- `main_text` (string)
	- `published_date` (string|null)
	- `publisher` (string|null)

### `extract_evidence_quotes`

目的: claims（主張）ごとに根拠抜粋を返します。

- params
	- `text` (string, required)
	- `claims` (string[], optional; 省略時は空配列)
- result: 配列
	- `claim` (string)
	- `excerpt` (string) - 最大 `excerpts.max_chars` 文字
	- `position` (string) - `chars <start>-<end>` など

注意:
- 抜粋はヒューリスティックです（厳密な引用や意味検索ではありません）。
- 1件あたり最大500文字（既定）を超えないよう制限します。

### `save_sources`

目的: ソース情報の配列をJSONとして保存します。

- params
	- `records` (object[], required)
	- `output_path` (string, required)

`records` の各要素（主な項目）:
- `url` (string)
- `final_url` (string|null)
- `fetched_at` (string; ISO 8601)
- `title` (string|null)
- `publisher` (string|null)
- `published_date` (string|null)
- `category` (string|null)
- `confidence` (string|null)

result:
- `path` (string)

### `save_report`

目的: Markdownテキストを指定パスに保存します。

- params
	- `markdown_text` (string, required)
	- `output_path` (string, required)
- result
	- `path` (string)

## 代表的な利用フロー

1) `fetch_url` でHTML取得
2) `extract_main_text` で本文抽出
3) `extract_evidence_quotes` でclaimsごとの根拠抜粋
4) `save_sources` / `save_report` で成果物保存

実運用では「取得したURL・取得日時・タイトル・publisher・published_date」などを `save_sources` に集約し、レポート本文は `save_report` に保存する構成を推奨します。

## 成果物（ファイル出力）

- `reports/` と `sources/` は成果物の保存先として想定されています（`.gitignore` 対象）。
- 保存先パスはツール呼び出し側で `output_path` として明示してください。

## セキュリティ・コンプライアンス注意

- `allow_domains` を使い、想定外ドメインへのアクセスを制限してください。
- 外部サイトの利用規約・robots.txt・著作権に配慮してください。
- レポートに含める根拠抜粋は最大500文字に制限されています。

## トラブルシューティング

- `Domain not allowed by allowlist`: `http.allow_domains` を見直してください（未設定なら制限なし）。
- `Content too large; aborted`: `http.max_content_length` を増やすか、対象URLを変更してください。
- `JSONDecodeError` / `unknown action`: 1行1JSONになっているか、`action` が正しいか確認してください。
- タイムアウト: `http.timeout_seconds` を調整してください。

## 開発者向け（任意）

テスト実行:

```bash
pytest
```

主なエントリ:
- `python -m src.main`（stdioサーバ）
- `src/server.py`（ツール実装本体）
