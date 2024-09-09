
# Algorand CLI Tool

This Python command-line interface (CLI) tool allows you to:
- Generate Algorand accounts (public/private keys and mnemonic phrase).
- Transfer ALGOs between accounts.
- Create an NFT (Algorand Standard Asset).

## Requirements
- Python 3.x
- `py-algorand-sdk`

## Installation

```bash
pip install py-algorand-sdk
```

## Usage

### Generate an Algorand Account

```bash
python main.py generate
```

### Transfer ALGOs

```bash
python main.py transfer --sender <SENDER_ADDRESS> --receiver <RECEIVER_ADDRESS> --amount <AMOUNT>
```

### Create an NFT

```bash
python main.py nft --sender <SENDER_ADDRESS> --unit_name <UNIT_NAME> --asset_name <ASSET_NAME> --url <ASSET_URL>
```

### Example:
```bash
python main.py generate
python main.py transfer --sender ABC123 --receiver XYZ456 --amount 1000000
python main.py nft --sender ABC123 --unit_name ART --asset_name MyArtNFT --url https://example.com/nft
```

Ensure you have your Algorand TestNet API key and replace the placeholder API key in the code.
        