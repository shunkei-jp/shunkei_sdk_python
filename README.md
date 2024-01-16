# Shunkei SDK for Python

Shunkei SDK for Python を利用することで、
プログラムより[Shunkei VTX](https://www.shunkei.jp/product/)を操作することが可能です。

## Installation

```sh
pip install shunkei_sdk
```

## sample

```python
from shunkei_sdk import ShunkeiVTX

vtx = ShunkeiVTX.auto_connect()
vtx.write(b"Hello, world") # Send UART message to Shunkei VTX
```

## お問い合わせ

質問・バグ報告・活用事例の報告などは、[Shunkei Github discussions](https://github.com/orgs/shunkei-jp/discussions) へご投稿ください。
機能追加に関する要望や検討中の利用事例なども投稿いただければ、今後の開発方針に参考にさせていただきます。

公開したくないお問い合せは [お問い合わせフォーム](https://docs.google.com/forms/d/e/1FAIpQLSdW6nHX65omXpBzfH-S1-7y5yRUXsz7jtYAO0YHv2naIvSpBg/viewform) までお寄せください。

