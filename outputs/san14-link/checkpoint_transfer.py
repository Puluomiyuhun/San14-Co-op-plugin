"""Bounded pipelined checkpoint fetch; no native load or room endpoint.

Use a one-transfer authenticated TLS Client; this call consumes and closes it.
The endpoint must already authorize this peer and pin the offered checkpoint.
Production Room currently has no artifact endpoint: this helper is exercised
against the research server only, and never enables native gameplay.
"""
from authoritative_sync import CHUNK, CheckpointReceiver, SyncError, digest, require
from room_transport import read_packet, write_packet


def receive_checkpoint(client, receiver, *, action, window=4, progress=None):
    """Fetch all artifacts in small request windows, verifying every response.

    No per-chunk ACK roundtrip is needed. Integrity still requires every chunk
    and the final content hashes. A failed/incomplete exchange closes the TLS
    connection because unread responses must not be used by the next request.
    A successful transfer also closes this one-shot channel, so any unsolicited
    trailing response cannot become the next control response. Do not hand in
    a long-lived room-control channel. A persistent control channel plus an
    independent artifact channel still needs production adapter integration.
    A reconnect may reuse a correct partial receiver; after corrupt/conflicting
    data, create a new receiver from the same pinned manifest. Exact retries
    are idempotent. Progress is byte receipt, never permission to load/play.
    """
    require(isinstance(receiver, CheckpointReceiver),'Expected checkpoint receiver')
    require(type(window) is int and 1<=window<=8,'Window must be 1..8')
    require(type(action) is str and 1<=len(action)<=64 and action.isascii(),'Bad artifact action')
    require(digest(receiver.manifest)==receiver.checkpoint_id,'Modified checkpoint manifest')
    coordinates=[(name,i) for name,row in sorted(receiver.manifest['parts'].items())
                 for i in range((row['size']+CHUNK-1)//CHUNK)]
    total=sum(row['size'] for row in receiver.manifest['parts'].values())
    accepted_bytes=0
    try:
        for start in range(0,len(coordinates),window):
            batch=coordinates[start:start+window];expected=set(batch)
            # At most eight small requests are queued; responses remain under
            # the transport's existing packet bound. No giant JSON packet.
            for name,index in batch:
                write_packet(client.stream,{'action':action,'checkpoint_id':receiver.checkpoint_id,
                                            'part':name,'index':index})
            for _ in batch:
                response=read_packet(client.stream)
                require(response.get('ok') is True and set(response)=={'ok','chunk'},'Artifact request failed')
                packet=response['chunk']
                require(type(packet) is dict,'Bad chunk response')
                name=packet.get('part');index=packet.get('index')
                require(type(name) is str and type(index) is int and (name,index) in expected,
                        'Unexpected or duplicate response in request window')
                receiver.accept(packet)
                expected.remove((name,index))
                accepted_bytes+=min(CHUNK,receiver.manifest['parts'][name]['size']-index*CHUNK)
                if progress:progress({'stage':'RECEIVING_BYTES','received':accepted_bytes,'total':total})
            require(not expected,'Missing response in request window')
        parts=receiver.verified_parts()
        return {'parts':parts,'received_bytes':accepted_bytes,'chunks':len(coordinates),
                'request_windows':(len(coordinates)+window-1)//window,'window':window,
                'integrity_verified':True,'native_loaded':False}
    finally:
        client.close()
