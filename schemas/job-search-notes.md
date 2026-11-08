# 求人・選考ノートのスキーマ

このスキーマは、`job-search/`配下の企業、求人、スカウト、応募、面接ノートを対象にする。企業・求人の調査内容は、取得日と参照URLを必ず記録する。利用者の関心や所感は、AI評価と分けて保存する。

## `company`

| プロパティ | 必須 | 型 | 説明 |
| --- | --- | --- | --- |
| `type` | 必須 | `company` | ノート種別 |
| `labels` | 必須 | 配列 | `watchlist`、`researching`、`target`など |
| `industry` | 任意 | 配列 | 事業領域 |
| `research_sources` | 任意 | 配列 | 企業調査のURL |
| `retrieved_at` | 任意 | 文字列 | Web情報を取得した日時 |
| `user_interest` | 任意 | 文字列 | 利用者が明示した関心度 |

企業ノートの本文には、事業、主要プロダクト、開発組織、成長性・収益性の調査メモを記載する。関連する有効求人・応募・面接はDataviewで自動表示する。

## `job`

| プロパティ | 必須 | 型 | 説明 |
| --- | --- | --- | --- |
| `type` | 必須 | `job` | ノート種別 |
| `company` | 必須 | 文字列 | 関連企業ノートへのリンク |
| `position` | 必須 | 文字列 | 募集ポジション |
| `status` | 必須 | 文字列 | `active`または`inactive` |
| `source_urls` | 必須 | 配列 | 掲載媒体・採用ページのURL |
| `retrieved_at` | 必須 | 文字列 | 求人を取得した日時 |
| `employment_type` | 任意 | 文字列 | 正社員など |
| `location` | 任意 | 文字列 | 勤務地 |
| `annual_income_min` | 任意 | 数値 | 年収下限（万円） |
| `annual_income_max` | 任意 | 数値 | 年収上限（万円） |
| `skills` | 任意 | 配列 | 求められる技術 |
| `score` | 任意 | 数値 | AI評価の5段階総合評価 |
| `user_interest` | 任意 | 文字列 | 利用者の明示評価 |

同じ企業・ポジションの複数媒体情報は、1つの有効求人ノートの`source_urls`へ集約する。除外した求人は通常の求人ノートを作らず、`exclusions/`の軽量な一覧へ記録する。

## `scout`

転職ドラフトなどから届くスカウトを表す。検討対象になった時点で、求人・応募ノートへリンクする。

| プロパティ | 必須 | 型 | 説明 |
| --- | --- | --- | --- |
| `type` | 必須 | `scout` | ノート種別 |
| `company` | 必須 | 文字列 | 関連企業ノートへのリンク |
| `medium` | 必須 | 文字列 | 例: `tenshoku-draft` |
| `status` | 必須 | 文字列 | `new`、`considering`、`declined`、`promoted` |
| `received_at` | 任意 | 文字列 | 受信日時 |
| `offered_annual_income` | 任意 | 数値 | 提示年収（万円） |
| `job` | 任意 | 文字列 | 昇格先求人ノートへのリンク |

## `application`

| プロパティ | 必須 | 型 | 説明 |
| --- | --- | --- | --- |
| `type` | 必須 | `application` | ノート種別 |
| `company` | 必須 | 文字列 | 関連企業ノートへのリンク |
| `job` | 必須 | 文字列 | 応募対象求人ノートへのリンク |
| `medium` | 必須 | 文字列 | 応募媒体 |
| `position` | 必須 | 文字列 | 応募ポジション |
| `status` | 必須 | 文字列 | `pre-application`、`applied`、`in-progress`、`offer`、`rejected`、`withdrawn` |
| `submitted_at` | 任意 | 文字列 | 応募日 |

提出済みの自己紹介・職務要約・職務経歴などは本文に確定版として保存する。タスク・期限・次アクションは管理しない。

## `interview`

| プロパティ | 必須 | 型 | 説明 |
| --- | --- | --- | --- |
| `type` | 必須 | `interview` | ノート種別 |
| `company` | 必須 | 文字列 | 関連企業ノートへのリンク |
| `application` | 必須 | 文字列 | 関連応募ノートへのリンク |
| `stage` | 必須 | 文字列 | `casual`、`first`、`second`、`final`など |
| `status` | 必須 | 文字列 | `planned`、`completed` |
| `held_at` | 任意 | 文字列 | 実施日時 |

本文には事前準備と事後振り返りを記載する。共通的な自己紹介や転職理由は、`profile/interview-basics/`のテーマ別ノートからリンクする。
