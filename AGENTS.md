# 開発条件

- Android addon/bridgeの実装正本はこのrepo。共通coreはMeltype fork、host統合はFcitx5 Android forkに置く。
- 未実装・未実行・提案を実装済みや確定要求として記述しない。ビルド入口を追加したらBUILDとTESTINGを実際の手順へ更新する。
- 依存revision・SDK/NDK/ABIを固定し、更新理由と検証をIssueに記録する。既存dirty submoduleには触れず別cloneを使う。
- MeltypeのGPLと第三者ライセンス・copyright・NOTICEを保持する。
- UTF-8、メモリ所有権、handle寿命、thread、保存先、例外のABI境界を明示し、C++/C#境界へ例外を漏らさない。
