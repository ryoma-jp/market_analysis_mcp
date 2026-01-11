# market_analysis_mcp

業界/技術動向調査を行うための **MCPサーバ（開発用の最小stdio実装）** です。
Web取得・本文抽出・根拠抜粋・成果物保存のツール群を提供し、エージェント（例: GitHub Copilot のカスタムエージェント）から呼び出すことを想定しています。

> 現時点では「MCPフレームワークそのもの」ではなく、置き換え可能な最小のstdio NDJSONプロトコル実装です。

## QuickStart（Docker推奨）

### 1) テスト実行

```bash
docker build -f env/Dockerfile.test -t market-analysis-mcp-test .
docker run --rm market-analysis-mcp-test
```

### 2) サーバ起動（stdio）

```bash
docker build -f env/Dockerfile -t market-analysis-mcp .
docker run --rm -i market-analysis-mcp python -m src.main
```

終了方法:
- 対話的に起動している場合は `Ctrl+C`（または `Ctrl+D` でEOF）で終了します。
- パイプで1回呼び出す形（例: `printf ... | docker run ...`）は入力終了で自動的に終了します。

別ターミナルから疎通確認（例）:

```bash
printf '%s\n' '{"action":"list_tools"}' | docker run --rm -i market-analysis-mcp python -m src.main
```

## 設定（config）

設定は `env/config.yaml`（YAML）を参照します。まずは例をコピーして編集してください。

```bash
cp env/config.example.yaml env/config.yaml
```

主な設定例:
- `http.allow_domains`: 取得を許可するドメインallowlist（末尾一致）
- `http.timeout_seconds`: タイムアウト
- `http.max_content_length`: 最大取得サイズ（bytes）

詳細はユーザマニュアルを参照してください。

## ドキュメント

- ユーザ向け手順: `docs/manual/user_manual.md`
- 開発/設計ドキュメント: `docs/design/`
	- まず読む順番の目安: `docs/design/README.md`

## プロジェクト構成

- `docs/design/`
	- 開発関連の情報（要件、設計、推奨プロセス、テスト仕様）を集約します。
- `docs/manual/`
	- 利用者向けの手順・使い方（起動、設定、ツール仕様、トラブルシュート）を配置します。
- `env/`
	- 開発環境/実行環境関連のファイルを集約します（Dockerfile、requirements、config例など）。
- `src/`
	- サーバ本体・ツール実装のソースコードを集約します。
	- 例: `src/main.py`（stdioサーバ入口）, `src/server.py`（ツール実装）, `src/config.py`（設定読み込み）
- `tests/`
	- テストコードを集約します（ユニットテスト、stdioプロトコルの簡易統合テスト）。

## ライセンス

See `LICENSE`.