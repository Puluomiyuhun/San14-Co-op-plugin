"""Strict single-command pilot protocol. No game access or network listeners."""
import hashlib
import hmac
import json
import re
from pilot_evidence import GAME_SHA

BASELINE_SHA='5c03db4d2fd171912a96ffa2e2474817ac41d0ed383de1ff7dbeaeb936a796d1'
WORDS=[666,0,1300,4,11,157,7,18,48400,48400,48400,48400,48400,4,5,20,0,1,0,1,2,48400,48400,0,48400,48400]


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def validate_payload(payload):
    keys={'schema','request_id','game_sha256','baseline_sha256','force_id','source_city_id','command_words'}
    if type(payload) is not dict or set(payload)!=keys:
        raise ValueError('Invalid command envelope')
    if payload['schema']!='san14.pilot-submit.v1':raise ValueError('Unsupported command schema')
    if type(payload['request_id']) is not str or re.fullmatch('[0-9a-f]{32}',payload['request_id']) is None:
        raise ValueError('Invalid request id')
    if payload['game_sha256']!=GAME_SHA or payload['baseline_sha256']!=BASELINE_SHA:
        raise ValueError('Wrong game version or checkpoint baseline')
    if type(payload['force_id']) is not int or payload['force_id']!=12 or type(payload['source_city_id']) is not int or payload['source_city_id']!=19:
        raise ValueError('Pilot ownership binding mismatch')
    words=payload['command_words']
    if type(words) is not list or len(words)!=26 or any(type(v) is not int for v in words) or words!=WORDS:
        raise ValueError('Pilot only permits the recorded Zhang Lu 1300 -> Chang an command')
    return words.copy()


def sign(payload,key):
    validate_payload(payload)
    return {'payload':payload,'mac':hmac.new(key,canonical(payload),hashlib.sha256).hexdigest()}


def authenticate(packet,key):
    if type(packet) is not dict or set(packet)!={'payload','mac'}:raise ValueError('Invalid packet')
    expected=hmac.new(key,canonical(packet['payload']),hashlib.sha256).hexdigest()
    if type(packet['mac']) is not str or not hmac.compare_digest(expected,packet['mac']):
        raise ValueError('Invalid session authentication')
    validate_payload(packet['payload'])
    return packet['payload']
