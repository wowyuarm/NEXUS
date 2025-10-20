"""
Authentication utilities for NEXUS.

This module provides shared cryptographic signature verification functionality
used across multiple interfaces (WebSocket commands, REST API endpoints).

Key features:
- Ethereum-style ECDSA signature verification using secp256k1
- Keccak-256 message hashing (Ethereum standard)
- Public key recovery from signatures
- Address validation and matching

This module is part of the core layer to ensure DRY principle and consistent
authentication across all NEXUS interfaces.
"""

import logging
from typing import Dict, Any, Optional

from eth_keys import keys
from eth_keys.exceptions import ValidationError, BadSignature
from eth_hash.auto import keccak

logger = logging.getLogger(__name__)


def verify_signature(payload: str, auth_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify cryptographic signature for a payload.

    This function implements Ethereum-style signature verification using eth_keys.
    It verifies that the payload was signed by the holder of the private key
    corresponding to the provided public key.

    Args:
        payload: The string payload that was signed (e.g., command or JSON data)
        auth_data: Dictionary containing 'publicKey' and 'signature'
                   Example: {"publicKey": "0x...", "signature": "0x..."}

    Returns:
        Dict with either:
            - {'status': 'success', 'public_key': verified_public_key}
            - {'status': 'error', 'message': error_description}

    Examples:
        >>> auth = {"publicKey": "0xabc...", "signature": "0xdef..."}
        >>> result = verify_signature("/identity", auth)
        >>> if result['status'] == 'success':
        ...     print(f"Verified: {result['public_key']}")
    """
    try:
        # Check if auth data is provided
        if not auth_data:
            logger.warning("Signature required but auth data not provided")
            return {
                "status": "error",
                "message": "Authentication required: This operation requires a cryptographic signature"
            }

        # Extract public key and signature
        public_key_hex = auth_data.get('publicKey')
        signature_hex = auth_data.get('signature')

        if not public_key_hex or not signature_hex:
            logger.warning("Missing publicKey or signature in auth data")
            return {
                "status": "error",
                "message": "Authentication failed: Missing public key or signature"
            }

        # Hash the payload message (same as frontend does)
        message_hash = keccak(payload.encode('utf-8'))
        
        # Parse the signature
        try:
            # Convert hex signature to bytes
            sig_bytes = bytes.fromhex(signature_hex.removeprefix('0x'))
            
            # Ethereum signatures have v=27 or 28, but eth_keys expects v=0 or 1
            # Adjust the v value (last byte) if it's in Ethereum format
            if len(sig_bytes) == 65:  # Standard signature format: r(32) + s(32) + v(1)
                v = sig_bytes[64]
                if v >= 27:  # Ethereum format
                    sig_bytes = sig_bytes[:64] + bytes([v - 27])
            
            signature = keys.Signature(signature_bytes=sig_bytes)
        except (ValueError, ValidationError) as e:
            logger.warning(f"Invalid signature format: {e}")
            return {
                "status": "error",
                "message": "Authentication failed: Invalid signature format"
            }

        # Recover public key from signature
        try:
            recovered_public_key = signature.recover_public_key_from_msg_hash(message_hash)
            recovered_address = recovered_public_key.to_address()
        except (BadSignature, ValidationError) as e:
            logger.warning(f"Signature recovery failed: {e}")
            return {
                "status": "error",
                "message": "Authentication failed: Invalid signature"
            }

        # Verify the recovered address matches the provided public key
        if recovered_address.lower() != public_key_hex.lower():
            logger.warning(f"Public key mismatch: expected {public_key_hex}, got {recovered_address}")
            return {
                "status": "error",
                "message": "Authentication failed: Public key mismatch"
            }

        # Signature verification successful
        logger.info(f"Signature verified successfully for public_key={public_key_hex}")
        return {
            "status": "success",
            "public_key": public_key_hex
        }

    except Exception as e:
        logger.error(f"Unexpected error during signature verification: {e}")
        return {
            "status": "error",
            "message": f"Authentication failed: {str(e)}"
        }

