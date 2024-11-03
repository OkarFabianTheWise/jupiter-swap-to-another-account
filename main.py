import base64
import asyncio
import json
import httpx
from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from spl.token.async_client import AsyncToken
from solana.rpc.commitment import Finalized

RPC = "https://api.mainnet-beta.solana.com"  # mainnet

SOL = 'So11111111111111111111111111111111111111112'

class SolanaSwap:
    def __init__(self, private_key, output_mint, swap_amount, publickey_of_intended_receiver):
        self.keypair = Keypair.from_base58_string(private_key)
        self.public_key = self.keypair.pubkey()
        self.publickey_of_intended_receiver = publickey_of_intended_receiver
        self.input_mint = SOL
        self.output_mint = output_mint
        self.swap_amount = swap_amount
        self.client = AsyncClient(RPC)
        self.spl_client = None

    async def get_dest_token_account(self):
        """Retrieve or create the destination token account."""
        try:
            # print("Generating connection...")
            mint = Pubkey.from_string(self.output_mint)
            program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

            if not self.spl_client:
                # print("Generating SPL client...")
                self.spl_client = AsyncToken(conn=self.client, pubkey=mint, program_id=program_id, payer=self.keypair)

            dest = Pubkey.from_string(self.publickey_of_intended_receiver)
            try:
                # Try to fetch existing account
                accounts = await self.spl_client.get_accounts_by_owner(
                    owner=dest, commitment=None, encoding='base64'
                )
                dest_token_account = accounts.value[0].pubkey
                # print("Found dest_token_account:", dest_token_account)
            except:
                # Create a new associated token account if not found
                # print("Token account not found; creating a new one.")
                dest_token_account = await self.spl_client.create_associated_token_account(
                    owner=dest,
                    skip_confirmation=False,
                    recent_blockhash=None
                )
                # print("Generated dest_token_account:", dest_token_account)

            return dest_token_account
        except Exception as e:
            print("Error in get_dest_token_account:", e)
            return None

    async def fetch_quote(self):
        try:
            """Fetch the swap quote from Jupiter API."""
            jupiter_url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": self.input_mint,
                "outputMint": self.output_mint,
                "amount": int(self.swap_amount * 1e9)
            }
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(jupiter_url, params=params)
                quote = response.json()
                return quote
        except Exception as error:
            print("Error::fetch_quote:", error)
            return None

    async def perform_swap(self):
        try:
            """Execute the swap using Jupiter API and submit the transaction."""
            quote = await self.fetch_quote()
            destination_account = await self.get_dest_token_account()
            swap_url = "https://quote-api.jup.ag/v6/swap"
            payload = {
                "userPublicKey": str(self.public_key),
                "quoteResponse": quote,
                "destinationTokenAccount": str(destination_account),
                "computeUnitPriceMicroLamports": 20000000
            }
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(swap_url, json=payload)
                data = response.json()
                swap_transaction = data["swapTransaction"]

                raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(swap_transaction))
                signature = self.keypair.sign_message(message.to_bytes_versioned(raw_transaction.message))
                signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])

                opts = TxOpts(skip_preflight=False, preflight_commitment=Finalized)
                result = await self.client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)

                transaction_id = json.loads(result.to_json())["result"]
                # print(f"Transaction sent: https://explorer.solana.com/tx/{transaction_id}")
                return transaction_id
        except Exception as error:
            print("perform_swap:", error)
            return "transaction failed! reach out to support"
        
    async def close(self):
        """Close the client connection."""
        await self.client.close()

# call this function to initiate swap
async def initiate_swap(swap_amount, output_mint: str, publickey_of_intended_receiver: str, your_private_key_str: str):
    try:
        solana_swap = SolanaSwap(your_private_key_str, output_mint, swap_amount, publickey_of_intended_receiver)
        transaction_id = await solana_swap.perform_swap()
        return transaction_id
    except Exception as error:
        print("initiate_swap:", error)
        return "Transaction failed! reach out to support"

