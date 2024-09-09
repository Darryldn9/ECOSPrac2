from algosdk import mnemonic, account, transaction
from algosdk.v2client import algod
from algosdk.v2client import indexer
import hashlib
import time


# Define a helper function to create an Algod client (no API key required)
def create_algod_client():
    algod_address = "https://testnet-api.algonode.cloud"
    algod_token = ""  # No API key required for Algonode
    return algod.AlgodClient(algod_token, algod_address)


# Create an indexer client (for fetching transaction history and asset info)
def create_indexer_client():
    indexer_address = "https://testnet-idx.algonode.cloud"
    indexer_token = ""  # No API key required for Algonode
    return indexer.IndexerClient(indexer_token, indexer_address)


# Generate a new Algorand account
def generate_account():
    private_key, address = account.generate_account()
    print("New Account Generated!")
    print("Address: ", address)
    print("Mnemonic: ", mnemonic.from_private_key(private_key))
    return private_key, address


# Load an account from mnemonic
def load_account_from_mnemonic():
    user_mnemonic = input("Enter your mnemonic: ").strip()
    private_key = mnemonic.to_private_key(user_mnemonic)
    address = account.address_from_private_key(private_key)
    print("Account Loaded!")
    print(f"Address: {address}")
    return private_key, address


# Get account details (balance, recent transactions, NFTs)
def view_account_details(algod_client, indexer_client, address):
    try:
        # Fetch account balance
        account_info = algod_client.account_info(address)
        balance = account_info.get('amount') / 1e6  # Convert microAlgos to Algos
        print(f"\nBalance: {balance} Algos")

        # Fetch owned NFTs (ASAs)
        assets = account_info.get('assets', [])
        if assets:
            print("\nOwned Assets (NFTs):")
            for asset in assets:
                asset_id = asset['asset-id']
                try:
                    # Fetch asset details
                    asset_info = indexer_client.asset_info(asset_id)

                    # Extract asset details
                    asset_details = asset_info.get('asset', {}).get('params', {})

                    # Print useful asset details
                    asset_name = asset_details.get('name', 'Unknown')
                    unit_name = asset_details.get('unit-name', 'Unknown')
                    url = asset_details.get('url', 'No URL')
                    amount = asset.get('amount', 0)  # Correctly fetch the amount

                    print(
                        f" - Asset ID: {asset_id}, Name: {asset_name}, Unit: {unit_name}, URL: {url}, Amount: {amount}")
                except Exception as e:
                    print(f"Error fetching details for Asset ID {asset_id}: {e}")
        else:
            print("\nNo NFTs found for this account.")

        # Fetch recent transactions using indexer
        transactions = indexer_client.search_transactions_by_address(address, limit=5)
        print("\nRecent Transactions:")
        for txn in transactions.get('transactions', []):
            txn_amount = txn.get('payment-transaction', {}).get('amount', 0) / 1e6  # Convert microAlgos to Algos
            print(f" - Transaction ID: {txn['id']}, Amount: {txn_amount} Algos")

    except Exception as e:
        print(f"Error fetching account details: {e}")


# Transfer ALGOs between accounts
def transfer_algo(algod_client, sender_private_key, sender_address):
    try:
        receiver_address = input("Enter the receiver's Algorand address: ").strip()
        if len(receiver_address) != 58:
            raise ValueError("Invalid receiver address!")

        amount = int(input("Enter the amount to transfer (in microAlgos): ").strip())
        if amount <= 0:
            raise ValueError("Amount must be positive!")

        params = algod_client.suggested_params()
        unsigned_txn = transaction.PaymentTxn(sender_address, params, receiver_address, amount)
        signed_txn = unsigned_txn.sign(sender_private_key)

        tx_id = algod_client.send_transaction(signed_txn)
        print(f"Transaction ID: {tx_id}")
        wait_for_confirmation(algod_client, tx_id)

    except Exception as e:
        print(f"Error during transfer: {e}")


# Create an NFT (ASA)
def create_nft(algod_client, sender_private_key, sender_address):
    try:
        unit_name = input("Enter the unit name for the NFT: ").strip()
        asset_name = input("Enter the asset name for the NFT: ").strip()
        asset_url = input("Enter the URL with more information about the asset: ").strip()
        asset_description = input("Enter a description for the asset: ").strip()
        quantity = int(input("Enter the number of NFTs to mint: ").strip())

        if quantity <= 0:
            raise ValueError("Quantity must be positive!")

        # Use a dummy metadata hash or remove it if not needed
        metadata_hash = hashlib.sha256(asset_description.encode()).digest()[:32]

        params = algod_client.suggested_params()
        txn = transaction.AssetConfigTxn(
            sender=sender_address,
            sp=params,
            total=quantity,  # Number of NFTs to mint
            default_frozen=False,
            unit_name=unit_name,
            asset_name=asset_name,
            manager=sender_address,
            reserve=sender_address,
            freeze=sender_address,
            clawback=sender_address,
            url=asset_url,
            decimals=0,  # Non-divisible, makes it an NFT
            metadata_hash=metadata_hash  # Optional field for metadata hash
        )
        signed_txn = txn.sign(sender_private_key)
        tx_id = algod_client.send_transaction(signed_txn)
        print(f"Transaction ID for NFT creation: {tx_id}")
        wait_for_confirmation(algod_client, tx_id)

    except Exception as e:
        print(f"Error during NFT creation: {e}")


# Opt-in to an NFT (ASA)
def opt_in_nft(algod_client, receiver_private_key, receiver_address, asset_id):
    try:
        # Get suggested params
        suggested_params = algod_client.suggested_params()

        # Create opt-in transaction
        txn = transaction.AssetTransferTxn(
            sender=receiver_address,
            receiver=receiver_address,
            amt=0,  # No actual transfer, just opt-in
            index=asset_id,
            sp=suggested_params
        )

        # Sign the transaction with the receiver's private key
        signed_txn = txn.sign(receiver_private_key)

        # Send the transaction
        txid = algod_client.send_transaction(signed_txn)
        print(f"Opt-in transaction sent. Transaction ID: {txid}")

        # Wait for the transaction to be confirmed
        wait_for_confirmation(algod_client, txid)

        print("Opt-in confirmed.")
        return True
    except Exception as e:
        print(f"Error during opt-in request: {e}")
        return False

def transfer_nft(algod_client, indexer_client, sender_private_key, sender_address):
    try:
        # List owned assets
        account_info = algod_client.account_info(sender_address)
        assets = account_info.get('assets', [])
        if not assets:
            print("No assets to transfer.")
            return

        print("\nOwned Assets (NFTs):")
        for asset in assets:
            asset_id = asset['asset-id']
            asset_info = indexer_client.asset_info(asset_id)
            asset_details = asset_info.get('asset', {}).get('params', {})
            asset_name = asset_details.get('name', 'Unknown')
            unit_name = asset_details.get('unit-name', 'Unknown')
            amount = asset.get('amount', 0)  # Fetch asset amount

            print(f" - Asset ID: {asset_id}, Name: {asset_name}, Unit: {unit_name}, Amount: {amount}")

        # Prompt for NFT transfer details
        asset_id = int(input("Enter the Asset ID of the NFT to transfer: ").strip())
        receiver_address = input("Enter the receiver's Algorand address: ").strip()
        if len(receiver_address) != 58:
            raise ValueError("Invalid receiver address!")

        amount = int(input("Enter the amount to transfer (in units): ").strip())
        if amount <= 0:
            raise ValueError("Amount must be positive!")

        # Check if the sender holds the asset and has enough to transfer
        for asset in assets:
            if asset['asset-id'] == asset_id:
                if asset.get('amount', 0) < amount:
                    raise ValueError("Insufficient amount of this asset.")
                break
        else:
            raise ValueError(f"Sender address does not hold Asset ID {asset_id}.")

        # Check if receiver has opted in for the asset
        receiver_account_info = indexer_client.account_info(receiver_address)
        receiver_assets = receiver_account_info.get('assets', [])
        receiver_asset_ids = [asset['asset-id'] for asset in receiver_assets]

        if asset_id not in receiver_asset_ids:
            print(f"Receiver has not opted in for Asset ID {asset_id}.")
            opt_in = input("Would you like to request the receiver to opt in? (Y/N): ").strip().upper()
            if opt_in == 'Y':
                if not opt_in_nft(algod_client, sender_private_key, receiver_address, asset_id):
                    print("Opt-in request failed. Aborting transfer.")
                    return
                input("Press 'Y' once the receiver has opted in: ")
            else:
                print("Opt-in request not sent. Aborting transfer.")
                return

        # Perform NFT transfer
        params = algod_client.suggested_params()
        unsigned_txn = transaction.AssetTransferTxn(
            sender=sender_address,
            sp=params,
            receiver=receiver_address,
            amt=amount,
            index=asset_id
        )
        signed_txn = unsigned_txn.sign(sender_private_key)
        tx_id = algod_client.send_transaction(signed_txn)
        print(f"Transaction ID for NFT transfer: {tx_id}")
        wait_for_confirmation(algod_client, tx_id)

    except Exception as e:
        print(f"Error during NFT transfer: {e}")


# Main menu to guide user through options
def main():
    algod_client = create_algod_client()
    indexer_client = create_indexer_client()

    # Initialize account information
    private_key = None
    address = None

    # Account setup (either load an existing mnemonic or generate a new one)
    while not private_key or not address:
        print("\n--- Account Setup ---")
        print("1. Generate a new account")
        print("2. Load account from mnemonic")
        choice = input("Select an option (1 or 2): ").strip()

        if choice == '1':
            private_key, address = generate_account()
        elif choice == '2':
            private_key, address = load_account_from_mnemonic()
        else:
            print("Invalid choice. Please select 1 or 2.")

    # Main menu
    while True:
        print("\n--- Main Menu ---")
        print("1. View account details")
        print("2. Transfer ALGOs")
        print("3. Create an NFT")
        print("4. Transfer an NFT")
        print("5. Exit")
        option = input("Select an option (1-5): ").strip()

        if option == '1':
            view_account_details(algod_client, indexer_client, address)
        elif option == '2':
            transfer_algo(algod_client, private_key, address)
        elif option == '3':
            create_nft(algod_client, private_key, address)
        elif option == '4':
            transfer_nft(algod_client, indexer_client, private_key, address)
        elif option == '5':
            print("Exiting...")
            break
        else:
            print("Invalid option. Please select a number between 1 and 5.")


def wait_for_confirmation(client, txid, timeout=10):
    """
    Waits for the transaction to be confirmed.
    """
    start_time = time.time()
    while True:
        try:
            status = client.pending_transaction_info(txid)  # Use the correct method here
            if status.get("confirmed-round") and status["confirmed-round"] > 0:
                print(f"Transaction confirmed in round {status['confirmed-round']}.")
                return
        except Exception as e:
            print(f"Error checking transaction status: {e}")

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise Exception("Transaction confirmation timeout.")

        time.sleep(1)
2

if __name__ == "__main__":
    main()
