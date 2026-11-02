# Code Cleaner

[English](README.md) | [简体中文](README.zh-CN.md) | **日本語**

人の判断を尊重する AI コードレビュー：**既定では読み取り専用。根拠を示し、許可された範囲で変更します。**

Code Cleaner は、インストール可能な Agent Skill と、単独でも使える Python コマンドラインツールです。Python、JavaScript / TypeScript（JSX・TSX を含む）、Java に対応しています。実行には Python 3.10 以降と標準ライブラリのみが必要です。

[CLI リファレンス](references/cli.ja.md) · [貢献ガイド](CONTRIBUTING.ja.md) · [変更履歴](CHANGELOG.ja.md) · [MIT ライセンス](LICENSE)

## 主な機能

- **プロジェクト構造の確認**：ファイルの行数、ディレクトリの深さ、定義数、空ファイル、空白を含むファイル名を確認します。Java / React の大文字を使うファイル名や、空の `__init__.py` は削除候補にしません。
- **未使用コードの候補検出**：Python は AST とシンボルテーブルで import のスコープとトップレベル定義を分析します。JS/TS/Java はヒューリスティックな import・参照分析を使います。
- **重複コードの候補検出**：行の順序を保つ正規化済みスライディングウィンドウで、長いコードに含まれる重複部分も探します。インデックスによる候補の絞り込みと、比較回数・結果数の上限設定に対応しています。
- **統一レポート**：元の行番号、ルール ID、重大度、確信度、修正案を JSON / Markdown で出力します。
- **プロジェクトごとの設定**：`.codecleaner.json`、`.codecleanerignore`、CLI オプションに対応しています。
- **CI 連携**：失敗とする重大度を指定でき、読み取り・構文エラーや結果の打ち切りを明示します。
- **復旧可能なインストール**：コピー元とインストール先の重複確認、ドライラン、明示的な上書き、ステージング、バックアップ、失敗時の復元に対応しています。

スクリプトは構造・未使用コード・重複コードの確認を補助します。コードの不適切な設計、セキュリティ、性能は、AI または人が文脈を読んで判断します。スキャナーはソースを変更せず、対象コードを実行せず、ネットワークにも接続しません。

## クイックスタート

リポジトリをクローンし、プロジェクトのルートで実行します。

```bash
git clone https://github.com/AssUt11/code-cleaner.git
cd code-cleaner
python scripts/run_review.py /path/to/project --format markdown
python scripts/run_review.py /path/to/project --format json --output report.json
```

空白を含む Windows のパスは引用符で囲んでください。

```powershell
python scripts/run_review.py "D:\My Project" --format markdown
```

AI アシスタントへの依頼例：

```text
code-cleaner でこのプロジェクトを確認してください。まず読み取り専用のレポートを作り、影響の大きい順に並べてください。
generated ディレクトリを除外して、未使用コードと重複コードを探してください。
確認済みの問題を修正し、公開 API を維持して、関連するテストを実行してください。
```

## Skill としてインストール

```bash
python install.py codex --dry-run
python install.py codex
python install.py claude workbuddy
python install.py --all
```

| 対象 | 既定の親ディレクトリ |
|---|---|
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |

指定した親ディレクトリの下に `code-cleaner/` を作成します。Skill の検出と読み込みは各クライアントの対応状況によります。メタデータには [Agent Skills 仕様](https://agentskills.io/specification)の `name`、`description`、`license`、`metadata` を使用しています。

シンボリックリンクを優先し、権限がない場合はコピーに切り替えます。リンクでのインストールは元ディレクトリの更新に追従します。コピーした場合は再インストールが必要です。既存のインストール先を置き換えるには明示的な指定が必要です。

```bash
python install.py codex --force
python install.py --target /custom/skills --no-symlink --dry-run
```

`--force` は同じ親ディレクトリに `.code-cleaner.backup-TIMESTAMP-ID` というバックアップを残します。復元するには、現在の `code-cleaner` を別の場所に移してから、バックアップを `code-cleaner` に改名してください。バックアップがリンクの場合は、リンク先の元ディレクトリも保持してください。コピー元そのものや、親子関係が重なる場所へのインストールは拒否します。

## 設定と除外ルール

`.codecleaner.example.json` を、確認対象プロジェクトのルートに `.codecleaner.json` としてコピーし、必要に応じて調整してください。統一スキャナーが自動で読み込みます。

```json
{
  "checks": ["structure", "dead", "duplicates"],
  "exclude": ["generated/*", "*.min.js"],
  "max_lines": 500,
  "max_depth": 6,
  "min_lines": 6,
  "threshold": 0.85,
  "max_comparisons": 50000,
  "max_findings": 200
}
```

`.codecleanerignore` に相対パスの glob を 1 行ずつ記述することもできます。`#` で始まる行はコメントです。`!` による除外の取り消しは未対応で、`.gitignore` は自動で読み込みません。CLI の単一値オプションは JSON の値を上書きし、`--exclude` は設定済みのリストに追加されます。依存ライブラリ、隠しディレクトリ、`.workbuddy/`、仮想環境、ビルド成果物、リンクは既定で除外します。

## CI と終了コード

```bash
python scripts/run_review.py /path/to/project --checks structure,dead --fail-on warning
```

| 終了コード | 意味 |
|---|---|
| `0` | スキャンが完了し、失敗とする重大度に達していません。既定の `--fail-on none` は候補があっても成功します。 |
| `1` | スキャンが完了し、指定した失敗基準に達する候補が見つかりました。 |
| `2` | 引数・設定・出力のエラー、または解析失敗や結果の打ち切りを含む不完全なスキャンです。 |

`--fail-on info` は全重大度、`warning` は warning / error、`error` は error のみを対象にします。現在の組み込みルールは主に warning / info を出力します。重大なセキュリティ問題は人または AI による確認が必要です。CI では統一エントリーポイントを使ってください。個別スキャナーは候補を JSON で出力します。

GitHub Actions は Ubuntu / Windows と Python 3.10 / 3.14 を対象にしています。[CI の実行結果を見る](https://github.com/AssUt11/code-cleaner/actions)。

## 制約

- 検出結果は候補です。**自動修正や自動削除のコマンドはありません。** import の副作用、公開 API、リフレクション、プラグイン登録、別リポジトリからの呼び出しは、静的な参照数だけでは判断できません。
- Python のクラスメソッド、ネストした定義、デコレーター付きの入口は未使用定義の候補から除外します。動的なエクスポートや文字列内の参照では誤判定が残る場合があります。
- JS/TS/Java は完全なコンパイラー解析ではありません。モジュールの別名、完全なスコープ、フレームワークの規約、CommonJS、動的 import の対応には制限があります。
- 重複検出は行順を保ち、文字列と数値を正規化します。近似一致には隣接する正規化済みの行が共通している必要があり、意味的に似たコードをすべて検出するものではありません。
- インデックスを使っても、繰り返しの多いプロジェクトでの最悪ケースは解消できません。上限に達すると、取得済みの結果、`complete: false`、終了コード `2` を返します。対象範囲を絞るか上限を調整してください。
- Python のエンコーディング宣言と UTF-8 BOM に対応します。他の言語は UTF-8 として読み込み、読み取り失敗は診断情報に表示します。

## 開発とリリース

```bash
python -B -m unittest discover -s tests -v
python -B tools/validate_skill.py
python -B tools/package_release.py --output ../code-cleaner.zip
```

検証ツールはメタデータ、バージョンの整合性、ローカル文書へのリンクを確認します。パッケージ作成時にも検証し、`code-cleaner/` を最上位ディレクトリとする ZIP を生成します。Git メタデータ、キャッシュ、依存ライブラリ、既存の ZIP、`.workbuddy/` は除外します。ソース、テスト、`.github/` の設定は含まれます。

フォークを公開する場合は、`.github/` や `.gitignore` などの隠しファイルも含めて、このディレクトリの内容をリポジトリのルートに配置してください。ZIP は必要に応じて Release に添付できます。ZIP だけをアップロードしても、ソースの CI は実行されません。

## ディレクトリ構成

```text
code-cleaner/
├── README*.md               # 英語・簡体字中国語・日本語の文書
├── SKILL.md                 # AI の作業手順と対象範囲の保護
├── install.py               # 対応クライアント向けインストーラー
├── scripts/                 # 統一 CLI、3 種のスキャナー、共通処理
├── references/              # CLI、コードの問題、言語規約、セキュリティ・性能
├── assets/                  # レポートのテンプレート
├── agents/openai.yaml       # Codex の UI メタデータ
├── tests/                   # 動作の回帰テスト
├── tools/                   # リリース検証とパッケージ作成
└── .github/                 # CI、Issue・PR テンプレート
```

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
