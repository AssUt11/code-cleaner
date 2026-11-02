# CLI リファレンス

[English](cli.md) | [简体中文](cli.zh-CN.md) | **日本語**

Python 3.10 以降が必要です。外部の実行用ライブラリは不要です。スキャナーは読み取り専用で、プロジェクトのコードを実行しません。以下のコマンドは Skill のルートで実行します。

## 統一スキャナー

```bash
python scripts/run_review.py PROJECT [OPTIONS]
```

| オプション | 既定値 | 説明 |
|---|---|---|
| `--checks` | `structure,dead,duplicates` | 確認項目をカンマ区切りで指定 |
| `--format` | `json` | `json` / `markdown` |
| `--output PATH` | 標準出力 | レポートの明示的な出力先。親ディレクトリは作成済みである必要があります |
| `--config PATH` | 存在する場合は `PROJECT/.codecleaner.json` | JSON 設定。不明なフィールドや不正な型はエラーになります |
| `--exclude GLOB` | 追加ルールなし | 複数指定可能。設定済みの除外リストに追加します |
| `--max-lines` | `500` | ファイル行数のしきい値。正の整数 |
| `--max-depth` | `6` | 相対ディレクトリの深さのしきい値。0 以上の整数 |
| `--min-lines` | `6` | 重複ウィンドウの正規化済みコード行数。2 以上 |
| `--threshold` | `0.85` | 順序付きウィンドウの類似度しきい値。`[0.5, 1]` |
| `--max-comparisons` | `50000` | 重複候補の比較回数の上限。正の整数 |
| `--max-findings` | `200` | 重複検出の結果数の上限。正の整数 |
| `--fail-on` | `none` | `none` / `info` / `warning` / `error` |
| `--version` | — | ツールのバージョンを表示 |

JSON のキーには `max_lines` のようにアンダースコアを使用します。`checks` と `exclude` は文字列の配列です。JSON 設定を読み込むのは統一スキャナーのみです。

## 除外ルール

すべてのスキャナーは、プロジェクトのルートにある `.codecleanerignore` を読み込みます。相対パスの glob を 1 行ずつ記述し、区切り文字には `/` を使います。Python の `fnmatch` の規則に従い、`*` はパスの区切りにも一致します。ディレクトリの接頭部分も判定します。`generated/` はそのディレクトリを除外し、`tests/*` はテストファイルを、`*.min.js` は任意の深さで一致するファイルを除外します。`#` で始まる行はコメントです。Git の否定、エスケープ、完全な `.gitignore` 構文には対応していません。

依存ライブラリのディレクトリ、仮想環境、ビルド成果物、隠しディレクトリ、`.workbuddy/`、シンボリックリンク、ジャンクションの除外は設定で無効にできません。依存ライブラリのディレクトリ自体をルートにせず、実際のプロジェクトを指定してください。

## JSON 形式（schema_version 1）

最上位フィールド：`schema_version`、`version`、`root`、`complete`、`total_findings`、`counts`、`diagnostics`、`findings`。

各候補には `rule_id`、`type`、`path`、`line`、`severity`、`confidence`、`detail`、`suggestion` が含まれます。パスはプロジェクトのルートからの相対パスで、行番号は 1 から始まります。重複コードには `path_b`、`line_b`、`end_line`、`end_line_b`、`similarity` も含まれます。正規化後も、位置は元のソースに対応します。

- `severity`：`error` / `warning` / `info`。影響に基づく分類であり、ルールの出力だけでバグが確定するわけではありません。
- `confidence`：`high` / `medium` / `low`。静的な推論の確信度であり、人による確認の代わりにはなりません。
- `diagnostics`：読み取り・解析・上限に関する情報。各項目に `path` と `message` が含まれ、1 件でもある場合は `complete` が false になります。
- 終了コード：0 は完了して失敗基準未満、1 は完了して失敗基準に達した候補あり、2 は引数・設定・I/O エラーまたは不完全なスキャンです。終了コード 2 も必ず処理してください。

ルール ID：`structure.depth`、`structure.lines`、`structure.definitions`、`structure.empty`、`structure.naming`、`dead.import`、`dead.definition`、`duplicates.window`。

## 個別スキャナー

```bash
python scripts/analyze_structure.py PROJECT --max-lines 600 --max-depth 6
python scripts/detect_dead_code.py PROJECT --exclude "generated/*"
python scripts/find_duplicates.py PROJECT --min-lines 8 --threshold 0.9
```

同じスキーマの JSON を出力しますが、JSON 設定と CI の重大度による判定は適用しません。診断情報については `complete` を確認してください。CI では `run_review.py` を使用します。

## インストーラー

```bash
python install.py codex --dry-run
python install.py claude workbuddy --no-symlink
python install.py --all --force
python install.py --target ./local-skills --no-symlink
```

`--target` には親ディレクトリを指定し、その下に `code-cleaner/` を作成します。プラットフォーム名や `--all` とは併用しません。`--force` は既存のインストール先を明示的に置き換え、旧版を残します。上書きの許可がない場合は既存の対象を拒否します。ステージングが失敗しても旧版は変わりません。最後の改名に失敗した場合は復元を試みます。保持されたバックアップから手動で復元することもできます。`--dry-run` ではディレクトリの作成やインストールを行いません。成功は 0、いずれかの対象の失敗は 1、引数の誤りは 2 を返します。
