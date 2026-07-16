#!/usr/bin/env python3
"""Fix remaining straggler files with cross-references."""

import os

def add_references(filepath, refs):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    
    new_section = "\n## References\n"
    for ref, reason in refs:
        new_section += f"- [[{ref}]] - {reason}\n"
    new_section += "___\n"
    
    if '## References' in content:
        ref_start = content.index('## References')
        after_refs = content[ref_start:]
        next_sep = after_refs.index('___') if '___' in after_refs else len(after_refs)
        end_pos = ref_start + next_sep + 3
        content = content[:ref_start] + new_section + content[end_pos:]
    elif '___' in content:
        last_ = content.rindex('___')
        content = content[:last_] + new_section + content[last_:]
    else:
        content += new_section
    
    with open(filepath, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print(f"  ✅ {os.path.basename(filepath)}")

d = '/opt/data/Docs/in'

add_references(f'{d}/Astro-Track Early Development.md', [
    ('Astro-Track Development.md', 'Main Astro-Track development docs'),
    ('Astro-Track Data Ingestion.md', 'Data ingestion patterns'),
    ('Astro-Track Early Design Notes.md', 'Initial design decisions'),
    ('Astro Data Organisation.md', 'Data organization scheme'),
    ('Chat GPT Prompt for Target Tracker.md', 'AI prompt for tracking'),
])

add_references(f'{d}/Astro-Track.md', [
    ('Astro-Track Development.md', 'Main development docs'),
    ('Astro-Track Data Ingestion.md', 'Data ingestion'),
    ('Astro Data Organisation.md', 'Data organization'),
])

add_references(f'{d}/AstroBuySell Watch List.md', [
    ('Tech Inventory 22Jun2026.md', 'Equipment inventory'),
    ('Apertura 75Q - Scout-Speeder.md', 'Astro equipment purchases'),
    ('Items to sell March 2026.md', 'Items to sell list'),
])

add_references(f'{d}/Merope on Astrophotography Help.md', [
    ('Misc Starfront Notes.md', 'Astrophotography discussions'),
    ('Scope diary.md', 'Telescope usage notes'),
    ('_AI and Hermes Agent.md', 'AI-assisted astrophotography'),
])

add_references(f'{d}/Programmatic astro image image quality.md', [
    ('Image Processing.md', 'Image processing workflows'),
    ('OSC Processing Workflow.md', 'Color camera processing'),
    ('Mac WBPP Stacking Performance.md', 'Stacking performance'),
])

add_references(f'{d}/SFRO Nightly App.md', [
    ('Seestar at Starfront - Notes.md', 'SFRO Seestar operations'),
    ('S30 & M4 Mac mini at SFRO.md', 'SFRO equipment setup'),
    ('Misc Starfront Notes.md', 'General SFRO notes'),
])

add_references(f'{d}/Target Scheduler API.md', [
    ('Target Scheduler Log Analysis.md', 'Scheduler log analysis'),
    ('Astro-Plan Developer Guide - 03Jul2026.md', 'Astro-Plan scheduling'),
    ('Astro-Track Development.md', 'Astro-Track integration'),
])

add_references(f'{d}/Target Scheduler Log Analysis.md', [
    ('Target Scheduler API.md', 'Scheduler API docs'),
    ('Astro-Plan Developer Guide - 03Jul2026.md', 'Astro-Plan scheduling'),
    ('Astro-Track Development.md', 'Astro-Track integration'),
])

add_references(f'{d}/_Astro Application To-Do.md', [
    ('Astro-Plan Developer Guide - 03Jul2026.md', 'Astro-Plan development'),
    ('Astro-Track Development.md', 'Astro-Track tasks'),
    ('NINA Dashboard Planning.md', 'NINA dashboard planning'),
])

print('\nAll stragglers fixed!')