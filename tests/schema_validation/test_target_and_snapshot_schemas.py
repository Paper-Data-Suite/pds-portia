from __future__ import annotations
import unittest
from pathlib import Path
try:
    from .schema_support import FIXTURE_ROOT, load_json, load_validated_catalog_and_store, schema_id_for, validator_for
except ImportError:
    from schema_support import FIXTURE_ROOT, load_json, load_validated_catalog_and_store, schema_id_for, validator_for

CASES={
 'person_display_snapshot':('snapshots','person-display-snapshot.schema.json','snapshots/person_display_snapshot'),
 'portia_target_ref':('targets','portia-target-ref.schema.json','targets/portia_target_ref'),
 'support_process_target_ref':('targets','support-process-target-ref.schema.json','targets/support_process_target_ref'),
}
ROOT=FIXTURE_ROOT/'shared'

def keys(value):
    if not isinstance(value,dict) or value.get('kind') not in {'event_participants','support_process_participants'}: return []
    result=[]
    for item in value.get('targets',[]):
        if not isinstance(item,dict): continue
        ref=item.get('record_ref')
        if isinstance(ref,dict) and isinstance(ref.get('record_kind'),str) and isinstance(ref.get('record_id'),str):
            result.append((ref['record_kind'],ref['record_id']))
    return result

def duplicate_identity(value):
    found=keys(value); return len(found)!=len(set(found))

class TargetAndSnapshotSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.catalog,cls.store=load_validated_catalog_and_store()
    def validator(self,name): return validator_for(name,'1',catalog=self.catalog,store=self.store)
    def paths(self,name,group): return sorted((ROOT/CASES[name][2]/group).glob('*.json'))
    def test_contracts_are_cataloged(self):
        for name,(folder,filename,_) in CASES.items():
            with self.subTest(contract=name):
                self.assertEqual(schema_id_for(name,'1',self.catalog),f'https://paper-data-suite.github.io/pds-portia/schemas/v1/{folder}/{filename}')
    def test_valid_fixtures(self):
        for name in CASES:
            validator=self.validator(name); paths=self.paths(name,'valid'); self.assertTrue(paths)
            for path in paths:
                with self.subTest(contract=name,fixture=path.name):
                    value=load_json(path); errors=list(validator.iter_errors(value)); self.assertFalse(errors,'\n'.join(e.message for e in errors))
                    if name.endswith('_target_ref'): self.assertFalse(duplicate_identity(value))
    def test_invalid_fixtures(self):
        for name in CASES:
            validator=self.validator(name); paths=self.paths(name,'invalid'); self.assertTrue(paths)
            for path in paths:
                with self.subTest(contract=name,fixture=path.name): self.assertTrue(list(validator.iter_errors(load_json(path))),f'{path.name} unexpectedly passed structural validation')
    def test_application_invalid_targets_pass_schema(self):
        for name in ('portia_target_ref','support_process_target_ref'):
            validator=self.validator(name); paths=self.paths(name,'application_invalid'); self.assertTrue(paths)
            for path in paths:
                with self.subTest(contract=name,fixture=path.name):
                    value=load_json(path); errors=list(validator.iter_errors(value)); self.assertFalse(errors,'Application-invalid fixture must remain structurally valid:\n'+'\n'.join(e.message for e in errors)); self.assertTrue(duplicate_identity(value))
    def test_person_snapshot_is_closed(self):
        schema=self.store.schema_for_id(schema_id_for('person_display_snapshot','1',self.catalog)); self.assertEqual(schema['type'],'object'); self.assertEqual(schema['required'],['display_name']); self.assertEqual(set(schema['properties']),{'display_name'}); self.assertFalse(schema['additionalProperties'])
    def test_event_target_branch_kinds(self):
        defs=self.store.schema_for_id(schema_id_for('portia_target_ref','1',self.catalog))['$defs']; self.assertEqual(defs['eventTarget']['properties']['kind']['const'],'event'); self.assertEqual(defs['eventParticipantTarget']['properties']['kind']['const'],'event_participant'); self.assertEqual(defs['eventParticipantsTarget']['properties']['kind']['const'],'event_participants')
    def test_support_target_branch_kinds(self):
        defs=self.store.schema_for_id(schema_id_for('support_process_target_ref','1',self.catalog))['$defs']; self.assertEqual(defs['supportProcessTarget']['properties']['kind']['const'],'support_process'); self.assertEqual(defs['supportProcessParticipantTarget']['properties']['kind']['const'],'support_process_participant'); self.assertEqual(defs['supportProcessParticipantsTarget']['properties']['kind']['const'],'support_process_participants')
    def test_plural_targets_require_two_items(self):
        for name,definition in (('portia_target_ref','eventParticipantsTarget'),('support_process_target_ref','supportProcessParticipantsTarget')):
            targets=self.store.schema_for_id(schema_id_for(name,'1',self.catalog))['$defs'][definition]['properties']['targets']; self.assertEqual(targets['minItems'],2); self.assertTrue(targets['uniqueItems'])

if __name__=='__main__': unittest.main()
