import argparse
import binascii
import json
import logging
import sys
import time
from datetime import datetime
from enum import Enum

import cose.algorithms
from cryptojwt.utils import b64d, b64e

from .cwt import CWT, CwtClaims, read_cosekey
from .optical import save_qrcode
from .utils import json_compact_len

SIGN_ALG = cose.algorithms.Es256
HCERT_CLAIM = -65537

logger = logging.getLogger(__name__)


class HealthCertificateClaims(Enum):
    EU_HCERT_V1 = 1


def command_sign(args: argparse.Namespace):
    """Create signed EHC"""

    private_key = read_cosekey(args.key, private=True)
    if args.kid:
        private_key.kid = b64d(args.kid.encode())

    with open(args.input, "rt") as input_file:
        input_data = input_file.read()

    logger.info("Input JSON data: %d bytes", len(input_data))

    eu_hcert_v1 = json.loads(input_data)
    logger.info("Compact JSON: %d bytes", json_compact_len(eu_hcert_v1))

    claims = {
        HCERT_CLAIM: {HealthCertificateClaims.EU_HCERT_V1.value: eu_hcert_v1},
    }
    cwt = CWT.from_dict(claims=claims, issuer=args.issuer, ttl=args.ttl)
    cwt_bytes = cwt.sign(private_key=private_key, alg=SIGN_ALG)
    logger.info("Raw signed CWT: %d bytes", len(cwt_bytes))

    if args.output:
        with open(args.output, "wb") as output_file:
            output_file.write(cwt_bytes)
    else:
        logger.info("Output: %s", binascii.hexlify(cwt_bytes).decode())

    if args.qrcode:
        save_qrcode(cwt_bytes, args.qrcode)


def command_verify(args: argparse.Namespace):
    """Verify signed EHC"""

    public_key = read_cosekey(args.key, private=False)

    if args.kid:
        public_key.kid = b64d(args.kid.encode())

    with open(args.input, "rb") as input_file:
        signed_data = input_file.read()

    now = int(time.time())
    cwt = CWT.from_bytes(signed_data=signed_data, public_keys=[public_key])

    if (iss := cwt.claims.get(CwtClaims.ISS.value)) is not None:
        logger.info("Signatured issued by: %s", iss)

    logger.info("Signature verified by: %s", b64e(cwt.key.kid).decode())

    if (iat := cwt.claims.get(CwtClaims.IAT.value)) is not None:
        logger.info("Signatured issued at: %s", datetime.fromtimestamp(iat))

    if (exp := cwt.claims.get(CwtClaims.EXP.value)) is not None:
        if exp > now:
            logger.info("Signatured expires at: %s", datetime.fromtimestamp(exp))
        else:
            logger.info("Signatured expired at: %s", datetime.fromtimestamp(exp))
            raise RuntimeError("Signature expired")

    hcert = cwt.claims.get(HCERT_CLAIM)
    eu_hcert_v1 = hcert.get(HealthCertificateClaims.EU_HCERT_V1.value)

    if eu_hcert_v1 is None:
        logger.error("No EU HCERT version 1 found in CWT")
        sys.exit(-1)

    if args.output:
        with open(args.output, "wt") as output_file:
            json.dump(eu_hcert_v1, output_file, indent=4)
    else:
        logger.info("Verified payload: %s", json.dumps(eu_hcert_v1, indent=4))


def main():
    """Main function"""

    parser = argparse.ArgumentParser(
        description="Electronic Health Certificate signer/verifier"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
        required=False,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug output",
        required=False,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_sign = subparsers.add_parser("sign", help="Sign health cert")
    parser_sign.set_defaults(func=command_sign)
    parser_sign.add_argument(
        "--key", metavar="filename", help="Private JWK filename", required=True
    )
    parser_sign.add_argument(
        "--issuer",
        metavar="issuer",
        help="Signature issuer (ISO 3166 country code)",
        required=False,
    )
    parser_sign.add_argument(
        "--ttl",
        metavar="seconds",
        help="Signature TTL",
        type=int,
        required=False,
    )
    parser_sign.add_argument(
        "--input",
        metavar="filename",
        help="JSON-encoded payload",
        required=True,
    )
    parser_sign.add_argument(
        "--output",
        metavar="filename",
        help="Compressed CBOR output",
        required=False,
    )
    parser_sign.add_argument(
        "--kid",
        metavar="id",
        help="Key identifier (base64url encoded)",
        required=False,
    )
    parser_sign.add_argument(
        "--qrcode",
        metavar="filename",
        help="QR output",
        required=False,
    )

    parser_verify = subparsers.add_parser("verify", help="Verify signed cert")
    parser_verify.set_defaults(func=command_verify)
    parser_verify.add_argument(
        "--key", metavar="filename", help="Public JWK filename", required=True
    )
    parser_verify.add_argument(
        "--input",
        metavar="filename",
        help="Compressed CBOR input",
        required=True,
    )
    parser_verify.add_argument(
        "--output",
        metavar="filename",
        help="JSON-encoded payload",
        required=False,
    )
    parser_verify.add_argument(
        "--kid",
        metavar="id",
        help="Key identifier (base64url encoded)",
        required=False,
    )

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    args.func(args)


if __name__ == "__main__":
    main()
