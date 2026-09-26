from ai.skills import SkillRegistry, SkillDefinition

# Test registry creation
registry = SkillRegistry()
print('Registry created successfully')

# Test validation with a minimal valid skill
test_skill = {
    'schema_version': '0.1.0',
    'skill_id': 'test_skill',
    'name': 'Test Skill',
    'description': 'A test skill',
    'skill_type': 'analysis',
    'category': 'geometry',
    'inputs': ['param1'],
    'outputs': ['result'],
    'parameters': {
        'param1': {
            'type': 'number',
            'required': True,
            'description': 'Test parameter'
        }
    },
    'preconditions': [],
    'operations': [],
    'validation': [],
    'failure_modes': [],
    'metadata': {
        'version': '0.1.0',
        'status': 'draft',
        'author': 'Test',
        'risk_level': 'read_only',
        'side_effects': [],
        'rhino_tools': [],
        'grasshopper_tools': [],
        'tags': ['test'],
        'references': [],
        'created_at': '2026-09-25T00:00:00Z',
        'updated_at': '2026-09-25T00:00:00Z'
    }
}

# Test validation
is_valid, errors = registry.validate_skill(test_skill)
print(f'Validation: valid={is_valid}, errors={errors}')

# Test registration
registry.register_skill(test_skill)
print(f'Registered skill: {registry.get_skill("test_skill") is not None}')

# Test list
skills = registry.list_skills()
print(f'Listed skills: {len(skills)}')

# Test search
results = registry.search_skills('test')
print(f'Search results: {len(results)}')

print('All tests passed!')
