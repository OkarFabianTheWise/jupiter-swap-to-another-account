import base58, base64, asyncio, json
from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.system_program import TransferParams, transfer
from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Finalized

from jupiter_python_sdk.jupiter import Jupiter, Jupiter_DCA

# network endpoint for Solana mainnet
rpc_endpoint = "https://api.mainnet-beta.solana.com"  # mainnet

async def token_swap(token_to_buy: str, amount: int | float, slippage: int | float, user_key: str) -> str | None:
    """
    Executes a token swap on the Solana blockchain using Jupiter SDK.
    
    Args:
        token_to_buy (str): The token's mint address (as a string) to purchase.
        amount (int | float): The amount of SOL (in SOL) to swap for the token.
        slippage (int | float): The acceptable slippage percentage (in bps).
        user_key (str): The private key of the user, Base58 encoded.
        
    Returns:
        str | None: The transaction ID if the swap was successful, or an error message if unsuccessful.
    """
    try:
        # Decode the user's private key from a Base58-encoded string
        private_key = Keypair.from_bytes(base58.b58decode(user_key))

        # Initialize async Solana RPC client and Jupiter SDK
        async_client = AsyncClient(rpc_endpoint)
        jupiter = Jupiter(async_client, private_key)

        """
        EXECUTE A SWAP
        """
        # Execute a swap transaction using Jupiter SDK
        transaction_data = await jupiter.swap(
            input_mint="So11111111111111111111111111111111111111112",  # Example input mint (SOL token)
            output_mint=token_to_buy,  # Token mint address for the token to buy
            amount=amount_to_lamports,  # Amount of SOL in lamports to swap
            slippage_bps=slippage,  # Slippage tolerance in basis points
        )

        # Decode the serialized swap transaction
        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        
        # Sign the transaction using the user's private key
        signature = private_key.sign_message(message.to_bytes_versioned(raw_transaction.message))

        # Populate the transaction with the signature
        signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])

        # Transaction options: skip preflight checks, set commitment level
        opts = TxOpts(skip_preflight=False, preflight_commitment=Finalized)

        # Send the signed transaction to the Solana network
        result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        
        # Extract the transaction ID from the result
        transaction_id = json.loads(result.to_json())['result']
        
        return transaction_id  # Return the transaction ID
    except Exception as error:
        print("execute_swap error:", error)
        return "Transaction failed! reach out to support"  # Return None in case of an error

if __name__ == '__main__':
    pass
