"""
Unit tests for authentication module.

Tests the shared signature verification functionality used across
NEXUS interfaces for cryptographic authentication.
"""

import pytest
from eth_keys import keys
from eth_hash.auto import keccak

from nexus.core.auth import verify_signature


class TestVerifySignature:
    """Test suite for verify_signature function."""

    def test_verify_signature_success(self):
        """Test successful signature verification with valid signature."""
        # Generate a test key pair
        private_key = keys.PrivateKey(b'\x01' * 32)
        public_key = private_key.public_key
        address = public_key.to_address()
        
        # Create a test payload
        payload = "/identity"
        message_hash = keccak(payload.encode('utf-8'))
        
        # Sign the payload
        signature = private_key.sign_msg_hash(message_hash)
        
        # Convert signature to hex format (with v in Ethereum format 27/28)
        sig_bytes = signature.to_bytes()
        v = sig_bytes[64]
        if v < 27:
            sig_bytes = sig_bytes[:64] + bytes([v + 27])
        signature_hex = '0x' + sig_bytes.hex()
        
        # Prepare auth data
        auth_data = {
            'publicKey': address,
            'signature': signature_hex
        }
        
        # Verify signature
        result = verify_signature(payload, auth_data)
        
        # Assert successful verification
        assert result['status'] == 'success'
        assert result['public_key'].lower() == address.lower()

    def test_verify_signature_missing_auth(self):
        """Test that missing auth_data returns error."""
        payload = "/identity"
        
        result = verify_signature(payload, None)
        
        assert result['status'] == 'error'
        assert 'Authentication required' in result['message']

    def test_verify_signature_missing_public_key(self):
        """Test that missing publicKey in auth_data returns error."""
        auth_data = {
            'signature': '0x123456'
        }
        
        result = verify_signature("/identity", auth_data)
        
        assert result['status'] == 'error'
        assert 'Missing public key or signature' in result['message']

    def test_verify_signature_missing_signature(self):
        """Test that missing signature in auth_data returns error."""
        auth_data = {
            'publicKey': '0xabc123'
        }
        
        result = verify_signature("/identity", auth_data)
        
        assert result['status'] == 'error'
        assert 'Missing public key or signature' in result['message']

    def test_verify_signature_invalid_format(self):
        """Test that invalid signature format returns error."""
        auth_data = {
            'publicKey': '0x1234567890abcdef',
            'signature': '0xinvalid_signature_format'
        }
        
        result = verify_signature("/identity", auth_data)
        
        assert result['status'] == 'error'
        assert 'Invalid signature format' in result['message']

    def test_verify_signature_key_mismatch(self):
        """Test that signature from different key returns error."""
        # Generate first key pair and sign
        private_key_1 = keys.PrivateKey(b'\x01' * 32)
        payload = "/identity"
        message_hash = keccak(payload.encode('utf-8'))
        signature = private_key_1.sign_msg_hash(message_hash)
        
        # Convert signature to hex
        sig_bytes = signature.to_bytes()
        v = sig_bytes[64]
        if v < 27:
            sig_bytes = sig_bytes[:64] + bytes([v + 27])
        signature_hex = '0x' + sig_bytes.hex()
        
        # Use different public key (second key pair)
        private_key_2 = keys.PrivateKey(b'\x02' * 32)
        public_key_2 = private_key_2.public_key
        address_2 = public_key_2.to_address()
        
        # Prepare auth data with mismatched key
        auth_data = {
            'publicKey': address_2,  # Different key
            'signature': signature_hex
        }
        
        # Verify signature
        result = verify_signature(payload, auth_data)
        
        # Assert verification failure
        assert result['status'] == 'error'
        assert 'Public key mismatch' in result['message']

    def test_verify_signature_wrong_payload(self):
        """Test that signature for different payload returns error."""
        # Generate key pair and sign original payload
        private_key = keys.PrivateKey(b'\x01' * 32)
        public_key = private_key.public_key
        address = public_key.to_address()
        
        original_payload = "/identity"
        original_hash = keccak(original_payload.encode('utf-8'))
        signature = private_key.sign_msg_hash(original_hash)
        
        # Convert signature to hex
        sig_bytes = signature.to_bytes()
        v = sig_bytes[64]
        if v < 27:
            sig_bytes = sig_bytes[:64] + bytes([v + 27])
        signature_hex = '0x' + sig_bytes.hex()
        
        # Prepare auth data
        auth_data = {
            'publicKey': address,
            'signature': signature_hex
        }
        
        # Verify with different payload
        different_payload = "/config"
        result = verify_signature(different_payload, auth_data)
        
        # Assert verification failure
        assert result['status'] == 'error'
        assert 'Public key mismatch' in result['message']

    def test_verify_signature_empty_payload(self):
        """Test signature verification with empty payload."""
        # Generate key pair and sign empty string
        private_key = keys.PrivateKey(b'\x01' * 32)
        public_key = private_key.public_key
        address = public_key.to_address()
        
        payload = ""
        message_hash = keccak(payload.encode('utf-8'))
        signature = private_key.sign_msg_hash(message_hash)
        
        # Convert signature to hex
        sig_bytes = signature.to_bytes()
        v = sig_bytes[64]
        if v < 27:
            sig_bytes = sig_bytes[:64] + bytes([v + 27])
        signature_hex = '0x' + sig_bytes.hex()
        
        # Prepare auth data
        auth_data = {
            'publicKey': address,
            'signature': signature_hex
        }
        
        # Verify signature
        result = verify_signature(payload, auth_data)
        
        # Should succeed for empty payload
        assert result['status'] == 'success'
        assert result['public_key'].lower() == address.lower()

