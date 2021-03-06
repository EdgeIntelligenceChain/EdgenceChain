from params.Params import Params
from utils.Errors import (
    BaseException,
    TxUnlockError,
    TxnValidationError,
    BlockValidationError,
)
from ds.OutPoint import OutPoint
from ds.TxOut import TxOut
from ds.TxIn import TxIn
from ds.Transaction import Transaction
from ds.Block import Block
import binascii
import time
import json
import hashlib
import threading
import logging
import socketserver
import socket
import random
import os

from p2p.Peer import Peer
from ds.UTXO_Set import UTXO_Set
from ds.MemPool import MemPool
from ds.MerkleNode import MerkleNode
from ds.BlockChain import BlockChain

import ecdsa
from base58 import b58encode_check
from utils.Utils import Utils
from wallet import Wallet

logging.basicConfig(
    level=getattr(logging, os.environ.get("TC_LOG_LEVEL", "INFO")),
    format="[%(asctime)s][%(module)s:%(lineno)d] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def save_to_disk(active_chain: BlockChain, CHAIN_PATH=Params.CHAIN_FILE):
    """
    Save active chain to chain_file.
    """

    with open(CHAIN_PATH, "wb") as f:
        # logger.info(f"[persistence] saving chain with {len(active_chain.chain)} blocks")
        f.write(Utils.encode_chain_data(list(active_chain.chain)))


def load_from_disk(active_chain: BlockChain, utxo_set: UTXO_Set, CHAIN_PATH=Params.CHAIN_FILE):

    def _connect_block(block: Block, active_chain: BlockChain, utxo_set: UTXO_Set) -> bool:
        """
        Add block after current chain. Return True if block added successfully, else False. 
        """

        if block.validate_block(active_chain, utxo_set) is None:
            return False

        logger.info(
            f"connecting the {len(active_chain.chain)+1}th block {block.id} to chain {active_chain.idx}"
        )
        active_chain.chain.append(block)

        # Minipulate transactions in this block.
        # Remove txin from utxo_set, add txout to utxo_set.
        for tx in block.txns:
            if not tx.is_coinbase:
                for txin in tx.txins:
                    utxo_set.rm_from_utxo(*txin.to_spend)
            for i, txout in enumerate(tx.txouts):
                utxo_set.add_to_utxo(
                    txout, tx, i, tx.is_coinbase, len(active_chain.chain)
                )

        return True

    if not os.path.isfile(CHAIN_PATH):
        logger.info(f"[persistence] chain storage file does not exist")
        return
    else:
        # active_chain.chain is a list initialized with genesis_block
        # so len(active_chain.chain) should equals to 1
        if len(active_chain.chain) > 1:
            logger.info(
                f"[persistence] more than the genesis block exists, load_from_disk stopped and return"
            )
            return
    try:
        with open(CHAIN_PATH, "rb") as f:
            block_len = int(f.read(20))
            logger.info(
                f"[persistence] {block_len} is claimed at the head of chain file"
            )
            msg_len = int(f.read(20))
            gs = dict()
            gs["Block"], gs["Transaction"], gs["TxIn"], gs["TxOut"], gs["OutPoint"] = (
                globals()["Block"],
                globals()["Transaction"],
                globals()["TxIn"],
                globals()["TxOut"],
                globals()["OutPoint"],
            )

            new_blocks = Utils.deserialize(f.read(msg_len), gs)
            logger.info(f"[persistence] parsing {len(new_blocks)} blocks from disk")

            # Connect block after genesis block.
            for block in new_blocks[1:]:
                if not _connect_block(block, active_chain, utxo_set):
                    logger.info(
                        f"[persistence] {active_chain.height+1} block connecting failed, load_from_disk stopped and return"
                    )
                    return
            logger.info(f"[persistence] loading {len(new_blocks)} blocks successful")
    except Exception:
        logger.exception(f"[persistence] failded in loading from chain storage file")
        return
