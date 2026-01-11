# テスト仕様（MVP）

対象: MCPサーバ（stdio）向けツール実装（`src/server.py`, `src/main.py`, `src/config.py`）

## 目的
- ツールの入出力とポリシー（allowlist、抜粋最大500文字、位置情報の扱い）が壊れていないことを自動で検証する
- ネットワークや外部サイトの状態に依存せずに、ローカルで再現可能なテストにする

## スコープ
### ユニットテスト（必須）
- `fetch_url`
  - allowlistによりブロック/許可される
  - 戻り値に `final_url` / `status_code` / `fetched_at` / `content_type` / `html` を含む
  - `max_content_length` 超過で失敗する
  - ネットワーク呼び出しはmockする（実通信しない）

- `extract_main_text`
  - HTMLから `title` と本文が抽出できる
  - `publisher` が `og:site_name` もしくは host から推定できる

- `extract_evidence_quotes`
  - 抜粋が最大500文字（設定値）を超えない
  - 位置情報が付与される（該当箇所が見つからない場合は `unknown` を返す）

- `save_sources` / `save_report`
  - 指定パスにファイルが作られる
  - `save_sources` はJSONとして読み戻せる

### インテグレーションテスト（推奨）
- `src/main.py` のstdio NDJSONプロトコル
  - `{"action":"list_tools"}` で tool list が返る
  - エラー時に `{"ok":false,"error":...}` になる
  - ※外部通信が絡む `fetch_url` の invoke はmock or list_toolsのみで十分

## 前提/制約
- 外部ネットワークへは接続しない（CIや社内環境での安定性のため）
- 抜粋の上限は `docs/design/agent_spec.md` のポリシー（最大500文字）に従う

## 合格基準
- 全テストが `pytest` で成功
- “壊れやすい条件”が最低限担保される
  - URLログ保存が可能
  - 抜粋の最大500文字制限
  - 位置情報が `unknown` で明示できる

## 実行方法（想定）
- ローカル: `python -m pytest -q`
- Docker:
  - `docker build -t market-analysis-test -f env/Dockerfile.test .`
  - `docker run --rm market-analysis-test`
