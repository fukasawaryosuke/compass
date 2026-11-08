# compass

Obsidian Vaultで転職活動の情報を一元管理するための、ローカルAIエージェント用ハーネスです。

compass本体はGit管理し、職歴・求人・企業研究・面接対策などの実データはObsidian Vaultの`compass/`配下で管理します。独立したWeb／デスクトップアプリは作りません。

## 現在の状態

要件定義段階です。初期実装では、過去の履歴書・職務経歴書・プロジェクト資料から、職歴・プロジェクト・実績・スキルのObsidianノートを作成する機能を対象にします。

## ドキュメント

- [要件定義書](REQUIREMENTS.md)

## 管理領域

| 領域 | 管理対象 |
| --- | --- |
| このリポジトリ | エージェント手順、スキーマ、テンプレート、検証スクリプト |
| Obsidian Vault | 転職活動のMarkdownデータ |
| Vault外アーカイブ | 原本資料、生成したPDF／Word、実行時キャッシュ |

詳細な方針、データモデル、セキュリティ要件は要件定義書を参照してください。

## 初期操作

ローカル設定を作成してから、Vaultとアーカイブを初期化します。

```sh
cp config/compass.example.toml config/local.toml
# config/local.tomlのパスをこの端末向けに編集
python -m compass init
```

資料はアーカイブの`incoming/`へ置き、以下を実行します。取り込み成功後、原本は`originals/`へ移動し、Vaultには抽出ノートだけが作成されます。

```sh
python -m compass ingest
```
