"""Offline, standard-library-only parser of explicitly supplied workspace archives.

No game/Steam/process/window imports or discovery. Raw ranges are never masked.
Known archive schemas are partial witnesses, never a complete world verdict.
"""
from dataclasses import dataclass, field
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import struct

WORKSPACE=Path(__file__).resolve().parents[2]
BUILD='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
LIMIT=128*1024*1024


class SnapshotError(ValueError):pass


def require(ok,message):
    if not ok:raise SnapshotError(message)


@dataclass(frozen=True)
class Segment:
    offset:int
    data:bytes
    source:str=''  # Exact archive JSON pointer, never a process address.


@dataclass(frozen=True)
class Snapshot:
    source_path:str
    source_sha256:str
    format:str
    records:dict[str,tuple[Segment,...]]
    fields:dict[str,object]
    metadata:dict
    coverage:dict
    diagnostic_fields:dict[str,object]=field(default_factory=dict)

    def to_dict(self):
        return {'source_path':self.source_path,'source_sha256':self.source_sha256,'format':self.format,
            'records':{k:[{'offset':s.offset,'hex':s.data.hex(),'source':s.source} for s in v]
                       for k,v in self.records.items()},'fields':deepcopy(self.fields),
            'diagnostic_fields':deepcopy(self.diagnostic_fields),'metadata':deepcopy(self.metadata),
            'coverage':deepcopy(self.coverage)}


def _canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def _sha(v):return hashlib.sha256(v).hexdigest()
def _hash(v):return type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None


def _file(path):
    p=Path(path)
    require(not str(p).startswith(('\\\\','//')),'No network/device paths')
    p=p if p.is_absolute() else WORKSPACE/p
    require(p.is_relative_to(WORKSPACE),'Explicit workspace path required')
    resolved=p.resolve(strict=True)
    require(resolved.is_relative_to(WORKSPACE) and resolved.is_file(),'Explicit workspace file required')
    for ancestor in [p,*p.parents]:
        st=ancestor.lstat()
        require(not ancestor.is_symlink() and not(getattr(st,'st_file_attributes',0)&0x400),'No reparse paths')
        if ancestor==WORKSPACE:break
    require(resolved.stat().st_size<=LIMIT,'Archive exceeds bounded reader size')
    return resolved


def _raw(path,expected=None):
    p=_file(path);before=p.stat();raw=p.read_bytes();after=p.stat()
    require((before.st_size,before.st_mtime_ns,before.st_ino)==
            (after.st_size,after.st_mtime_ns,after.st_ino) and len(raw)==before.st_size,'Archive changed while reading')
    value=_sha(raw)
    require(expected is None or (_hash(expected) and value==expected),'Archive SHA mismatch')
    return p,raw,value


def _object(pairs):
    value={}
    for key,item in pairs:
        require(key not in value,'Duplicate JSON key');value[key]=item
    return value


def _json(raw):
    def bad(_):raise SnapshotError('Nonfinite JSON value')
    try:return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_object,parse_constant=bad)
    except (UnicodeError,json.JSONDecodeError) as exc:raise SnapshotError('Invalid archive JSON') from exc


def _hex(value,size=None):
    require(type(value) is str and re.fullmatch('(?:[0-9a-fA-F]{2})*',value) is not None,'Invalid raw hex')
    raw=bytes.fromhex(value);require(size is None or len(raw)==size,'Raw range length mismatch');return raw


def _number(v,low,high):return type(v) is int and low<=v<=high


def _id(value,maximum):
    require(type(value) is str and re.fullmatch('0|[1-9][0-9]*',value) is not None,'Invalid object table ID')
    result=int(value);require(result<=maximum,'Object ID out of range');return result


def _flatten(value,prefix,destination):
    # Lists preserve native iteration order. Scalars/dict leaves retain the
    # original value. No names or unknown fields are heuristically discarded.
    if type(value) is dict and value:
        for key,item in value.items():
            _flatten(item,prefix+'/'+str(key).replace('~','~0').replace('/','~1'),destination)
    else:destination[prefix]=deepcopy(value)


def _player_diagnostics(fields,diagnostics,prefix):
    # Only these three evidenced leaf fields are local identity. A future or
    # unknown player child remains shared/unknown, including nested children.
    for name in ('force_id','ruler_id','ruler_name'):
        key=prefix+'/'+name
        if key in fields:diagnostics[key]=fields.pop(key)


def _range(records,key,offset,data,source):
    require(key not in records,'Duplicate stable object ID')
    records[key]=(Segment(offset,data,source),)


def _context(snapshot,meta):
    require(type(snapshot) is dict and snapshot.get('exe_sha256')==BUILD,'Unsupported/missing game build')
    date=snapshot.get('date');player=snapshot.get('player');stack=snapshot.get('state_stack')
    require(type(date) is dict and all(k in date for k in ('year','month','day')) and
        _number(date['year'],1,9999) and _number(date['month'],1,12) and _number(date['day'],1,30),'Invalid sampled date')
    require(type(player) is dict and _number(player.get('force_id'),0,51) and
        _number(player.get('ruler_id'),0,5999) and type(stack) is list and
        all(type(s) is str for s in stack),'Invalid player/state stack')
    candidate={'build_sha256':BUILD,'date':deepcopy(date),'player':deepcopy(player),'state_stack':list(stack)}
    if 'date' in meta:
        require(meta['date']==date and meta['player']==player and meta['state_stack']==stack,
                'Embedded snapshot contexts disagree')
    else:meta.update(candidate)
    meta['phase']='PLANNING_STACK_OBSERVED' if stack==[
        'CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'] else 'OTHER_STACK'
    meta['planning_ready_proved']=False


def read_binary_range(path,*,expected_sha256,file_offset,length):
    """Opaque archived bytes only; caller receives no invented object identity."""
    p,raw,_=_raw(path,expected_sha256)
    require(p.suffix.lower()=='.bin' and _hash(expected_sha256),'Pinned workspace .bin required')
    require(_number(file_offset,0,len(raw)) and _number(length,1,len(raw)) and
            file_offset+length<=len(raw),'Invalid explicit binary range')
    return Segment(file_offset,raw[file_offset:file_offset+length],str(p)+'#file-offset='+str(file_offset))


def _objects(obj,records,fields,diagnostics,meta,gaps,source):
    required={'focused','eligibility','records','pools','record_scope'}
    require(type(obj) is dict and required<=obj.keys(),'Incomplete object witness')
    focus=obj['focused'];elig=obj['eligibility'];raw=obj['records']
    require(focus.get('schema')=='san14.focused-state.v1' and
            elig.get('schema')=='san14.reward-eligibility.v1' and type(raw) is dict,'Unknown object witness format')
    critical=focus['critical_state']
    require(_sha(_canonical(critical))==focus['critical_state_sha256'],'Focused sample hash mismatch')
    _context({'exe_sha256':focus['exe_sha256'],'date':critical['date'],'player':critical['player'],
              'state_stack':focus['state_stack']},meta)
    require(elig['exe_sha256']==BUILD and elig['date']==critical['date'] and
            elig['player']==critical['player'],'Object/eligibility contexts differ')
    lengths={'person':0x188,'city':0xC0,'district':0x18,'force':0x30,'army':0x1F0}
    ids={k:set() for k in lengths}
    for key,hx in raw.items():
        require(type(key) is str and re.fullmatch('(person|city|district|force|army):(0|[1-9][0-9]*)',key),
                'Unknown object key')
        kind,identity=key.split(':');number=_id(identity,5999 if kind=='person' else 500 if kind=='army' else 51)
        data=_hex(hx,lengths[kind])
        if kind in ('person','city'):require(int.from_bytes(data[:2],'little')==number,'Raw embedded ID mismatch')
        _range(records,key,0x10,data,source+'/records/'+key);ids[kind].add(number)
    for kind in ('city','district','force'):require(ids[kind]==set(range(52)),'Incomplete fixed table: '+kind)
    persons=elig['persons'];units=focus['all_active_units'];tasks=elig['tasks']
    require(type(persons) is list and type(units) is list and type(tasks) is list and
            len(persons)==elig['person_count'] and len(tasks)==elig['task_count'],'Sample count mismatch')
    for rows,kind in ((persons,'person'),(units,'army')):
        got=[r['id'] for r in rows]
        require(all(type(i) is int for i in got) and len(got)==len(set(got)) and set(got)==ids[kind],
                'Record and decoded object membership differ: '+kind)
    person_hash=hashlib.sha256()
    for row in persons:person_hash.update(records['person:'+str(row['id'])][0].data)
    require(person_hash.hexdigest()==elig['person_records_sha256'],'Ordered person record hash mismatch')
    require(_hash(elig['task_fields_sha256']),'Invalid task digest')
    for task in tasks:
        require(type(task) is dict and set(task)=={'type','valid','officer_ids','elapsed_value'} and
            type(task['type']) is str and type(task['valid']) is bool and type(task['officer_ids']) is list and
            len(task['officer_ids'])==len(set(task['officer_ids'])) and
            all(_number(i,1,5999) for i in task['officer_ids']) and type(task['elapsed_value']) is int,
            'Malformed sampled task fields')
    # Preserve every non-record observation including order, derived claims and
    # unknown fields. Only explicit local player identity moves to diagnostics.
    for key,value in obj.items():
        if key!='records':_flatten(value,'/objects/'+key,fields)
    for prefix in ('/objects/focused/critical_state/player','/objects/eligibility/player'):
        _player_diagnostics(fields,diagnostics,prefix)
    if 'world_rng_fields_hex' in obj:
        data=_hex(obj['world_rng_fields_hex'],16)
        _range(records,'world:0',0x450,data,source+'/world_rng_fields_hex')
        require(_number(obj.get('global_rng'),0,2**32-1),'Missing global RNG sample')
    if 'random_inputs' in obj:
        rng=obj['random_inputs'];names=['world_450','world_454','world_458','world_45c','global_18eb8b0']
        require(type(rng) is dict and set(rng)==set(names) and all(_number(rng[n],0,2**32-1) for n in names),
                'Malformed discovered RNG fields')
        data=struct.pack('<4I',*[rng[n] for n in names[:4]])
        if 'world:0' in records:require(records['world:0'][0].data==data,'Duplicate world RNG fields disagree')
        else:_range(records,'world:0',0x450,data,source+'/random_inputs')
        if 'global_rng' in obj:require(obj['global_rng']==rng[names[-1]],'Duplicate global RNG fields disagree')
    if 'world:0' not in records:gaps.append('No archived discovered world RNG bytes')
    meta['object_record_scope']=obj['record_scope']
    meta['task_identity']='Ordered observations only; stable native task IDs and +58..68 raw bytes absent'
    meta['task_digest_recomputed']=False
    gaps.extend(['Inactive/missing person and army slots are not a full table sample',
                 'Tasks retain order/decoded fields/digest but no stable ID or raw digest preimage',
                 'RNG sample is not an exhaustive random-state inventory'])


def _startup(obj,fields,diagnostics,meta,source):
    require(obj.get('schema')=='san14.startup-context-sample.v1','Unknown startup context')
    _context(obj['snapshot'],meta)
    for key,value in obj.items():
        if key=='snapshot':
            for name,item in value.items():
                target=diagnostics if name=='pid' else fields
                _flatten(item,'/context/snapshot/'+name,target)
        else:_flatten(value,'/context/'+key,fields)
    _player_diagnostics(fields,diagnostics,'/context/snapshot/player')
    # Unknown context fields, including rank-derived state and any state_sample
    # fields, remain shared/unknown observations. Never guess pointer semantics.
    meta.setdefault('sources',{})['context']=source


def _tiles(obj,records,fields,diagnostics,meta,gaps,source):
    require(obj.get('schema')=='san14.checkpoint-hex-payload-sample.v1','Unknown hex payload schema')
    _context(obj['context'],meta)
    ranges=[{'offset':0x14,'length':1},{'offset':0x16,'length':2},
            {'offset':0x18,'length':1},{'offset':0x19,'length':1}]
    require(obj['table_root_offset']==0xDFE0 and obj['slot_count']==48400 and obj['field_ranges']==ranges and
            obj['all_slot_payload_bytes']==242000 and obj['identity_or_pointer_fields_normalized'] is False,
            'Unsupported hex coverage layout')
    data=_hex(obj['ordered_payload_hex'],242000)
    require(_sha(b'san14.hex.stream-fields.v1\0'+struct.pack('<II',0xDFE0,48400)+data)==
            obj['ordered_payload_sha256'],'Tagged hex payload hash mismatch')
    for i in range(48400):
        at=i*5;key='hex:'+str(i);require(key not in records,'Duplicate hex identity')
        records[key]=(Segment(0x14,data[at:at+1],source+'/ordered_payload_hex'),
                      Segment(0x16,data[at+1:at+3],source+'/ordered_payload_hex'),
                      Segment(0x18,data[at+3:at+4],source+'/ordered_payload_hex'),
                      Segment(0x19,data[at+4:at+5],source+'/ordered_payload_hex'))
    for key,value in obj.items():
        if key=='ordered_payload_hex':continue
        _flatten(value,'/tiles/'+key,diagnostics if key=='created' else fields)
    _player_diagnostics(fields,diagnostics,'/tiles/context/player')
    if '/tiles/context/pid' in fields:diagnostics['/tiles/context/pid']=fields.pop('/tiles/context/pid')
    gaps.append('Hex coverage is exactly five serialized bytes per slot, not all CHexData or related map state')


def _economy(obj,records,fields,diagnostics,meta,gaps,source):
    require(obj.get('schema')=='san14.extended-economy-sample.v1','Unknown economic sample')
    _context(obj['snapshot'],meta)
    require(obj.get('complete_economy_inputs') is False,'Archive claims unsupported complete economy coverage')
    require(set(obj['areas'])=={str(i) for i in range(501)} and
        set(obj['area_records'])=={'area:'+str(i) for i in range(501)} and
        set(obj['cities'])==set(obj['forces_raw'])=={str(i) for i in range(52)},'Incomplete economy tables')
    consumed={'area_records','cities','forces_raw','districts_raw','center_hexes','assigned_officers'}
    for i,row in obj['areas'].items():
        identity=_id(i,500);require(row['id']==identity,'Area key/ID mismatch')
        data=_hex(obj['area_records']['area:'+i],0x88)
        require(data[0x25]==row['city_id'] and int.from_bytes(data[0x26:0x28],'little')==row['assigned_officer_id'] and
                int.from_bytes(data[0x2A:0x2C],'little')==row['center_hex_id'],'Area raw relationship mismatch')
        _range(records,'area:'+i,0x10,data,source+'/area_records/area:'+i)
    for name,kind,size,rawkey in (('cities','city',0x158,'raw_10_168'),
            ('forces_raw','force',0x1C0,None),('districts_raw','district',0x18,None),
            ('center_hexes','hex',0x10,'raw_10_20'),('assigned_officers','person',0x1F0,'raw_10_200')):
        require(type(obj[name]) is dict,'Malformed economic record group')
        for i,row in obj[name].items():
            identity=_id(i,48399 if kind=='hex' else 5999 if kind=='person' else 51)
            data=_hex(row[rawkey] if rawkey else row,size)
            if kind in ('city','person'):require(int.from_bytes(data[:2],'little')==identity,'Economic embedded ID mismatch')
            if kind=='city':require(row['id']==identity,'City key/ID mismatch')
            if kind=='person':require(row['table_id']==identity,'Officer key/ID mismatch')
            if kind=='hex':require(row['force_id']==data[4],'Center ownership differs from bytes')
            _range(records,kind+':'+i,0x10,data,source+'/'+name+'/'+i)
            if rawkey:_flatten({k:v for k,v in row.items() if k!=rawkey},'/economy/'+name+'/'+i,fields)
    order=obj['native_area_order']
    require(type(order) is list and len(order)==len(set(order)) and all(_number(i,0,500) for i in order),
            'Invalid ordered native area membership')
    expected={str(i):[] for i in range(1,52)}
    for i in order:
        city=obj['areas'][str(i)]['city_id'];require(_number(city,0,51),'Bad area city')
        if city:expected[str(city)].append(i)
    require(obj['city_area_order']==expected,'Filtered economic area order differs')
    for key,value in obj.items():
        if key not in consumed:_flatten(value,'/economy/'+key,fields)
    _player_diagnostics(fields,diagnostics,'/economy/snapshot/player')
    if '/economy/snapshot/pid' in fields:diagnostics['/economy/snapshot/pid']=fields.pop('/economy/snapshot/pid')
    gaps.extend(deepcopy(obj.get('missing_dependencies',[])))
    gaps.append('Economy person/center/district samples include referenced members only; no full task/map coverage')


def read_snapshot(path,*,expected_sha256=None):
    p,raw,source_sha=_raw(path,expected_sha256)
    require(p.suffix.lower()=='.json','JSON witness required; use explicit read_binary_range for opaque .bin')
    obj=_json(raw);require(type(obj) is dict,'Archive root must be an object')
    records={};fields={};diagnostics={};meta={'provenance':'ARCHIVED_OBSERVATION_NOT_RECAPTURED',
        'reader_game_access':False,'normalization_applied':False};gaps=[]
    schema=obj.get('schema');source=''
    if {'objects','tiles','context'}<=obj.keys():
        form='checkpoint-live-witness.v1'
        _objects(obj['objects'],records,fields,diagnostics,meta,gaps,'/objects')
        _startup(obj['context'],fields,diagnostics,meta,'/context')
        _tiles(obj['tiles'],records,fields,diagnostics,meta,gaps,'/tiles')
        for key,value in obj.items():
            if key not in ('objects','tiles','context'):
                _flatten(value,'/witness/'+key,diagnostics if key in ('created','save_files') else fields)
    elif {'focused','eligibility','records','record_scope'}<=obj.keys():
        form='partial-object-witness.v1';_objects(obj,records,fields,diagnostics,meta,gaps,source)
    elif schema=='san14.startup-context-sample.v1':
        form=schema;_startup(obj,fields,diagnostics,meta,source);gaps.append('Identity/context only: no object records')
    elif schema=='san14.checkpoint-hex-payload-sample.v1':
        form=schema;_tiles(obj,records,fields,diagnostics,meta,gaps,source)
    elif schema=='san14.extended-economy-sample.v1':
        form=schema;_economy(obj,records,fields,diagnostics,meta,gaps,source)
    elif schema=='san14.readonly-memory-transcript.v1':
        form=schema;require(obj.get('sha256')==BUILD and type(obj.get('reads')) is list,'Unknown memory transcript')
        seen=set();total=0
        for row in obj['reads']:
            require(type(row) is list and len(row)==3 and _number(row[0],0x10000,2**63-1) and
                    _number(row[1],1,LIMIT) and (row[0],row[1]) not in seen,'Invalid/duplicate transcript read')
            _hex(row[2],row[1]);seen.add((row[0],row[1]));total+=row[1]
        _economy(obj['expected_sample'],records,fields,diagnostics,meta,gaps,'/expected_sample')
        # Addresses/read order remain evidence, not portable object IDs. The
        # archived expected_sample is NOT rerun through a live-import reader.
        for key,value in obj.items():
            if key!='expected_sample':_flatten(value,'/transcript/'+key,diagnostics)
        meta['transcript_expected_sample_recomputed']=False
        meta['transcript_read_count']=len(seen);meta['transcript_total_read_bytes']=total
        gaps.append('Transcript expected_sample is archived output, not independently replayed by this reader')
    else:raise SnapshotError('Unsupported archive schema; shadow/selector fixture results are not world captures')
    meta['format_id']=form
    domains={}
    for key,segments in records.items():
        kind,identity=key.split(':');row=domains.setdefault(kind,{'ids':[],'ranges':set(),'bytes':0})
        row['ids'].append(int(identity))
        for s in segments:row['ranges'].add((s.offset,len(s.data)));row['bytes']+=len(s.data)
    for row in domains.values():
        row['ids'].sort();row['count']=len(row['ids']);row['ranges']=[{'offset':a,'length':n} for a,n in sorted(row['ranges'])]
    gaps.extend(['Archived samples are sequential observations, not a proven atomic world barrier',
                 'Diplomacy/events/AI queues/settings and complete native deserialization closure are not certified',
                 'No fresh process attachment, input barrier, planning readiness or frame attribution supplied'])
    coverage={'status':'INCOMPLETE','full_world_verified':False,'atomic_world_verified':False,
        'domains':domains,'missing_or_unproven':list(dict.fromkeys(gaps)),
        'diagnostics_are_not_automatically_ignorable':True,'raw_pointer_bytes_preserved':True}
    return Snapshot(str(p),source_sha,form,records,fields,meta,coverage,diagnostics)
