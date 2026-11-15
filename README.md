# compass

Obsidian Vaultで転職活動の情報を一元管理するための、ローカルAIエージェント用ハーネスです。

compass本体はGit管理し、職歴・求人・企業研究・面接対策などの実データはObsidian Vaultの`compass/`配下で管理します。独立したWeb／デスクトップアプリは作りません。

## 現在の状態

要件定義段階です。初期実装では、過去の履歴書・職務経歴書・プロジェクト資料から、職歴・プロジェクト・実績・スキルのObsidianノートを作成する機能を対象にします。

## ドキュメント

- [要件定義書](REQUIREMENTS.md)
- [認証済み求人媒体の定期取得設計](docs/authenticated-job-collection-design.md)

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

## 企業情報の取得と定期更新

公開企業ページは、企業名とURLを指定して取得します。取得日・URL・要約だけを企業ノートへ記録し、ページ本文全体は保存しません。

```sh
python -m compass research-company "株式会社DONUTS" https://www.donuts.ne.jp/
python -m compass refresh-companies
```

定期実行はOSのスケジューラから`refresh-companies`を呼び出します。macOS向けのLaunchAgent定義は次で生成できます（例は毎日8時）。生成後、内容を確認してから`~/Library/LaunchAgents/`へ配置・読み込みしてください。ログイン済み媒体は対象にせず、公開URLだけを更新します。

```sh
python -m compass schedule-company-refresh \
  --output ~/Library/LaunchAgents/local.compass.company-refresh.plist \
  --hour 8
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.compass.company-refresh.plist
```

生成される定義は次のようなProgramArgumentsを持ちます。

```xml
<key>ProgramArguments</key>
<array>
  <string>/absolute/path/to/.venv/bin/python</string>
  <string>-m</string>
  <string>compass</string>
  <string>--config</string>
  <string>/absolute/path/to/config/local.toml</string>
  <string>refresh-companies</string>
</array>
```
