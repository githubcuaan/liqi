# Liqily

Data-mining project using the AoG Spring 2026 tournament dataset.

The raw dataset is downloaded separately from Drive; ask the project owner for
the link to the `liquipedia-final.zip` archive. Put it at
`dataset/liquipedia-final.zip` and extract it:

```sh
sha256sum dataset/liquipedia-final.zip
unzip -n dataset/liquipedia-final.zip -d dataset/
```

Expected archive SHA-256:
`ffdc93066709c99567f1845b68be885afea3973cd4000251a473943c3fd3473f`.
If the Drive download is an unpacked directory instead, copy it into
`dataset/035ce761e53a47db/`. Check the per-file hashes in
`dataset/035ce761e53a47db/release-manifest.json` and
`dataset/035ce761e53a47db/csv/manifest.json` before running experiments.
Do not mix snapshots from different versions. The expected dataset version is
`035ce761e53a47dbfd18ca1d9fabe7ceb0ec79115271bccac303bed2a6c0195c`.

See the [dataset notes](dataset/035ce761e53a47db/README.md) for scope and
limitations. Redistribution rights are not yet verified.
